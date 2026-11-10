"""テスト用のER図画像と正解DSLを作る。スキルのSVG生成器とは別の描き方にしている。"""
from PIL import Image, ImageDraw, ImageFont

FONT = "/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc"


def font(size):
    return ImageFont.truetype(FONT, size)


def attr(i, name, type_=None, keys=()):
    return {"id": f"A{i:03d}", "name": name, "type": type_, "keys": list(keys), "note": None}


def rel(i, src, dst, sm, dm, line="solid", label=None, identifying=None):
    return {"id": f"R{i:03d}", "src": src, "dst": dst, "src_multiplicity": sm, "dst_multiplicity": dm,
            "line_style": line, "identifying": identifying, "label": label}


def model(notation, sem, entities, relationships):
    return {"schema_version": 1, "notation": notation, "line_semantics": sem,
            "entities": entities, "relationships": relationships, "unresolved": []}


def dashed(d, a, b, width=2, on=9, off=7):
    x0, y0 = a
    x1, y1 = b
    length = max(abs(x1 - x0), abs(y1 - y0))
    step = on + off
    for t in range(0, length, step):
        e = min(length, t + on)
        d.line((x0 + (x1 - x0) * t / length, y0 + (y1 - y0) * t / length,
                x0 + (x1 - x0) * e / length, y0 + (y1 - y0) * e / length), fill="black", width=width)


def stroke(d, a, b, style):
    if style == "dashed":
        dashed(d, a, b)
    else:
        d.line((*a, *b), fill="black", width=2)


def symbol(d, p, out, mult):
    """p は箱の境界上の端点、out は外向きの単位ベクトル。"""
    x, y = p
    ox, oy = out
    px, py = -oy, ox

    def at(dist, off=0):
        return (x + ox * dist + px * off, y + oy * dist + py * off)

    def bar(dist):
        d.line((*at(dist, -9), *at(dist, 9)), fill="black", width=2)

    def circle(dist, r=7):
        cx, cy = at(dist)
        d.ellipse((cx - r, cy - r, cx + r, cy + r), fill="white", outline="black", width=2)

    def crow():
        d.line((*at(0, -11), *at(16)), fill="black", width=2)
        d.line((*at(0, 11), *at(16)), fill="black", width=2)

    if mult == "exactly_one":
        bar(10)
        bar(19)
    elif mult == "zero_or_one":
        bar(10)
        circle(25)
    elif mult == "one_or_more":
        crow()
        bar(24)
    elif mult == "zero_or_more":
        crow()
        circle(26)


def table_box(d, x, y, w, entity):
    rows = entity["attributes"]
    h = 46 + 30 * len(rows)
    d.rectangle((x, y, x + w, y + h), outline="black", width=2)
    d.text((x + 14, y + 9), entity["name"], fill="black", font=font(20))
    d.line((x, y + 40, x + w, y + 40), fill="#888888", width=1)
    for i, a in enumerate(rows):
        row = y + 46 + 30 * i
        d.text((x + 12, row), ",".join(a["keys"]), fill="black", font=font(16))
        d.text((x + 80, row), a["name"], fill="black", font=font(16))
        if a["type"]:
            d.text((x + 210, row), a["type"], fill="black", font=font(16))
    return (x, y, x + w, y + h)


