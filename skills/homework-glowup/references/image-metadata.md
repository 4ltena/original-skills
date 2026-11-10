# Image metadata and watermark workflow

## Inspect before selecting an edit

Use a local Python environment with Pillow already available. The helper performs no downloads, network calls or recursive directory discovery. Run it on explicitly selected files and keep the JSON evidence outside submission packages and public repositories:

```bash
python3 scripts/image_metadata.py inspect source.png
```

It reports the actual format, byte and decoded-pixel hashes, dimensions, mode, PNG bit depth, transparency, palette/profile hashes, orientation, DPI/gamma where exposed, metadata keys and EXIF tag candidates. PNG chunk boundaries and CRCs are checked. Text values are represented by hashes and literal marker candidates rather than dumped into the report. Candidate strings such as `Claude`, `Codex`, `ChatGPT` or `OpenAI` are clues for inspection, not authenticated identity. C2PA presence does not itself imply AI generation.

For non-PNG files, inspection is limited to properties and EXIF exposed by Pillow; the helper does not enumerate every JPEG/WebP segment or all nested EXIF/XMP data. It cannot validate C2PA signatures or certificate trust. Do not call this a complete provenance or forensic analysis.

## Classify the finding

| Finding | What it establishes | Treatment |
| --- | --- | --- |
| PNG text/EXIF/XMP attribution | A stored field contains a tool or author name | Inspect the field's meaning. Preserve confirmed human values; select only the requested removal. |
| PNG `caBX` | An embedded C2PA manifest container is present | Distinguish presence and literal markers from signature validation. Removal discards that copy's embedded signed history. |
| Visible logo or text in pixels | A visible image element exists | Record its location. Pixel editing is a separate operation that changes content. |
| Suspected invisible pixel watermark | Requires a method-specific detector and evidence | Mark unverified when a suitable detector is unavailable; a text search or entropy test is not a detector. |
| No metadata candidates | The inspected metadata has no matching candidate | Report that limited result; do not infer human authorship or absence of other marks. |

The [C2PA 2.2 specification, PNG embedding](https://spec.c2pa.org/specifications/specifications/2.2/specs/C2PA_Specification.html#_embedding_manifests_into_png) defines the `caBX` container. Its glossary separately defines visible/invisible watermarks and soft bindings. Removing embedded metadata does not remove a watermark carried in pixels or an externally stored manifest.

## Remove selected PNG metadata on a copy

After inspection, use only the options matching the user's requested edit. Existing authorization to remove the identified information is sufficient; do not add a separate approval round.

```bash
python3 scripts/image_metadata.py clean-png source.png adjusted.png --remove-c2pa
python3 scripts/image_metadata.py clean-png source.png adjusted.png --drop-text-key Software
```

Repeat `--drop-text-key` to select multiple exact, case-sensitive keys. All text entries using a selected key are removed, including compressed and international entries. Check every matching entry first. A key may contain mixed human/tool attribution or a full XMP packet with unrelated fields: use a namespace-aware editor for selective changes inside such a value instead of dropping the whole key.

`--remove-c2pa` removes every embedded `caBX` chunk, including its signature, assertions and thumbnails. It does not rewrite individual signed claims, forge a replacement signature or assert that the image was created by a human. Explain the loss of embedded provenance before applying it and preserve the original. Where the user requested this removal, proceed within that scope. If `caBX` exists during a text edit, the helper requires an explicit provenance selection to avoid silently retaining a potentially invalid signature.

The output must be a new `.png` path. The helper rejects overwrites, unsupported animations, malformed/truncated chunks, invalid CRCs, trailing data, missing targets and changes in image/display properties. Limits are 128 MiB per file, 25 million pixels, 10,000 PNG chunks and 1 MiB per decoded text entry. Unsupported formats or larger files need another suitable, verified local tool; report the limit instead of silently converting.

## Verify the saved file

- Reopen the output, check the selected entries are absent, and compare source/output decoded-pixel hashes. The helper keeps all retained chunks byte for byte, including `IDAT`, profiles, palette, transparency and display-related chunks.
- Check original SHA-256 is unchanged. Record the different output hash and removed chunk/key names and bytes. File-size reduction alone is not verification.
- View the original and output to check readability, image orientation, colors and alpha appearance. Pixel equality does not replace a requested visual review.
- Keep genuine AI-use disclosures required by the assignment. A metadata change does not change how an image was made.
- State exactly which metadata was removed. Invisible pixel watermarks and external provenance remain unverified unless separately tested with a suitable detector. Pixel-preserving metadata removal leaves any existing pixel-domain mark unchanged.
