"""Check a table of expected values against a Lean spec with the Lean kernel.

Usage: lean_oracle.py TABLE.json --project LAKE_DIR --import MODULE [--timeout SECONDS]
TABLE: {"spec": "Mod.fn", "cases": [{"args": [...], "expected": ...}]}
Values: integers, strings, booleans and lists of them. Exit 0 pass, 1 fail, 2 bad input.
"""
import argparse
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

STANDARD_AXIOMS = {'propext', 'Classical.choice', 'Quot.sound'}


def lit(value):
    if type(value) is bool:
        return 'true' if value else 'false'
    if type(value) is int:
        return f'({value})'
    if type(value) is str:
        out = []
        for ch in value:
            if ch in '\\"':
                out.append('\\' + ch)
            elif ch == '\n':
                out.append('\\n')
            elif ord(ch) < 0x20 or ord(ch) == 0x7f:
                out.append(f'\\x{ord(ch):02x}')
            else:
                out.append(ch)
        return '"' + ''.join(out) + '"'
    if type(value) is list:
        return '[' + ', '.join(lit(v) for v in value) + ']'
    raise ValueError(f'unsupported value: {value!r}')


def canonical(value):
    return json.dumps(value, ensure_ascii=False, separators=(',', ':'))


def generate(table, module):
    spec, cases = table['spec'], table['cases']
    if not re.fullmatch(r'[A-Za-z_][\w.]*', spec) or not re.fullmatch(r'[A-Za-z_][\w.]*', module):
        raise ValueError('spec and module must be Lean identifiers')
    if not isinstance(cases, list) or not cases:
        raise ValueError('cases must be a non-empty list')
    if not all(isinstance(case, dict) and isinstance(case.get('args'), list) and 'expected' in case for case in cases):
        raise ValueError('each case needs an args list and an expected value')
    arities = {len(case['args']) for case in cases}
    lines = [f'import {module}', 'import Lean.Data.Json']
    for n in sorted(arities):
        # The echo takes the spec itself so every literal is elaborated at the spec's types.
        names = [f'a{i}' for i in range(n)]
        types = [f'α{i}' for i in range(n)] + ['ρ']
        binders = ' '.join(f'{{{t}}} [ToJson {t}]' for t in types)
        arrow = ' → '.join(types)
        params = ' '.join(f'({a} : α{i})' for i, a in enumerate(names)) + ' (e : ρ)'
        items = ', '.join([f'toJson {a}' for a in names] + ['toJson e'])
        lines.append(f'open Lean in def oracleEcho{n} {binders} (_ : {arrow}) {params} : String := (Json.arr #[{items}]).compress')
    for i, case in enumerate(cases):
        args = ' '.join(lit(a) for a in case['args'])
        expected = lit(case['expected'])
        lines.append(f'theorem case_{i} : {spec} {args} = {expected} := by decide +kernel')
        lines.append(f'#print axioms case_{i}')
        lines.append(f'#eval IO.println ("ECHO {i} " ++ oracleEcho{len(case["args"])} {spec} {args} {expected})')
    return '\n'.join(lines) + '\n'


def check(table, output, returncode):
    cases = table['cases']
    failures = [] if returncode == 0 else [f'lean exited {returncode}']
    axioms, echoes = {}, {}
    # split('\n'), not splitlines(): Lean leaves U+2028 and U+0085 raw inside echoed strings.
    for line in output.split('\n'):
        if m := re.match(r"'case_(\d+)' depends on axioms: \[(.*)\]$", line):
            axioms[int(m[1])] = {a.strip() for a in m[2].split(',')}
        elif m := re.match(r"'case_(\d+)' does not depend on any axioms$", line):
            axioms[int(m[1])] = set()
        elif m := re.match(r'ECHO (\d+) (.*)$', line):
            echoes[int(m[1])] = m[2]
    for i, case in enumerate(cases):
        if i not in axioms:
            failures.append(f'case {i}: not checked by Lean')
        elif extra := axioms[i] - STANDARD_AXIOMS:
            failures.append(f'case {i}: non-standard axioms {sorted(extra)}')
        want = canonical(case['args'] + [case['expected']])
        got = echoes.get(i)
        try:
            read = canonical(json.loads(got)) if got is not None else None
        except ValueError:
            read = None
        if read != want:
            failures.append(f'case {i}: Lean read {got}, table says {want}')
    if len(axioms) != len(cases) or len(echoes) != len(cases):
        failures.append(f'{len(cases)} rows, Lean checked {len(axioms)} and echoed {len(echoes)}')
    return failures


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('table')
    parser.add_argument('--project', required=True)
    parser.add_argument('--import', dest='module', required=True)
    parser.add_argument('--timeout', type=int, default=600)
    args = parser.parse_args()
    try:
        table = json.loads(Path(args.table).read_text(encoding='utf-8'))
        source = generate(table, args.module)
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f'invalid table: {error}', file=sys.stderr)
        return 2
    project = Path(args.project)
    subprocess.run(['lake', 'build', args.module], cwd=project, check=True, timeout=args.timeout)
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / 'OracleCases.lean'
        path.write_text(source, encoding='utf-8')
        run = subprocess.run(['lake', 'env', 'lean', str(path)], cwd=project, capture_output=True,
                             text=True, timeout=args.timeout)
    failures = check(table, run.stdout + run.stderr, run.returncode)
    for failure in failures:
        print(failure)
    if failures and run.returncode != 0:
        print(run.stdout + run.stderr, file=sys.stderr)
    print(f'{len(table["cases"]) if not failures else 0}/{len(table["cases"])} cases verified')
    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(main())