def crows_foot_image(doc, path):
    """横2列に箱を置き、関係は箱の下か横へ直線で結ぶ。"""
    image = Image.new("RGB", (1300, 900), "white")
    d = ImageDraw.Draw(image)
    boxes = {}
    for i, e in enumerate(doc["entities"]):
        boxes[e["id"]] = table_box(d, 60 + (i % 2) * 720, 60 + (i // 2) * 420, 400, e)
    used = {}
    for r in doc["relationships"]:
        a, b = boxes[r["src"]], boxes[r["dst"]]
        k = used.get(r["src"] + r["dst"], 0)
        used[r["src"] + r["dst"]] = k + 1
        if a[1] == b[1] and a[0] < b[0]:  # 同じ行: 右辺から左辺へ
            y = (a[1] + min(a[3], b[3])) // 2 + 40 * k
            p, q, po, qo = (a[2], y), (b[0], y), (1, 0), (-1, 0)
        elif a[0] == b[0] and a[1] < b[1]:  # 同じ列: 下辺から上辺へ
            x = a[0] + 120 + 60 * k
            p, q, po, qo = (x, a[3]), (x, b[1]), (0, 1), (0, -1)
        else:
            raise ValueError("synth: この配置は未対応")
        stroke(d, p, q, r["line_style"])
        symbol(d, p, po, r["src_multiplicity"])
        symbol(d, q, qo, r["dst_multiplicity"])
        if r["label"]:
            mx, my = (p[0] + q[0]) // 2, (p[1] + q[1]) // 2
            d.text((mx + 10, my - 30 if p[1] == q[1] else my - 12), r["label"], fill="black", font=font(16))
    image.save(path)


def ratio_image(doc, path, chen=False):
    image = Image.new("RGB", (1300, 760), "white")
    d = ImageDraw.Draw(image)
    centers = {}
    for i, e in enumerate(doc["entities"]):
        x, y = 170 + i * 460, 340
        d.rectangle((x - 110, y - 50, x + 110, y + 50), outline="black", width=2)
        d.text((x - 44, y - 13), e["name"], fill="black", font=font(22))
        centers[e["id"]] = (x, y)
        if chen:
            for j, a in enumerate(e["attributes"]):
                ax, ay = x - 110 + j * 150, y - 200
                d.line((ax + 40, ay + 34, x - 60 + j * 90, y - 50), fill="black", width=2)
                d.ellipse((ax - 40, ay - 34, ax + 110, ay + 34), outline="black", width=2)
                d.text((ax - 12, ay - 12), a["name"], fill="black", font=font(18))
    for r in doc["relationships"]:
        a, b = centers[r["src"]], centers[r["dst"]]
        left, right = (a[0] + 110, a[1]), (b[0] - 110, b[1])
        text_of = {"exactly_one": "1", "zero_or_one": "1", "zero_or_more": "N", "one_or_more": "N"}
        if chen:
            mx = (left[0] + right[0]) // 2
            d.line((*left, mx - 90, a[1]), fill="black", width=2)
            d.line((mx + 90, a[1], *right), fill="black", width=2)
            d.polygon([(mx - 90, a[1]), (mx, a[1] - 62), (mx + 90, a[1]), (mx, a[1] + 62)], outline="black", width=2)
            d.text((mx - 34, a[1] - 13), r["label"], fill="black", font=font(20))
        else:
            d.line((*left, *right), fill="black", width=2)
            if r["label"]:
                d.text(((left[0] + right[0]) // 2 - 30, a[1] - 34), r["label"], fill="black", font=font(18))
        d.text((left[0] + 12, a[1] + 8), text_of[r["src_multiplicity"]], fill="black", font=font(28))
        d.text((right[0] - 34, a[1] + 8), text_of[r["dst_multiplicity"]], fill="black", font=font(28))
    image.save(path)


def shop():
    return model("crows_foot", "identifying", [
        {"id": "E001", "name": "顧客", "attributes": [attr(1, "顧客ID", "int", ["PK"]), attr(2, "氏名", "varchar")]},
        {"id": "E002", "name": "注文", "attributes": [attr(3, "注文ID", "int", ["PK"]), attr(4, "顧客ID", "int", ["FK"])]},
        {"id": "E003", "name": "配送先", "attributes": [attr(5, "配送ID", "int", ["PK"])]},
        {"id": "E004", "name": "明細", "attributes": [attr(6, "明細ID", "int", ["PK"]), attr(7, "注文ID", "int", ["FK"])]},
    ], [
        rel(1, "E001", "E002", "exactly_one", "zero_or_more", "dashed", "発注する", False),
        rel(2, "E002", "E004", "exactly_one", "one_or_more", "solid", "含む", True),
        rel(3, "E001", "E003", "zero_or_one", "zero_or_more", "dashed", None, False),
    ])


def school():
    return model("crows_foot", "none", [
        {"id": "E001", "name": "学生", "attributes": [attr(1, "学籍番号", "char(8)", ["PK"])]},
        {"id": "E002", "name": "履修", "attributes": [attr(2, "科目番号", "int", ["PK", "FK"])]},
    ], [rel(1, "E001", "E002", "exactly_one", "one_or_more", "solid", "登録する")])


def ratio():
    return model("ratio", "none", [
        {"id": "E001", "name": "学科", "attributes": []},
        {"id": "E002", "name": "教員", "attributes": []},
        {"id": "E003", "name": "授業", "attributes": []},
    ], [rel(1, "E001", "E002", "exactly_one", "zero_or_more", "solid", "所属"),
        rel(2, "E002", "E003", "exactly_one", "one_or_more", "solid", "担当")])


def chen():
    return model("chen", "none", [
        {"id": "E001", "name": "学生", "attributes": [attr(1, "氏名"), attr(2, "住所")]},
        {"id": "E002", "name": "科目", "attributes": [attr(3, "単位数")]},
    ], [rel(1, "E001", "E002", "zero_or_one", "zero_or_more", "solid", "履修")])


def scale(entities=50, per=10, relationships=100):
    mults = ["zero_or_one", "exactly_one", "zero_or_more", "one_or_more"]
    ents, n = [], 0
    for i in range(entities):
        attrs = []
        for j in range(per):
            n += 1
            attrs.append(attr(n, f"属性{i}_{j}", "varchar", ["PK"] if j == 0 else []))
        ents.append({"id": f"E{i + 1:03d}", "name": f"エンティティ{i}", "attributes": attrs})
    rels = []
    for k in range(relationships):
        rels.append(rel(k + 1, f"E{(k * 7) % entities + 1:03d}", f"E{(k * 13 + 3) % entities + 1:03d}",
                        mults[k % 4], mults[(k + 1) % 4], "solid" if k % 2 else "dashed", f"関係{k}", bool(k % 2)))
    return model("crows_foot", "identifying", ents, rels)
