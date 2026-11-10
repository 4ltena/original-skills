# Using the Lean 4 kernel

Lean is used at two levels. Checking a table of expected values is light and replaces test-of-test code. Proving a criterion for all inputs is an escalation. Both check only Lean code: the shipped code is linked to them by an ordinary test, not by the kernel. Lean is not installed by default; installing the toolchain needs the user's authorization.

## Shared by both: the definition

Write the specification as a Lean definition from the request and the acceptance criteria, and show it in the report; do not wait for approval. The kernel confirms agreement with the definition, not that the definition says the right thing. Keep it a plain function of the inputs, without I/O, time or external state.

## Expected-value table

Use when a test's expected values come from a calculation that could be wrong: rounding, money in minor units, date arithmetic, a parser's output.

1. Put the cases in one JSON table that both the shipped tests and Lean read:
   `{"spec": "Spec.roundDiv", "cases": [{"args": [-7, 2], "expected": -3}]}`.
   Values are integers, strings, booleans and lists of them, and the definition's argument and result types need `ToJson` instances (`Int`, `Nat`, `String`, `Bool`, `List`). `Fin`, `UInt8` and tuples fail closed. Represent money in integer minor units; `Float` cannot be decided by the kernel.
2. Keep the definition in a Lake project with a pinned `lean-toolchain`, then run:
   `<verified-python> <this skill>/scripts/lean_oracle.py TABLE.json --project LAKE_DIR --import Spec`
   Use the host's verified Python 3.8 or later. `--timeout SECONDS` (default 600) bounds `lake build` and the check.
   The script writes one `theorem case_<i> ... := by decide +kernel` per row into a temporary file and checks it. It fails a row when the kernel rejects it, when `#print axioms` lists anything beyond `propext`, `Classical.choice` and `Quot.sound` (this catches `sorry` and `native_decide`), or when the values Lean echoes back differ from the table. It also fails when the number of rows checked differs from the number of rows in the table.
3. Exit code 0 means every row agrees with the definition. Structural and well-founded recursion both reduce with `decide +kernel`; a `partial` definition cannot be reduced and fails rather than passing.
4. Mutate the shipped implementation once to show that the shipped test reading the table fails. The link from the table to the shipped code is that test alone.

Do not write tests for the table or the script. A table row that fails is fixed in whichever of the table and the definition disagrees with the request. When the request does not settle it, report the disagreement as a gap instead of guessing.

## Proof of a criterion for all inputs

### Escalate only when both hold

- The target is a small pure function.
- The criterion quantifies over all inputs, and the remaining risk after example, property and table checks is unacceptable, such as arithmetic on money, a parser invariant or a security decision.

Otherwise stay with tests and report the unproved universal claim as unverified.

### Gates

1. **Statement from the criterion.** A correct proof of the wrong statement is worthless. Write the statement in terms of the definition, not the proof's internals, check that it says what the criterion says, and show it in the report.
2. **Satisfiable hypotheses.** A theorem with contradictory hypotheses proves anything. Prove one `example` that instantiates the hypotheses with concrete values.
3. **No escape hatches.** Run `#print axioms` on every delivered theorem. Accept only `propext`, `Classical.choice` and `Quot.sound`. `sorryAx` means an unfinished proof; `native_decide` appears as an auxiliary axiom whose name depends on the Lean version; any other axiom is an unproved assumption.
4. **Link to the shipped code.** Unless the shipped code is the Lean code, the proof covers only the Lean definition. Keep one differential test that runs the compiled Lean definition and the shipped implementation on the same generated inputs and requires equal results. Mutate the shipped implementation once to show the differential test fails.
5. **Bounded search.** Allow at most three proof attempts with different strategies. Then stop and report the criterion as unproved, with the goal state at which the attempts stopped. Do not weaken the statement to make it provable. If only a weaker statement is proved, report the criterion as unproved and name the weaker claim.

After these gates pass, the criterion is done. Do not add tests of the proof.
