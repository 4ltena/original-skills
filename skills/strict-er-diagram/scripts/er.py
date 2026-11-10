#!/usr/bin/env python3
"""strict-er-diagram CLI: DSLの厳密検証、図の生成、Leanカーネル検査、画像照合の呼び出し。"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent
LEAN_SRC = SKILL / "lean" / "Er.lean"
LEAN_VERSION = "4.35.0"
MAX_DSL = 256 * 1024
MAX_OUTPUT = 256 * 1024
MAX_LINES = 4096
MAX_LINE = 1024
MAX_ENTITIES, MAX_ATTRIBUTES, MAX_RELATIONSHIPS = 50, 500, 100
LEAN_TIMEOUT = 120
PROOF_WORKERS = 3  # 同時に動かす証明プロセスの上限
VIEWS = ("conceptual", "logical")
MULT = {"zero_or_one": "zeroOne", "exactly_one": "one", "zero_or_more": "zeroMany",
        "one_or_more": "oneMany", "unknown": "unknown"}
NOTATION = {"crows_foot": "crows", "chen": "chen", "ratio": "ratio", "unknown": "unknown"}
LINE_SEM = {"identifying": "identifying", "none": "none", "unknown": "unknown"}
SYM = {"bar_bar": "barBar", "circle_bar": "circleBar", "circle_crow": "circleCrow",
       "bar_crow": "barCrow", "ratio_1": "ratioOne", "ratio_n": "ratioMany", "user": "user"}
KEY_ORDER = ["PK", "FK", "UK"]
ALLOWED_AXIOMS = {"propext", "Classical.choice", "Quot.sound"}


class DslError(ValueError):
    pass


def _no_dup(pairs):
    seen = {}
    for key, value in pairs:
        if key in seen:
            raise DslError(f"重複キー: {key}")
        seen[key] = value
    return seen


def _no_float(text):
    raise DslError(f"浮動小数点は使えない: {text}")


def strict_loads(raw: bytes):
    try:
        return json.loads(raw.decode("utf-8"), object_pairs_hook=_no_dup,
                          parse_float=_no_float, parse_constant=_no_float)
    except UnicodeDecodeError as exc:
        raise DslError(f"UTF-8ではない: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise DslError(f"JSONとして読めない: {exc}") from exc


def _obj(value, keys, where):
    if not isinstance(value, dict):
        raise DslError(f"{where}: オブジェクトが必要")
    if set(value) != set(keys):
        raise DslError(f"{where}: キーが不正 {sorted(set(value) ^ set(keys))}")
    return value


def _str(value, where, *, nullable=False, nonempty=True):
    if value is None and nullable:
        return None
    if not isinstance(value, str) or (nonempty and not value):
        raise DslError(f"{where}: 文字列が必要")
    return value


def _enum(value, allowed, where):
    if value not in allowed:
        raise DslError(f"{where}: 不正な値 {value!r}")
    return value


def _id(value, pattern, where):
    if not isinstance(value, str) or not re.fullmatch(pattern, value):
        raise DslError(f"{where}: IDの形式が不正 {value!r}")
    return value


def validate(doc) -> dict:
    """スキーマと規約を検査し、IDで整列した正規形を返す。属性の順序は保持する。"""
    _obj(doc, ["schema_version", "notation", "line_semantics", "entities", "relationships",
               "unresolved"], "root")
    if doc["schema_version"] != 1 or isinstance(doc["schema_version"], bool):
        raise DslError("schema_version は 1")
    _enum(doc["notation"], NOTATION, "notation")
    _enum(doc["line_semantics"], LINE_SEM, "line_semantics")
    for name in ("entities", "relationships", "unresolved"):
        if not isinstance(doc[name], list):
            raise DslError(f"{name}: 配列が必要")
    if len(doc["entities"]) > MAX_ENTITIES or len(doc["relationships"]) > MAX_RELATIONSHIPS:
        raise DslError("上限超過: エンティティまたは関係の数")
    attr_total = 0
    for i, e in enumerate(doc["entities"]):
        where = f"entities[{i}]"
        _obj(e, ["id", "name", "attributes"], where)
        _id(e["id"], r"E\d{3}", where)
        _str(e["name"], where + ".name")
        if not isinstance(e["attributes"], list):
            raise DslError(where + ".attributes: 配列が必要")
        for j, a in enumerate(e["attributes"]):
            w = f"{where}.attributes[{j}]"
            attr_total += 1
            _obj(a, ["id", "name", "type", "keys", "note"], w)
            _id(a["id"], r"A\d{3}", w)
            _str(a["name"], w + ".name")
            _str(a["type"], w + ".type", nullable=True)
            _str(a["note"], w + ".note", nullable=True)
            if not isinstance(a["keys"], list) or not all(k in KEY_ORDER for k in a["keys"]) \
                    or a["keys"] != [k for k in KEY_ORDER if k in a["keys"]]:
                raise DslError(w + ".keys: PK, FK, UK の順の部分集合が必要")
    if attr_total > MAX_ATTRIBUTES:
        raise DslError("上限超過: 属性の数")
    for i, r in enumerate(doc["relationships"]):
        where = f"relationships[{i}]"
        _obj(r, ["id", "src", "dst", "src_multiplicity", "dst_multiplicity", "line_style",
                 "identifying", "label"], where)
        _id(r["id"], r"R\d{3}", where)
        _id(r["src"], r"E\d{3}", where + ".src")
        _id(r["dst"], r"E\d{3}", where + ".dst")
        _enum(r["src_multiplicity"], MULT, where)
        _enum(r["dst_multiplicity"], MULT, where)
        _enum(r["line_style"], ("solid", "dashed"), where)
        if r["identifying"] not in (True, False, None):
            raise DslError(where + ".identifying")
        _str(r["label"], where + ".label", nullable=True)
    for i, u in enumerate(doc["unresolved"]):
        where = f"unresolved[{i}]"
        _obj(u, ["target", "field", "views", "question"], where)
        _str(u["target"], where + ".target")
        _str(u["field"], where + ".field")
        _str(u["question"], where + ".question")
        if u["views"] not in (["conceptual"], ["logical"], ["conceptual", "logical"]):
            raise DslError(where + ".views")
    ids = [e["id"] for e in doc["entities"]]
    aids = [a["id"] for e in doc["entities"] for a in e["attributes"]]
    rids = [r["id"] for r in doc["relationships"]]
    for group in (ids, aids, rids):
        if len(group) != len(set(group)):
            raise DslError("IDが重複している")
    for r in doc["relationships"]:
        if r["src"] not in ids or r["dst"] not in ids:
            raise DslError(f"{r['id']}: 存在しないエンティティを参照している")
    out = dict(doc)
    out["entities"] = sorted(doc["entities"], key=lambda e: e["id"])
    out["relationships"] = sorted(doc["relationships"], key=lambda r: r["id"])
    return out


def _jstr(text: str) -> str:
    out = ['"']
    for ch in text:
        if ch == '"':
            out.append('\\"')
        elif ch == "\\":
            out.append("\\\\")
        elif ord(ch) < 32:
            out.append(f"\\u{ord(ch):04x}")
        else:
            out.append(ch)
    out.append('"')
    return "".join(out)


def _jdump(value) -> str:
    if value is None:
        return "null"
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, str):
        return _jstr(value)
    if isinstance(value, list):
        return "[" + ",".join(_jdump(v) for v in value) + "]"
    return "{" + ",".join(_jstr(k) + ":" + _jdump(value[k]) for k in sorted(value)) + "}"


def canonical(doc) -> bytes:
    return (_jdump(doc) + "\n").encode("utf-8")


def load_model(path: Path) -> tuple[dict, bytes]:
    raw = path.read_bytes()
    if len(raw) > MAX_DSL:
        raise DslError(f"上限超過: DSLは{MAX_DSL}バイトまで")
    return validate(strict_loads(raw)), raw


def lean_bytes(text) -> str:
    raw = text if isinstance(text, bytes) else text.encode("utf-8")
    return f"(Bytes.mk {len(raw)} 0x{raw.hex() or '0'})"


def _opt(text) -> str:
    return "none" if text is None else f"(some {lean_bytes(text)})"


def _bool(value) -> str:
    return "true" if value else "false"


def lean_model(doc) -> str:
    attrs = lambda e: ", ".join(
        f"⟨{lean_bytes(a['id'])}, {lean_bytes(a['name'])}, {_opt(a['type'])}, "
        f"{_bool('PK' in a['keys'])}, {_bool('FK' in a['keys'])}, {_bool('UK' in a['keys'])}, "
        f"{_opt(a['note'])}⟩" for a in e["attributes"])
    ents = ",\n".join(f"⟨{lean_bytes(e['id'])}, {lean_bytes(e['name'])}, [{attrs(e)}]⟩"
                      for e in doc["entities"])
    rels = ",\n".join(
        f"⟨{lean_bytes(r['id'])}, {lean_bytes(r['src'])}, {lean_bytes(r['dst'])}, "
        f".{MULT[r['src_multiplicity']]}, .{MULT[r['dst_multiplicity']]}, .{r['line_style']}, "
        f"{'none' if r['identifying'] is None else '(some ' + _bool(r['identifying']) + ')'}, "
        f"{_opt(r['label'])}⟩" for r in doc["relationships"])
    unres = ",\n".join(
        f"⟨{lean_bytes(u['target'])}, {lean_bytes(u['field'])}, {_bool('conceptual' in u['views'])}, "
        f"{_bool('logical' in u['views'])}, {lean_bytes(u['question'])}⟩" for u in doc["unresolved"])
    return (f"def model : Model := ⟨.{NOTATION[doc['notation']]}, .{LINE_SEM[doc['line_semantics']]},\n"
            f"[{ents}],\n[{rels}],\n[{unres}]⟩\n")


def lean_lines(raw: bytes) -> str:
    return "[" + ", ".join(lean_bytes(line) for line in raw.split(b"\n")[:-1]) + "]"


def find_lean() -> str | None:
    env = os.environ.get("ER_LEAN")
    if env is not None:
        return env if Path(env).exists() else None
    pinned = Path.home() / f".elan/toolchains/leanprover--lean4---v{LEAN_VERSION}/bin/lean"
    if pinned.exists():
        return str(pinned)  # elanの代理を経由しないのでtoolchainの自動取得が起きない
    return shutil.which("lean")


def run_lean(lean: str, args: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run([lean, *args], cwd=cwd, capture_output=True, text=True,
                          timeout=LEAN_TIMEOUT)


def lean_ready() -> tuple[str | None, str]:
    lean = find_lean()
    if lean is None:
        return None, "leanが見つからない"
    try:
        out = subprocess.run([lean, "--version"], capture_output=True, text=True, timeout=30,
                             cwd=tempfile.gettempdir()).stdout
    except (OSError, subprocess.SubprocessError) as exc:
        return None, f"leanを実行できない: {exc}"
    if f"version {LEAN_VERSION}," not in out:
        return None, f"Leanの版が違う: {out.strip()!r}（{LEAN_VERSION}が必要）"
    return lean, ""


def wanted(fmt: str) -> list[str]:
    return ["mermaid", "svg"] if fmt == "both" else [fmt]


def views_of(view: str) -> list[str]:
    return list(VIEWS) if view == "both" else [view]


def generator_source(doc, views, formats) -> str:
    lines = [LEAN_SRC.read_text(encoding="utf-8"), "open Er\n", lean_model(doc)]
    body = ['def main : IO Unit := do',
            '  if !wellFormed model then',
            '    IO.eprintln "wellFormed failed"',
            '    IO.Process.exit 3']
    for v in views:
        p = f"(project .{v} model)"
        body.append(f'  writeB "status.{v}.json" (encodeClassified (classifyView .{v} model))')
        body.append(f'  writeB "mermaid_problems.{v}.json" (jarr ((mermaidProblems {p}).map jstr) ++ b!"\\n")')
        body.append(f'  if (classifyView .{v} model).status != .blocked then')
        if "mermaid" in formats:
            body.append(f'    if mermaidRepresentable {p} then writeB "{v}.mmd" (renderMermaid {p})')
        if "svg" in formats:
            body.append(f'    writeB "{v}.svg" (renderSvg (layout {p}))')
            body.append(f'    writeB "label_crossings.{v}.txt" (natB (labelCrossings (layout {p})) ++ b!"\\n")')
        body.append('    pure ()')
    return "\n".join(lines + body) + "\n"


def proof_sources(doc, raw_dsl, work: Path, views, observation) -> dict[str, tuple[str, list[str]]]:
    """保存物を読み直し、成果物ごとの証明ファイルを組み立てる。

    重い検査を別プロセスへ分け、1ファイルごとの時間上限を保つ。
    """
    # 時間の上限は LEAN_TIMEOUT で管理する
    head = (LEAN_SRC.read_text(encoding="utf-8") + "\nopen Er\nset_option maxHeartbeats 0\n" + lean_model(doc))
    groups: dict[str, tuple[list[str], list[str]]] = {}

    def group(name):
        return groups.setdefault(name, ([], []))

    def thm(name, statement, where="model"):
        src, thms = group(where)
        src.append(f"theorem {name} : {statement} := by decide +kernel")
        thms.append(name)

    def data(line, where):
        group(where)[0].append(line)

    thm("wf", "wellFormed model = true")
    data(f"def savedDsl : Bytes := {lean_bytes(raw_dsl)}", "model")
    thm("dsl", "encodeDsl model = savedDsl")
    if observation is not None:
        data(lean_observation(observation), "model")
        thm("obs", "observationConsistent observations links model = true")
    for v in views:
        p = f"(project .{v} model)"
        status = (work / f"status.{v}.json").read_bytes()
        data(f"def savedStatus_{v} : Bytes := {lean_bytes(status)}", "model")
        thm(f"status_{v}", f"encodeClassified (classifyView .{v} model) = savedStatus_{v}")
        problems = (work / f"mermaid_problems.{v}.json").read_bytes()
        data(f"def savedProblems_{v} : Bytes := {lean_bytes(problems)}", "model")
        thm(f"problems_{v}", f'jarr ((mermaidProblems {p}).map jstr) ++ b!"\\n" = savedProblems_{v}')
        mmd = work / f"{v}.mmd"
        if mmd.exists():
            raw = mmd.read_bytes()
            where = f"mermaid_{v}"
            data(f"def savedMmd_{v} : Bytes := {lean_bytes(raw)}", where)
            data(f"def linesMmd_{v} : List Bytes := {lean_lines(raw)}", where)
            thm(f"mermaid_ok_{v}", f"mermaidRepresentable {p} = true", where)
            thm(f"mermaid_render_{v}", f"renderMermaid {p} = savedMmd_{v}", where)
            thm(f"mermaid_decode_{v}",
                f"decodeMermaidSubset savedMmd_{v} linesMmd_{v} = some {p}", where)
        svg = work / f"{v}.svg"
        if svg.exists():
            raw = svg.read_bytes()
            ids = "[" + ", ".join(lean_bytes(e["id"]) for e in doc["entities"]) + "]"
            where, decode = f"svg_{v}", f"svg_decode_{v}"
            for w in (where, decode):
                data(f"def savedSvg_{v} : Bytes := {lean_bytes(raw)}", w)
            data(f"def linesSvg_{v} : List Bytes := {lean_lines(raw)}", decode)
            thm(f"svg_render_{v}", f"renderSvg (layout {p}) = savedSvg_{v}", where)
            thm(f"svg_layout_{v}", f"layoutOk (layout {p}) = true", where)
            thm(decode, f"decodeSvgSubset savedSvg_{v} linesSvg_{v} {ids} = some {p}", decode)
    return {name: (head + "\n".join(src) + "\n" + "\n".join(f"#print axioms {t}" for t in thms) + "\n", thms)
            for name, (src, thms) in groups.items()}


def lean_observation(obs) -> str:
    def sym(o):
        return "none" if o.get("symbol") is None else f"(some .{SYM[o['symbol']]})"
    observations = ",\n".join(f"⟨{lean_bytes(o['id'])}, {sym(o)}⟩" for o in obs["observations"])
    links = ",\n".join(f"⟨{lean_bytes(l['item'])}, {lean_bytes(l['observation'])}⟩" for l in obs["links"])
    return (f"def observations : List Ob := [{observations}]\n"
            f"def links : List Link := [{links}]\n")


def load_observation(path: Path) -> dict:
    obs = strict_loads(path.read_bytes())
    _obj(obs, ["schema_version", "image", "observations", "links", "reviewed_area"], "observation")
    if not isinstance(obs["observations"], list) or not isinstance(obs["links"], list):
        raise DslError("observation: 配列が必要")
    for o in obs["observations"]:
        if not isinstance(o, dict) or not isinstance(o.get("id"), str):
            raise DslError("observation: idが必要")
        if o.get("symbol") is not None and o["symbol"] not in SYM:
            raise DslError(f"observation: 不正な記号 {o['symbol']!r}")
    for l in obs["links"]:
        _obj(l, ["item", "observation"], "link")
    return obs


def check_axioms(stdout: str, names: list[str]) -> list[str]:
    bad = []
    for name in names:
        match = re.search(rf"'{name}' (does not depend on any axioms|depends on axioms: \[([^\]]*)\])",
                          stdout)
        if match is None:
            bad.append(f"{name}: 公理の確認結果がない")
            continue
        used = {a.strip() for a in (match.group(2) or "").split(",") if a.strip()}
        if used - ALLOWED_AXIOMS:
            bad.append(f"{name}: {sorted(used - ALLOWED_AXIOMS)}")
    return bad


def size_problems(work: Path) -> list[str]:
    bad = []
    for path in list(work.glob("*.mmd")) + list(work.glob("*.svg")):
        raw = path.read_bytes()
        lines = raw.split(b"\n")
        if len(raw) > MAX_OUTPUT or len(lines) > MAX_LINES or max(map(len, lines)) > MAX_LINE:
            bad.append(f"上限超過: {path.name}")
    return bad


def prove_one(lean, name, source, thms, work) -> dict:
    path = f"proof.{name}.lean"
    (work / path).write_text(source, encoding="utf-8")
    try:
        run = run_lean(lean, [path], work)
    except subprocess.TimeoutExpired:
        return {"state": "not_run", "reason": f"{path}: {LEAN_TIMEOUT}秒で終わらなかった"}
    errors = [l for l in run.stdout.splitlines() + run.stderr.splitlines() if "error" in l]
    if run.returncode != 0 or errors:
        return {"state": "failed", "reason": " / ".join(errors[:5])[:800] or f"{path}: exit {run.returncode}"}
    bad = check_axioms(run.stdout, thms)
    if bad:
        return {"state": "failed", "reason": "; ".join(bad)}
    return {"state": "passed"}


def prove(lean, doc, raw_dsl, work, views, observation) -> dict:
    groups = proof_sources(doc, raw_dsl, work, views, observation)
    total = sum(len(t) for _, t in groups.values())
    with ThreadPoolExecutor(max_workers=PROOF_WORKERS) as pool:
        results = list(pool.map(lambda kv: prove_one(lean, kv[0], kv[1][0], kv[1][1], work), groups.items()))
    for state in ("failed", "not_run"):
        hit = [r["reason"] for r in results if r["state"] == state]
        if hit:
            return {"state": state, "reason": "; ".join(hit), "theorems": total}
    return {"state": "passed", "theorems": total}


def view_reports(work: Path, views, formats, formal) -> dict:
    out = {}
    for v in views:
        status = json.loads((work / f"status.{v}.json").read_text(encoding="utf-8"))
        problems = json.loads((work / f"mermaid_problems.{v}.json").read_text(encoding="utf-8"))
        entry = {"design_state": status["status"], "missing": status["missing"],
                 "formal_state": formal["state"], "omitted_by_view": ["attributes", "keys", "types"]
                 if v == "conceptual" else []}
        if status["status"] != "blocked":
            if "mermaid" in formats:
                entry["mermaid"] = "generated" if (work / f"{v}.mmd").exists() else "not_representable"
                if problems:
                    entry["mermaid_problems"] = problems
            if "svg" in formats:
                entry["svg"] = "generated"
                entry["label_crossings"] = int((work / f"label_crossings.{v}.txt").read_text())
        out[v] = entry
    return out


def cmd_canonicalize(args) -> int:
    doc = validate(strict_loads(Path(args.input).read_bytes()))
    target = Path(args.output)
    if target.exists() and not args.force:
        raise DslError(f"既に存在する: {target}")
    target.write_bytes(canonical(doc))
    print(json.dumps({"written": str(target), "entities": len(doc["entities"]),
                      "relationships": len(doc["relationships"]),
                      "unresolved": len(doc["unresolved"])}, ensure_ascii=False))
    return 0


def _emit(report: dict, code: int) -> int:
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return code


def cmd_generate(args) -> int:
    doc, raw = load_model(Path(args.model))
    if raw != canonical(doc):
        raise DslError("正規DSLではない。先に canonicalize で別ファイルへ保存して確定する")
    observation = load_observation(Path(args.observation)) if args.observation else None
    views, formats = views_of(args.view), wanted(args.format)
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    lean, reason = lean_ready()
    if lean is None:
        return _emit({"formal_state": "not_run", "reason": reason}, 4)
    work = Path(tempfile.mkdtemp(prefix=".work-", dir=outdir))
    keep = False
    try:
        (work / "gen.lean").write_text(generator_source(doc, views, formats), encoding="utf-8")
        try:
            run = run_lean(lean, ["--run", "gen.lean"], work)
        except subprocess.TimeoutExpired:
            return _emit({"formal_state": "not_run", "reason": "生成がタイムアウトした"}, 4)
        if run.returncode != 0:
            keep = True
            return _emit({"formal_state": "failed", "reason": (run.stdout + run.stderr)[:800],
                          "work": str(work)}, 1)
        (work / "gen.lean").unlink()
        (work / "model.er.json").write_bytes(raw)
        limits = size_problems(work)
        if limits:
            return _emit({"formal_state": "not_run", "reason": "; ".join(limits)}, 4)
        if observation is not None:
            shutil.copyfile(args.observation, work / "observation.json")
        formal = prove(lean, doc, raw, work, views, observation)
        report = {"formal": formal, "views": view_reports(work, views, formats, formal),
                  "observation_consistency": "passed" if observation is not None
                  and formal["state"] == "passed" else "not_run",
                  "image_comparison": "not_run", "scope": "形式検証はDSL以降。画像の解釈は別途照合する",
                  "reproduces_image_or_adds_design": args.provenance}
        (work / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n",
                                          encoding="utf-8")
        if formal["state"] != "passed":
            keep = True
            report["work"] = str(work)
            return _emit(report, 1 if formal["state"] == "failed" else 4)
        for path in sorted(work.iterdir()):
            os.replace(path, outdir / path.name)
        return _emit(report, 0)
    finally:
        if not keep:
            shutil.rmtree(work, ignore_errors=True)


def cmd_verify(args) -> int:
    """保存済みの出力ディレクトリを読み直して再検査する（改変の検出）。"""
    outdir = Path(args.outdir)
    doc, raw = load_model(outdir / "model.er.json")
    views = [v for v in VIEWS if (outdir / f"status.{v}.json").exists()]
    obs_path = outdir / "observation.json"
    observation = load_observation(obs_path) if obs_path.exists() else None
    lean, reason = lean_ready()
    if lean is None:
        return _emit({"formal_state": "not_run", "reason": reason}, 4)
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        for path in outdir.iterdir():
            if path.is_file():
                shutil.copyfile(path, work / path.name)
        formal = prove(lean, doc, raw, work, views, observation)
    return _emit(formal, 0 if formal["state"] == "passed" else 1)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("canonicalize")
    p.add_argument("input")
    p.add_argument("output")
    p.add_argument("--force", action="store_true")
    p.set_defaults(func=cmd_canonicalize)
    p = sub.add_parser("generate")
    p.add_argument("model")
    p.add_argument("--outdir", required=True)
    p.add_argument("--format", choices=("mermaid", "svg", "both"), default="mermaid")
    p.add_argument("--view", choices=("conceptual", "logical", "both"), default="both")
    p.add_argument("--observation")
    p.add_argument("--provenance", choices=("image_only", "image_and_supplement"), default="image_only")
    p.set_defaults(func=cmd_generate)
    p = sub.add_parser("verify")
    p.add_argument("outdir")
    p.set_defaults(func=cmd_verify)
    p = sub.add_parser("check-image")
    p.add_argument("image")
    p.add_argument("model")
    p.add_argument("--out", required=True)
    p.add_argument("--observation-out")
    p.set_defaults(func=lambda a: __import__("imagecheck").run(a))
    p = sub.add_parser("compare")
    p.add_argument("a")
    p.add_argument("b")
    p.set_defaults(func=lambda a: __import__("imagecheck").compare_cli(a))
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except DslError as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    sys.exit(main())
