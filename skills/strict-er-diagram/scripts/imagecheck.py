"""画像とDSLの双方向照合。OCR(macOS Vision)と線・端点の幾何検出は、VLMの抽出とは独立した経路。

結果の状態は matched / conflict / insufficient_evidence / not_checked。
matched は「この検査で一致した」ことだけを示し、正しさの証明ではない。
"""
from __future__ import annotations

import difflib
import hashlib
import json
import shutil
import subprocess
import tempfile
import unicodedata
from collections import Counter
from pathlib import Path

import er

try:
    import cv2
    import numpy as np
except ImportError:  # OpenCVがなければ幾何検査は not_checked
    cv2 = None
    np = None

SYMBOL_OF = {"exactly_one": {"bar_bar"}, "zero_or_one": {"circle_bar"},
             "zero_or_more": {"circle_crow"}, "one_or_more": {"bar_crow"}}
RATIO_OF = {"exactly_one": "ratio_1", "zero_or_one": "ratio_1",
            "zero_or_more": "ratio_n", "one_or_more": "ratio_n"}
FUZZY = 0.72


def norm(text: str) -> str:
    return "".join(unicodedata.normalize("NFKC", text).casefold().split())


class Ocr:
    """ocr.swift を一度だけコンパイルして使い回す。使えなければ available が偽になる。"""

    def __init__(self):
        self.dir = tempfile.TemporaryDirectory()
        self.binary = Path(self.dir.name) / "ocr"
        swiftc = shutil.which("swiftc")
        self.available = False
        if swiftc is not None:
            built = subprocess.run([swiftc, "-O", str(Path(__file__).with_name("ocr.swift")), "-o", str(self.binary)],
                                   capture_output=True, text=True, timeout=180)
            self.available = built.returncode == 0

    def read(self, image: Path) -> list[dict]:
        out = subprocess.run([str(self.binary), str(image)], capture_output=True, text=True, timeout=120)
        if out.returncode != 0:
            return []
        return [json.loads(line) for line in out.stdout.splitlines() if line.strip()]

    def read_scaled(self, gray, factor: int) -> list[dict]:
        """拡大して読み直す。座標は元画像へ戻す。"""
        path = Path(self.dir.name) / "scaled.png"
        cv2.imwrite(str(path), cv2.resize(gray, None, fx=factor, fy=factor, interpolation=cv2.INTER_CUBIC))
        rows = self.read(path)
        for row in rows:
            row["bbox"] = [v // factor for v in row["bbox"]]
        return rows


def is_line_noise(text: str) -> bool:
    """破線や記号をOCRが文字と誤認した結果。文字として扱わず、線も消さない。"""
    return not norm(text).strip("ー一-‐–—_|=・.,'`~〇ol1ij!レへ/\\+十")


def title_of(tokens: list[dict]) -> str:
    """箱の中で最も上の行。エンティティ名はここに書かれる。"""
    if not tokens:
        return ""
    top = min(t["bbox"][0] for t in tokens)
    return " ".join(t["text"] for t in sorted(tokens, key=lambda t: t["bbox"][1]) if t["bbox"][0] - top < 8)


def binarize(gray):
    dark = gray.mean() < 128
    image = 255 - gray if dark else gray
    return (image < 160).astype("uint8")


def inside(a, b, pad=0) -> bool:
    return a[0] >= b[0] - pad and a[1] >= b[1] - pad and a[2] <= b[2] + pad and a[3] <= b[3] + pad


def merge_split_boxes(found: list[dict]) -> list[dict]:
    """線が接する箱は外形が崩れるため、内側の輪郭から戻す。見出しの罫線で分かれた穴はつなぐ。"""
    boxes = sorted((s for s in found if s["kind"] == "box"), key=lambda s: s["bbox"][0])
    others = [s for s in found if s["kind"] != "box"]
    merged: list[dict] = []
    for s in boxes:
        y0, x0, y1, x1 = s["bbox"]
        for m in merged:
            my0, mx0, my1, mx1 = m["bbox"]
            if abs(mx0 - x0) <= 6 and abs(mx1 - x1) <= 6 and -2 <= y0 - my1 <= 10:
                m["bbox"] = (my0, min(mx0, x0), y1, max(mx1, x1))
                m["area"] = (y1 - my0) * (m["bbox"][3] - m["bbox"][1])
                break
        else:
            merged.append(dict(s))
    return merged + others


def detect_shapes(mask) -> list[dict]:
    """(y0, x0, y1, x1) の箱・ひし形・楕円。内側の輪郭と包含された図形は捨てる。"""
    contours, _ = cv2.findContours(mask, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    found = []
    for c in contours:
        x, y, w, h = cv2.boundingRect(c)
        if w < 36 or h < 24:
            continue
        area = cv2.contourArea(c)
        fill = area / float(w * h)
        approx = cv2.approxPolyDP(c, 0.02 * cv2.arcLength(c, True), True)
        if len(approx) == 4 and fill > 0.88:
            kind = "box"
        elif len(approx) == 4 and 0.38 < fill < 0.62:
            kind = "diamond"
        elif len(approx) >= 6 and abs(fill - 0.785) < 0.05:
            kind = "ellipse"
        else:
            continue
        found.append({"kind": kind, "bbox": (y, x, y + h, x + w), "area": w * h})
    found = merge_split_boxes(found)
    found.sort(key=lambda s: -s["area"])
    kept: list[dict] = []
    boxes = [s for s in found if s["kind"] == "box"]
    for s in found:
        if s["kind"] != "box" and any(inside(b["bbox"], s["bbox"], 2) for b in boxes):
            continue  # 線の付いた箱の外形。内側の輪郭を採用する
        if not any(inside(s["bbox"], k["bbox"], 2) for k in kept):
            kept.append(s)
    return kept


def locate(text: str, haystacks: list[tuple[int, str]]) -> tuple[int, str, float] | None:
    """text に最も近い候補を返す。部分一致は完全一致として扱う。"""
    target = norm(text)
    best = None
    for index, hay in haystacks:
        h = norm(hay)
        if not target or not h:
            continue
        if target == h or target in h:
            return index, hay, 1.0
        score = difflib.SequenceMatcher(None, target, h).ratio()
        if len(h) > len(target):
            step = len(target)
            for start in range(0, len(h) - step + 1):
                score = max(score, difflib.SequenceMatcher(None, target, h[start:start + step]).ratio())
        if best is None or score > best[2]:
            best = (index, hay, score)
    return best


def center(b) -> tuple[int, int]:
    return (b[0] + b[2]) // 2, (b[1] + b[3]) // 2


def assign_text(shapes, ocr):
    texts = {i: [] for i in range(len(shapes))}
    free = []
    for t in ocr:
        y, x = center(t["bbox"])
        hit = None
        for i, s in enumerate(shapes):
            b = s["bbox"]
            if b[0] <= y <= b[2] and b[1] <= x <= b[3]:
                hit = i
                break
        if hit is None:
            free.append(t)
        else:
            texts[hit].append(t)
    return texts, free


def line_scale(mask) -> float:
    """線の太さから図の倍率を推定する。線幅2ピクセルを倍率1とする。"""
    runs = []
    for row in mask[:: max(1, mask.shape[0] // 400)]:
        edges = np.flatnonzero(np.diff(np.concatenate(([0], row, [0]))))
        widths = edges[1::2] - edges[0::2]
        runs.extend(int(v) for v in widths if v <= 12)
    return max(1.0, float(np.median(runs)) / 2) if runs else 1.0


def cluster_contacts(contacts, radius):
    """カラスの足の枝のように、同じ端点に属する接触をまとめる。"""
    merged: list[dict] = []
    for c in sorted(contacts, key=lambda k: (k["shape"], k["y"], k["x"])):
        for m in merged:
            if m["shape"] == c["shape"] and abs(m["y"] - c["y"]) + abs(m["x"] - c["x"]) <= radius:
                m["n"] += 1
                m["y"] += (c["y"] - m["y"]) // m["n"]
                m["x"] += (c["x"] - m["x"]) // m["n"]
                break
        else:
            merged.append({**c, "n": 1})
    return merged


def trace_connections(mask, shapes, labels=()):
    """図形と文字を除いた線画の連結成分から、接続と接触点を求める。"""
    scale = line_scale(mask)
    rest = mask.copy()
    # DSLのラベルと一致した文字だけを消す。一致しない文字は記号の誤認かもしれず、消すと線が途切れる
    for t in labels:
        y0, x0, y1, x1 = t["bbox"]
        rest[y0:y1, x0:x1] = 0
    for s in shapes:
        y0, x0, y1, x1 = s["bbox"]
        rest[max(0, y0 - 3):y1 + 3, max(0, x0 - 3):x1 + 3] = 0
    # 破線の隙間だけを線の方向に埋める。正方形で閉じると平行な線どうしが文字を介してつながる
    size = int(4 * scale) + 5
    corner = int(2 * scale) + 3  # 破線の角
    closed = (cv2.morphologyEx(rest, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_RECT, (size, 1)))
              | cv2.morphologyEx(rest, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_RECT, (1, size)))
              | cv2.morphologyEx(rest, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_RECT, (corner, corner))))
    n, labels = cv2.connectedComponents(closed, connectivity=8)
    out = []
    pad = int(6 * scale) + 3
    for c in range(1, n):
        comp = (labels == c).astype("uint8")
        if comp.sum() < 20 * scale:
            continue
        contacts = []
        for i, s in enumerate(shapes):
            y0, x0, y1, x1 = s["bbox"]
            region = np.zeros_like(comp)
            region[max(0, y0 - pad):y1 + pad, max(0, x0 - pad):x1 + pad] = 1
            region[y0 + pad:max(y0 + pad, y1 - pad), x0 + pad:max(x0 + pad, x1 - pad)] = 0
            n2, lab2 = cv2.connectedComponents((comp & region).astype("uint8"), connectivity=8)
            for k in range(1, n2):
                ys, xs = np.nonzero(lab2 == k)
                contacts.append({"shape": i, "y": int(ys.mean()), "x": int(xs.mean())})
        pieces, _ = cv2.connectedComponents((rest & comp).astype("uint8"), connectivity=8)
        ys, xs = np.nonzero(comp)
        out.append({"contacts": cluster_contacts(contacts, int(26 * scale)), "dashed": pieces - 1 >= 5,
                    "bbox": (int(ys.min()), int(xs.min()), int(ys.max()), int(xs.max()))})
    return out, scale


def classify_symbol(mask, shape_bbox, contact, scale) -> str | None:
    """端点から外へ走査し、幅の変化から記号を判定する。"""
    y0, x0, y1, x1 = shape_bbox
    y, x = contact["y"], contact["x"]
    dists = {"top": abs(y - y0), "bottom": abs(y - y1), "left": abs(x - x0), "right": abs(x - x1)}
    side = min(dists, key=dists.get)
    length, half = int(34 * scale), int(14 * scale)
    if side in ("top", "bottom"):
        start = y0 if side == "top" else y1
        step = -1 if side == "top" else 1
        cut = lambda d: mask[start + step * d, max(0, x - half):x + half + 1] \
            if 0 <= start + step * d < mask.shape[0] else np.zeros(1, "uint8")
    else:
        start = x0 if side == "left" else x1
        step = -1 if side == "left" else 1
        cut = lambda d: mask[max(0, y - half):y + half + 1, start + step * d] \
            if 0 <= start + step * d < mask.shape[1] else np.zeros(1, "uint8")
    # 箱の線そのものを飛ばす。輪郭の取り方で境界の位置が数ピクセルずれる
    full = [d for d in range(-int(4 * scale), int(5 * scale)) if cut(d).mean() >= 0.7]
    begin = max(full) + 1 if full else 1
    rows = [cut(d) for d in range(begin, begin + length)]
    spans, holes = [], []
    for row in rows:
        idx = np.nonzero(row)[0]
        if len(idx) == 0:
            spans.append(0)
            holes.append(False)
            continue
        span = int(idx[-1] - idx[0] + 1)
        spans.append(span)
        holes.append(span >= 5 * scale and row[idx[0]:idx[-1] + 1].mean() < 0.55)
    head = spans[: int(5 * scale)]
    tip = max(spans[int(6 * scale): int(13 * scale)] or [0])
    crow = len(head) > 0 and max(head) >= 9 * scale and tip < max(head) and sum(holes[: int(8 * scale)]) >= 2 * scale
    # 枝が閉じていく区間を除く
    tail_from = int(11 * scale) if crow else 0
    tail = range(tail_from, len(spans))
    circle = sum(1 for i in tail if holes[i]) >= 3 * scale
    bars, run = 0, 0
    for i in tail:
        if spans[i] >= 8 * scale and not holes[i]:
            run += 1
        else:
            if 0 < run <= 5 * scale:
                bars += 1
            run = 0
    if crow and circle:
        return "circle_crow"
    if crow and bars >= 1:
        return "bar_crow"
    if circle and bars >= 1:
        return "circle_bar"
    if bars >= 2:
        return "bar_bar"
    return None


def ratio_crop(reader, gray, contact, scale) -> str | None:
    """1文字はOCRが見落としやすいので、端点の周りだけ拡大して読み直す。"""
    if reader is None or not reader.available:
        return None
    r = int(70 * scale)
    y0, x0 = max(0, contact["y"] - r), max(0, contact["x"] - r)
    crop = gray[y0:contact["y"] + r, x0:contact["x"] + r]
    rows = reader.read_scaled(crop, 4)
    for row in rows:
        b = row["bbox"]
        row["bbox"] = [b[0] + y0, b[1] + x0, b[2] + y0, b[3] + x0]
    return ratio_near(rows, contact, scale)


def ratio_glyph(mask, contact, scale) -> str | None:
    """OCRが読めない孤立した1文字を形で判定する。細長ければ1、幅があればN。"""
    r = int(60 * scale)
    y0, x0 = max(0, contact["y"] - r), max(0, contact["x"] - r)
    crop = mask[y0:contact["y"] + r, x0:contact["x"] + r].astype("uint8")
    n, labels, stats, _ = cv2.connectedComponentsWithStats(crop, connectivity=8)
    best = None
    for i in range(1, n):
        left, top, w, h, _ = stats[i]
        touches_edge = left == 0 or top == 0 or left + w >= crop.shape[1] or top + h >= crop.shape[0]
        if touches_edge or not 12 * scale <= h <= 44 * scale:
            continue
        d = abs(top + h / 2 + y0 - contact["y"]) + abs(left + w / 2 + x0 - contact["x"])
        if best is None or d < best[0]:
            best = (d, "ratio_1" if w / h < 0.5 else "ratio_n")
    return best[1] if best else None


def ratio_near(ocr, contact, scale) -> str | None:
    best = None
    for t in ocr:
        text = norm(t["text"])
        if text not in ("1", "n", "m", "*", "l", "i"):
            continue
        y, x = center(t["bbox"])
        d = abs(y - contact["y"]) + abs(x - contact["x"])
        if d < 70 * scale and (best is None or d < best[0]):
            best = (d, "ratio_1" if text in ("1", "l", "i") else "ratio_n")
    return best[1] if best else None


class Result:
    def __init__(self):
        self.items: dict[str, dict] = {}

    def put(self, item, state, evidence=""):
        self.items[item] = {"state": state, "evidence": evidence}

    def summary(self):
        return dict(Counter(v["state"] for v in self.items.values()))


def row_text(tokens: list[dict], name: str) -> str | None:
    """属性名と縦位置が重なる文字をまとめ、1行の文字列にする。"""
    target = norm(name)
    anchors = [t for t in tokens if target in norm(t["text"])]
    if not anchors:
        return None
    anchors.sort(key=lambda t: len(t["text"]))
    y0, _, y1, _ = anchors[0]["bbox"]
    middle = (y0 + y1) / 2
    row = [t for t in tokens if t["bbox"][0] <= middle <= t["bbox"][2]
           and (t["bbox"][2] - t["bbox"][0]) <= 2 * (y1 - y0)]
    return " ".join(t["text"] for t in sorted(row, key=lambda t: t["bbox"][1]))


def text_check(result, item, text, candidates, *, scope_ok=True):
    if not scope_ok:
        result.put(item, "insufficient_evidence", "対応する図形を特定できない")
        return
    hit = locate(text, candidates)
    if hit is None:
        result.put(item, "insufficient_evidence", "OCRの結果がない")
    elif hit[2] >= 1.0:
        result.put(item, "matched", hit[1])
    elif hit[2] >= FUZZY:
        result.put(item, "conflict", f"OCR候補: {hit[1]}")
    else:
        result.put(item, "conflict", "画像の該当範囲に見つからない")


def check(image: Path, doc: dict) -> tuple[dict, dict]:
    result = Result()
    meta = {"ocr": "not_checked", "geometry": "not_checked"}
    all_items = [i for i in iter_items(doc)]
    for item in all_items:
        result.put(item, "not_checked")
    if cv2 is None:
        return finish(result, meta, doc, [], [], [])
    gray = cv2.imread(str(image), cv2.IMREAD_GRAYSCALE)
    if gray is None:
        raise er.DslError(f"画像を読めない: {image}")
    mask = binarize(gray)
    meta["geometry"] = "checked"
    shapes = detect_shapes(mask)
    reader = Ocr()
    ocr = reader.read(image) + reader.read_scaled(gray, 3) if reader.available else None
    ocr_list = [t for t in (ocr or []) if not is_line_noise(t["text"])]
    if ocr is not None:
        meta["ocr"] = "checked"
    texts, free = assign_text(shapes, ocr_list)
    joined = {i: " ".join(t["text"] for t in v) for i, v in texts.items()}
    boxes = [i for i, s in enumerate(shapes) if s["kind"] == "box"]
    ellipses = [i for i, s in enumerate(shapes) if s["kind"] == "ellipse"]
    diamonds = [i for i, s in enumerate(shapes) if s["kind"] == "diamond"]

    entity_shape: dict[str, int] = {}
    if ocr is not None:
        pool = [(i, title_of(texts[i])) for i in boxes]
        taken: set[int] = set()
        for e in sorted(doc["entities"], key=lambda x: -len(x["name"])):
            free_pool = [p for p in pool if p[0] not in taken]
            hit = locate(e["name"], free_pool)
            if hit and hit[2] >= FUZZY:
                entity_shape[e["id"]] = hit[0]
                taken.add(hit[0])
            text_check(result, f"{e['id']}.name", e["name"], free_pool)

    wanted = [norm(r["label"]) for r in doc["relationships"] if r["label"]]
    connections, scale = trace_connections(mask, shapes, [t for t in free if norm(t["text"]) in wanted])
    edges: list[dict] = []
    for c in connections:
        kinds = {shapes[k["shape"]]["kind"] for k in c["contacts"]}
        edges.append({**c, "kinds": kinds})
    chen = doc["notation"] == "chen"
    owner_of_ellipse: dict[int, int] = {}
    for c in edges:
        ids = [k["shape"] for k in c["contacts"]]
        for a in ids:
            for b in ids:
                if shapes[a]["kind"] == "ellipse" and shapes[b]["kind"] == "box":
                    owner_of_ellipse[a] = b

    if ocr is not None:
        for e in doc["entities"]:
            shape = entity_shape.get(e["id"])
            scope = [(0, joined.get(shape, ""))] + [
                (i + 1, joined[i]) for i in ellipses if owner_of_ellipse.get(i) == shape]
            for a in e["attributes"]:
                text_check(result, f"{a['id']}.name", a["name"], scope, scope_ok=shape is not None)
                if a["type"] is not None:
                    text_check(result, f"{a['id']}.type", a["type"], scope, scope_ok=shape is not None)
                if a["keys"]:
                    if chen:
                        result.put(f"{a['id']}.keys", "insufficient_evidence", "下線は幾何検査の対象外")
                    else:
                        row = row_text(texts.get(shape, []), a["name"])
                        ok = row is not None and all(k.casefold() in norm(row) for k in a["keys"])
                        result.put(f"{a['id']}.keys", "matched" if ok else "insufficient_evidence",
                                   row or "属性の行を特定できない")

    # 接続の照合
    links = hub_links(edges, shapes, diamonds) if diamonds else [
        {"a": c["contacts"][0], "b": c["contacts"][-1], "edge": c}
        for c in edges if len(c["contacts"]) == 2 and c["kinds"] == {"box"}]
    ambiguous = [c for c in edges if len(c["contacts"]) > 2]
    remaining = list(links)
    for r in doc["relationships"]:
        sa, sb = entity_shape.get(r["src"]), entity_shape.get(r["dst"])
        hit = None
        for link in remaining:
            pair = (link["a"]["shape"], link["b"]["shape"])
            if pair == (sa, sb) or pair == (sb, sa):
                hit = link
                break
        endpoints = ("src", "dst", "src_multiplicity", "dst_multiplicity", "line")
        if sa is None or sb is None:
            for name in endpoints:
                result.put(f"{r['id']}.{name}", "insufficient_evidence", "端のエンティティを特定できない")
            continue
        if hit is None:
            state = "insufficient_evidence" if ambiguous else "conflict"
            why = "交差で線を分離できない" if ambiguous else "この組の接続が画像にない"
            for name in endpoints:
                result.put(f"{r['id']}.{name}", state, why)
            continue
        remaining.remove(hit)
        result.put(f"{r['id']}.src", "matched", f"box{sa}")
        result.put(f"{r['id']}.dst", "matched", f"box{sb}")
        drawn = "dashed" if hit["edge"]["dashed"] else "solid"
        result.put(f"{r['id']}.line", "matched" if drawn == r["line_style"] else "conflict", drawn)
        src_contact = hit["a"] if hit["a"]["shape"] == sa else hit["b"]
        dst_contact = hit["b"] if src_contact is hit["a"] else hit["a"]
        for field, contact, shape in (("src_multiplicity", src_contact, sa),
                                      ("dst_multiplicity", dst_contact, sb)):
            value = r[field]
            if doc["notation"] in ("chen", "ratio"):
                seen = (ratio_near(ocr_list, contact, scale) or ratio_crop(reader, gray, contact, scale)
                        or ratio_glyph(mask, contact, scale))
                expected = RATIO_OF.get(value)
            else:
                seen = classify_symbol(mask, shapes[shape]["bbox"], contact, scale)
                expected = None
            if seen is None:
                result.put(f"{r['id']}.{field}", "insufficient_evidence", "記号を判定できない")
            elif (expected == seen) if expected else (seen in SYMBOL_OF.get(value, ())):
                result.put(f"{r['id']}.{field}", "matched", seen)
            else:
                result.put(f"{r['id']}.{field}", "conflict", f"画像の記号: {seen}")
        if r["label"]:
            pool = [(i, t["text"]) for i, t in enumerate(free)] + [(1000 + i, joined[i]) for i in diamonds]
            text_check(result, f"{r['id']}.label", r["label"], pool)
    return finish(result, meta, doc, shapes, remaining, reverse_texts(doc, texts, free, ambiguous))


def hub_links(edges, shapes, diamonds):
    """Chen記法: ひし形を挟む2本の線を、箱どうしの1関係へまとめる。"""
    hub: dict[int, list] = {}
    for c in edges:
        ids = [k for k in c["contacts"]]
        for k in ids:
            if shapes[k["shape"]]["kind"] == "diamond":
                for other in ids:
                    if shapes[other["shape"]]["kind"] == "box":
                        hub.setdefault(k["shape"], []).append((other, c))
    links = []
    for pairs in hub.values():
        if len(pairs) == 2:
            links.append({"a": pairs[0][0], "b": pairs[1][0], "edge": pairs[0][1]})
    return links


def reverse_texts(doc, texts, free, ambiguous):
    tokens = {norm(e["name"]) for e in doc["entities"]}
    for e in doc["entities"]:
        for a in e["attributes"]:
            tokens |= {norm(a["name"]), norm(a["type"] or ""), norm(a["note"] or "")} | {k.casefold() for k in a["keys"]}
    for r in doc["relationships"]:
        tokens.add(norm(r["label"] or ""))
    tokens.discard("")
    leftover = []
    for t in [x for v in texts.values() for x in v] + free:
        text = norm(t["text"])
        if len(text) <= 1:
            continue
        rest = text
        for token in sorted(tokens, key=len, reverse=True):
            rest = rest.replace(token, "")
        if len(rest) >= 2 and len(rest) * 2 >= len(text):
            kind = "unclassified"
            if not any(ord(ch) > 0x3040 and ch not in "ーレ〇一" for ch in text):
                kind = "possible_symbol"  # 記号や線の誤認かもしれない
            leftover.append({"text": t["text"], "bbox": list(t["bbox"]), "class": kind})
    return leftover + [{"text": "(交差で分離できない線)", "bbox": list(c["bbox"]), "class": "ambiguous_line"} for c in ambiguous]


def finish(result, meta, doc, shapes, unmatched_links, leftovers):
    boxes = sum(1 for s in shapes if s["kind"] == "box")
    unmatched = list(leftovers)
    if shapes and boxes != len(doc["entities"]) and doc["notation"] != "chen":
        unmatched.append({"text": f"(箱{boxes}個とエンティティ{len(doc['entities'])}件が不一致)",
                          "bbox": [], "class": "count_mismatch"})
    for link in unmatched_links:
        unmatched.append({"text": "(DSLにない接続)", "bbox": list(link["edge"]["bbox"]), "class": "extra_connection"})
    report = {"methods": meta, "summary": result.summary(), "items": result.items,
              "unmatched_image_items": unmatched,
              "limits": "幾何検出とOCRの取りこぼしがあるため、全項目matchedでも読み取りの完全性は保証しない"}
    return report, {"shapes": len(shapes)}


def iter_items(doc):
    for e in doc["entities"]:
        yield f"{e['id']}.name"
        for a in e["attributes"]:
            yield f"{a['id']}.name"
            if a["keys"]:
                yield f"{a['id']}.keys"
            if a["type"] is not None:
                yield f"{a['id']}.type"
    for r in doc["relationships"]:
        yield from (f"{r['id']}.{n}" for n in ("src", "dst", "src_multiplicity", "dst_multiplicity", "line"))
        if r["label"]:
            yield f"{r['id']}.label"


def symbol_for(doc, value) -> str | None:
    if value == "unknown":
        return None
    if doc["notation"] in ("chen", "ratio"):
        return RATIO_OF[value]
    return next(iter(SYMBOL_OF[value]))


def observation_from(image: Path, doc: dict, report: dict) -> dict:
    """照合結果から観察記録を作る。機械で確かめられなかった項目は source: vlm として区別する。"""
    raw = image.read_bytes()
    rels = {r["id"]: r for r in doc["relationships"]}
    observations, links = [], []
    for index, (item, entry) in enumerate(report["items"].items(), start=1):
        oid = f"O{index:04d}"
        symbol = None
        owner, _, field = item.partition(".")
        if field.endswith("_multiplicity") and owner in rels:
            symbol = entry["evidence"] if entry["state"] == "matched" else symbol_for(doc, rels[owner][field])
        observations.append({"id": oid, "source": "ocr_or_geometry" if entry["state"] == "matched" else "vlm",
                             "state": entry["state"], "symbol": symbol})
        links.append({"item": item, "observation": oid})
    return {"schema_version": 1, "image": {"sha256": hashlib.sha256(raw).hexdigest()},
            "observations": observations, "links": links, "reviewed_area": "whole_image"}


def run(args) -> int:
    doc, _ = er.load_model(Path(args.model))
    report, _ = check(Path(args.image), doc)
    Path(args.out).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.observation_out:
        Path(args.observation_out).write_text(
            json.dumps(observation_from(Path(args.image), doc, report), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8")
    print(json.dumps({"methods": report["methods"], "summary": report["summary"],
                      "unmatched_image_items": len(report["unmatched_image_items"])}, ensure_ascii=False))
    return 1 if report["summary"].get("conflict") else 0


def compare(a: dict, b: dict) -> list[dict]:
    """同じ画像から独立に抽出した2つのDSLの差。IDは抽出ごとに変わるため名前で対応付ける。"""
    out = []
    names_a = {norm(e["name"]): e for e in a["entities"]}
    names_b = {norm(e["name"]): e for e in b["entities"]}
    for name in sorted(set(names_a) ^ set(names_b)):
        out.append({"kind": "entity", "name": name, "only_in": "a" if name in names_a else "b"})
    for name in sorted(set(names_a) & set(names_b)):
        attrs_a = {norm(x["name"]): x for x in names_a[name]["attributes"]}
        attrs_b = {norm(x["name"]): x for x in names_b[name]["attributes"]}
        for attr in sorted(set(attrs_a) ^ set(attrs_b)):
            out.append({"kind": "attribute", "entity": name, "name": attr, "only_in": "a" if attr in attrs_a else "b"})
        for attr in sorted(set(attrs_a) & set(attrs_b)):
            for field in ("type", "keys", "note"):
                if attrs_a[attr][field] != attrs_b[attr][field]:
                    out.append({"kind": "attribute_field", "entity": name, "name": attr, "field": field,
                                "a": attrs_a[attr][field], "b": attrs_b[attr][field]})

    def rel_key(doc):
        ids = {e["id"]: norm(e["name"]) for e in doc["entities"]}
        rows = Counter()
        for r in doc["relationships"]:
            ends = [(ids[r["src"]], r["src_multiplicity"]), (ids[r["dst"]], r["dst_multiplicity"])]
            rows[(tuple(sorted(ends)), r["line_style"], norm(r["label"] or ""))] += 1
        return rows

    keys_a, keys_b = rel_key(a), rel_key(b)
    for key in (keys_a - keys_b):
        out.append({"kind": "relationship", "only_in": "a", "value": str(key)})
    for key in (keys_b - keys_a):
        out.append({"kind": "relationship", "only_in": "b", "value": str(key)})
    return out


def compare_cli(args) -> int:
    a, _ = er.load_model(Path(args.a))
    b, _ = er.load_model(Path(args.b))
    diff = compare(a, b)
    print(json.dumps({"differences": diff}, ensure_ascii=False, indent=2))
    return 1 if diff else 0
