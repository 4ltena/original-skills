#!/usr/bin/env python3
"""Inspect raster metadata and remove explicitly selected PNG metadata on a copy."""

import argparse
from collections import Counter
import hashlib
from io import BytesIO
import json
from pathlib import Path
import struct
import sys
import warnings
import zlib

from PIL import ExifTags, Image


PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
MAX_FILE_BYTES = 128 * 1024 * 1024
MAX_PIXELS = 25_000_000
MAX_TEXT_BYTES = 1024 * 1024
TEXT_CHUNKS = {b"tEXt", b"zTXt", b"iTXt"}
MARKERS = (
    "codex", "claude", "anthropic", "openai", "chatgpt", "gpt-image",
    "dall-e", "dall·e", "c2pa", "trainedalgorithmicmedia", "synthid",
)


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def markers(value):
    text = value.decode("utf-8", "replace") if isinstance(value, bytes) else str(value)
    return [name for name in MARKERS if name in text.casefold()]


def read_file(path):
    with path.open("rb") as stream:
        data = stream.read(MAX_FILE_BYTES + 1)
    if len(data) > MAX_FILE_BYTES:
        raise ValueError("Input exceeds the 128 MiB file limit")
    return data


def png_chunks(data):
    if not data.startswith(PNG_SIGNATURE):
        raise ValueError("PNG signature required")
    chunks = []
    offset = len(PNG_SIGNATURE)
    while offset < len(data):
        if len(chunks) >= 10000 or offset + 12 > len(data):
            raise ValueError("Too many chunks or truncated PNG header")
        length = struct.unpack_from(">I", data, offset)[0]
        end = offset + 12 + length
        if end > len(data):
            raise ValueError("Truncated PNG chunk")
        kind = data[offset + 4:offset + 8]
        payload = data[offset + 8:end - 4]
        crc = struct.unpack_from(">I", data, end - 4)[0]
        if zlib.crc32(kind + payload) & 0xFFFFFFFF != crc:
            raise ValueError("Invalid PNG chunk CRC")
        if not all(65 <= c <= 90 or 97 <= c <= 122 for c in kind):
            raise ValueError("Invalid PNG chunk type")
        chunks.append((kind, payload, data[offset:end]))
        offset = end
        if kind == b"IEND":
            if length or offset != len(data):
                raise ValueError("Invalid IEND or trailing bytes; no automatic edit")
            break
    if (not chunks or chunks[0][0] != b"IHDR" or len(chunks[0][1]) != 13
            or chunks[-1][0] != b"IEND" or not any(k == b"IDAT" for k, _, _ in chunks)):
        raise ValueError("Missing required PNG chunks")
    return chunks


def inflate_text(data):
    decoder = zlib.decompressobj()
    result = decoder.decompress(data, MAX_TEXT_BYTES + 1)
    if len(result) > MAX_TEXT_BYTES or not decoder.eof or decoder.unused_data:
        raise ValueError("Invalid or oversized compressed PNG text")
    return result


def png_text(kind, payload):
    keyword, separator, rest = payload.partition(b"\0")
    if not separator or not 1 <= len(keyword) <= 79:
        raise ValueError("Invalid PNG text keyword")
    if kind == b"zTXt":
        if not rest or rest[0] != 0:
            raise ValueError("Unsupported PNG text compression")
        value = inflate_text(rest[1:])
    elif kind == b"iTXt":
        if len(rest) < 2 or rest[0] not in (0, 1) or rest[1] != 0:
            raise ValueError("Invalid international PNG text")
        flag = rest[0]
        language, sep1, remaining = rest[2:].partition(b"\0")
        translated, sep2, value = remaining.partition(b"\0")
        if not sep1 or not sep2:
            raise ValueError("Missing international PNG text separators")
        if flag:
            value = inflate_text(value)
    else:
        value = rest
    if len(value) > MAX_TEXT_BYTES:
        raise ValueError("PNG text exceeds the 1 MiB limit")
    return keyword.decode("latin1"), value


def image_properties(data):
    with warnings.catch_warnings():
        warnings.simplefilter("error", Image.DecompressionBombWarning)
        with Image.open(BytesIO(data)) as image:
            if image.width * image.height > MAX_PIXELS:
                raise ValueError("Image exceeds the 25 million pixel limit")
            image.load()
            exif = image.getexif()
            info = image.info
            palette = bytes(image.palette.palette) if image.palette else b""
            return {
                "format": image.format,
                "width": image.width, "height": image.height,
                "mode": image.mode, "bands": list(image.getbands()),
                "frames": getattr(image, "n_frames", 1),
                "has_transparency": "A" in image.getbands() or "transparency" in info,
                "orientation": exif.get(274),
                "dpi": info.get("dpi"), "gamma": info.get("gamma"),
                "icc_profile_sha256": sha256(info["icc_profile"]) if info.get("icc_profile") else None,
                "palette_sha256": sha256(palette) if palette else None,
                "decoded_pixels_sha256": sha256(image.tobytes()),
                "metadata_keys": sorted(str(key) for key in info),
                "exif_tags": [
                    {"id": tag, "name": ExifTags.TAGS.get(tag, str(tag)),
                     "marker_candidates": markers(value)}
                    for tag, value in exif.items()
                ],
            }


def inspect_bytes(data):
    report = {"bytes": len(data), "sha256": sha256(data), "image": image_properties(data)}
    report["limits"] = [
        "Marker candidates are literal strings, not proof of authorship or watermark detection.",
        "C2PA signatures and certificate trust are not validated.",
        "Pixel-domain watermarks, external manifests and unparsed metadata remain unverified.",
        "Decoded pixel hashes cover the first frame only; animation editing is unsupported.",
        "Metadata values are not dumped; keys, hashes and candidate labels are reported.",
    ]
    if data.startswith(PNG_SIGNATURE):
        chunks = png_chunks(data)
        report["png"] = {
            "bit_depth": chunks[0][1][8],
            "chunk_counts": dict(Counter(k.decode("ascii") for k, _, _ in chunks)),
            "text": [], "c2pa_chunks": [],
        }
        for index, (kind, payload, _) in enumerate(chunks):
            if kind in TEXT_CHUNKS:
                keyword, value = png_text(kind, payload)
                report["png"]["text"].append({
                    "index": index, "chunk": kind.decode("ascii"), "key": keyword,
                    "value_bytes": len(value), "value_sha256": sha256(value),
                    "marker_candidates": markers(value),
                })
            elif kind == b"caBX":
                report["png"]["c2pa_chunks"].append({
                    "index": index, "bytes": len(payload), "sha256": sha256(payload),
                    "marker_candidates": markers(payload), "signature_validation": "Unverified",
                })
    else:
        report["limits"].append("Non-PNG inspection is limited to Pillow properties and EXIF tag candidates.")
    return report


def clean_png(source, output, remove_c2pa=False, drop_text_keys=()):
    if source.resolve() == output.resolve() or output.exists() or output.is_symlink():
        raise ValueError("Output must be a distinct, non-existing path")
    if output.suffix.lower() != ".png":
        raise ValueError("Output filename must use the .png extension")
    if not remove_c2pa and not drop_text_keys:
        raise ValueError("Select --remove-c2pa and/or exact --drop-text-key values after inspection")
    data = read_file(source)
    chunks = png_chunks(data)
    before = inspect_bytes(data)
    if before["image"]["frames"] != 1 or any(k == b"acTL" for k, _, _ in chunks):
        raise ValueError("Animated PNG editing is unsupported")
    if any(k == b"caBX" for k, _, _ in chunks) and not remove_c2pa:
        raise ValueError("Metadata edits may invalidate provenance; explicitly select --remove-c2pa for this copy")
    kept, removed, found_keys = [], [], set()
    for index, (kind, payload, raw) in enumerate(chunks):
        keyword = png_text(kind, payload)[0] if kind in TEXT_CHUNKS else None
        drop = (remove_c2pa and kind == b"caBX") or keyword in drop_text_keys
        if drop:
            removed.append({"index": index, "chunk": kind.decode("ascii"), "key": keyword,
                            "bytes": len(raw), "sha256": sha256(raw)})
            if keyword is not None:
                found_keys.add(keyword)
        else:
            kept.append(raw)
    if not removed or set(drop_text_keys) - found_keys:
        raise ValueError("Requested metadata was not found; no output written")
    if remove_c2pa and not any(item["chunk"] == "caBX" for item in removed):
        raise ValueError("Requested caBX metadata was not found; no output written")
    cleaned = PNG_SIGNATURE + b"".join(kept)
    after = inspect_bytes(cleaned)
    # Exclude only the list of metadata keys; every image/display property must agree.
    compared = [key for key in before["image"] if key != "metadata_keys"]
    if any(before["image"][key] != after["image"][key] for key in compared):
        raise ValueError("Image/display properties changed; no output written")
    if read_file(source) != data:
        raise ValueError("Source changed during processing; no output written")
    # Exclusive creation never overwrites an original, destination or symlink.
    with output.open("xb") as stream:
        stream.write(cleaned)
    saved = read_file(output)
    reopened = inspect_bytes(saved)
    if saved != cleaned or read_file(source) != data:
        raise ValueError("Post-save verification failed; inspect the output before use")
    return {
        "source": str(source), "output": str(output), "before": before, "after": reopened,
        "removed": removed, "original_unchanged": True,
        "retained_chunks_byte_identical": [raw for _, _, raw in png_chunks(saved)] == kept,
        "decoded_pixels_identical": before["image"]["decoded_pixels_sha256"] == reopened["image"]["decoded_pixels_sha256"],
        "provenance_effect": (
            "Embedded caBX manifest removed, including its signature; original retained."
            if remove_c2pa else "No embedded caBX manifest was present."
        ),
        "watermark_limit": "No claim of human authorship or absence of other watermarks.",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    audit = commands.add_parser("inspect", help="Read image properties and candidate metadata")
    audit.add_argument("files", nargs="+", type=Path)
    clean = commands.add_parser("clean-png", help="Remove selected metadata on a lossless PNG copy")
    clean.add_argument("source", type=Path)
    clean.add_argument("output", type=Path)
    clean.add_argument("--remove-c2pa", action="store_true", help="Remove the entire embedded caBX manifest, including its signature")
    clean.add_argument("--drop-text-key", action="append", default=[], help="Remove all PNG text entries with this exact key; repeat as needed")
    args = parser.parse_args()
    try:
        if args.command == "inspect":
            result = [{"path": str(path), **inspect_bytes(read_file(path))} for path in args.files]
        else:
            result = clean_png(args.source, args.output, args.remove_c2pa, args.drop_text_key)
        print(json.dumps(result, indent=2, ensure_ascii=True))
    except (OSError, ValueError, SyntaxError, zlib.error, Image.DecompressionBombWarning,
            Image.DecompressionBombError) as error:
        print(json.dumps({"error": str(error)}, ensure_ascii=True), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
