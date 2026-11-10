---
metadata:
  author: "4ltena"
  version: "1.7"
name: finite-verification
description: Use when writing or changing tests or fuzz targets for code you are implementing, choosing complementary verification methods, deciding whether verification is done, or rerunning checks after a fix. Review each changed test's adequacy and bound the work without writing tests of tests. Also use when existing tests' adequacy is in question or Lean may check expected values or prove a criterion.
---

# Give verification a finite end

Asking "is this test valid?" with another test starts a regress that never ends: the new test needs a test too. The regress ends only when verification is grounded in something that is not a test. Accept exactly three grounds:

1. **Acceptance criteria**, fixed before writing tests. They come from the request or the approved specification, not from tests.
2. **One deliberate implementation mutation per test or fuzz target**, following `mutation-check` including its protection of the starting state. This demonstrates detection of that fault, not overall correctness or coverage of other faults. Mutating fuzz inputs is input exploration and does not replace this check.
3. **The Lean kernel.** It checks expected values against a Lean definition of the specification, or proves a criterion for all inputs. Nothing tests a kernel check; trust rests on the checker and the definition, which the report shows. Read `references/lean-gate.md` before using it.

Every test or fuzz target you write or change gets the rough review below automatically, and so does any other test whose adequacy is in question. It is weaker than a ground, but it is reading, not code, so it starts no regress. Fuzzing, property, differential, metamorphic, stateful and integration tests exercise the shipped code against criteria; they are not tests of tests.

Bend is a parallel runtime, not a proof checker. Tests written in it still need tests, so it does not end the regress.

Within this skill — writing tests and verifying them — do not stop to ask the user for approval. Decide, act and record the decision in the report. Changes outside that scope, such as installing a toolchain, keep their own approval rules.

## Before writing tests

Take the acceptance criteria from the request or the approved specification; do not invent them. For each, identify the plausible fault, the input or state space, and the oracle (the rule that decides pass or fail). Choose complementary evidence for distinct risks, reusing the project's existing tools:

- example, boundary and regression tests for specific behavior;
- property-based tests for invariants over generated inputs;
- bounded fuzzing for malformed or complex inputs, with an explicit oracle;
- differential tests against an independent reference, or metamorphic tests of specification-derived input/output relations;
- stateful/model-based tests for operation sequences, fault injection for recovery criteria, and integration/contract/E2E tests for real boundaries;
- existing lint, type and static analysis checks; add relevant sanitizers to dynamic runs when supported;
- a Lean-checked table of expected values when an expected value comes from a calculation that could itself be wrong;
- a proof only when the escalation conditions in `references/lean-gate.md` all hold.

Read [references/verification-methods.md](references/verification-methods.md) when choosing or extending methods beyond examples and mutation. Select methods for their additional evidence, not to fill a checklist; do not run every method on every change. Static diagnostics and coverage guide verification but do not establish behavioral correctness.

When choosing static checks, read the relevant language and purpose rows in [references/static-analysis-tools.md](references/static-analysis-tools.md). It covers lint, type checks, bug/security analysis and tools that run other checkers. Reuse configured checks, identify their effective rules and scope, and report unsupported or skipped checks as gaps. The catalog does not require installing tools or running them all.

Before generated or exploratory runs, record finite limits for examples, steps or executions and wall time, plus relevant input-size and memory limits. Record the target, oracle and replay information. Prefer existing project limits; otherwise choose a small explicit budget proportional to the change. A completed budget is sampled evidence, not proof for all inputs. Do not extend it merely because the run is green or coverage is still growing.

Write a test only when it maps to a criterion and would fail for a plausible broken implementation. Do not write:

- tests of tests, or assertions about the test suite itself;
- tests that restate the implementation's expressions;
- tests that map to no criterion.

Right after writing or changing each test, run the rough review on it without being asked.

Test-of-test code is code whose subject is tests, test data or test helpers: recomputing stored expected values merely to validate that table, asserting that another test fails under mutation, testing fixtures or helpers, or checking test counts or names. A differential test runs the shipped code against an independent specification or reference implementation on the same inputs; that is allowed. A copied implementation or a reference that calls the subject is not an independent oracle.

If a needed check maps to no criterion, the criteria are incomplete. Add the criterion yourself when it follows from the request, and list it in the report as added; otherwise do not write the test.

## Remove existing test-of-test code

List each instance and its replacement in the report; do not wait for approval:

- a check of expected values moves into a table verified by `scripts/lean_oracle.py`;
- a check of detection power is deleted; record its mutation result in the report instead;
- a test of a helper goes away with the helper when the helper can be inlined or removed; otherwise keep it and list it in the report as an added criterion.

## Rough review of test adequacy

It runs automatically on every test or fuzz target you write or change, as soon as it is written. For generated tests, review the property or harness once, not each generated input. Run it also on existing tests whose adequacy is in question. It produces no code whose subject is tests. Mutations it runs are temporary edits to the implementation, reverted afterwards.

Read each test once and check:

1. **Criterion** — it maps to an acceptance criterion, or its intent is clear from its name and body.
2. **Reached oracle** — its assertion or instrumentation-based check actually runs on the subject: no skipped assertion, swallowed failure, empty input set or generator that rejects every case. Confirm that generated tests reach the claimed behaviors, not only harness setup.
3. **Independent expectation** — the expected value, invariant or metamorphic relation comes from the specification or a justified independent reference, not from repeating the subject's expression. Round trips alone can hide matching encoder/decoder bugs.
4. **Observed behavior** — it checks output, state or a stated safety criterion, not merely a mock echoing its own setup; mocks do not replace the subject. Absence of crashes, hangs or sanitizer findings is valid evidence only for that explicit robustness criterion, not functional correctness.
5. **Discrimination** — name one plausible bug in the subject, such as an off-by-one, a wrong sign, a missed branch or an ignored argument, and judge whether this test would fail for it. Loose checks like `is not None` or `>= 0`, and trivial inputs where many bugs give the same answer, fail this check.

Classify each test:

- **sound** — all five hold;
- **weak** — the oracle runs but check 3, 4 or 5 fails;
- **vacuous** — check 2 fails, or the test can pass whatever the subject does.

A weak or vacuous test you wrote or changed is fixed once and then goes straight to its mutation; do not review it again. An existing test outside the change is reported, not fixed. When a judgment on an existing test is uncertain and one mutation is cheap, run it; its result replaces the judgment. Review each test once; review an existing test again only after it or its subject changes.

For a generated test or fuzz target, use a fixed input or saved replay case that reaches the deliberate implementation mutation; do not rely on a lucky random rediscovery. Check one mutation per authored test or target, not per generated input or corpus file.

## Stop condition

Verification is done when this state holds:

- every criterion has passing evidence from the selected methods or a reported gap;
- each new or changed test or fuzz target has a rough-review classification;
- each new or changed test or fuzz target has failed once against a deliberate implementation mutation, or its surviving mutation has been reported as a gap after the bounded retry;
- existing tests whose adequacy was in question have a classification;
- selected generated/exploratory runs have reached their declared stopping condition or have a reported shortfall; relevant replay inputs and observed limits are recorded.

Compare the current state with this one before each additional check. Once it holds, stop. Resume only for a new code change, a reproducible new failure in the changed behavior, evidence that contradicts a criterion, or an explicit user request. A failure that does not reproduce or lies outside the change is reported, not chased. Rerunning green checks, adding edge cases nobody asked for, and rephrasing existing assertions are not reasons to resume.

When a mutation survives, fix that test once and repeat its mutation. Do not add a second test to check the first. If it survives again, report the gap. A reported gap ends verification of that criterion just as passing evidence does.

## Re-running checks after a fix

When a check run reports failures and you fix them, every later run covers two items only:

1. **The failed units, on their own** — the tests that failed, the files or targets that `fmt` or the linter flagged — rerun with the fix in place, until they pass.
2. **One whole run** of the gate the change must pass (the full test command, or `fmt`/`clippy` over the whole workspace), once, after those units pass.

Units that passed in the earlier run are not rerun on their own; their result stands. They are back in scope only when the fix changes code they exercise, and then they count as failed units. Rerun failed units after each fix; run the whole gate once at the end, not after every fix. A failure caused by the environment (paths, permissions, build settings) is fixed in the environment, then the same failed units are rerun; report the cause.

Never write a test of a test, even on request. When the user asks for one, point to the rough review already run on the new tests, run it on any other tests in question, and offer a mutation for a test the user still doubts.

## Report

List each criterion with its methods, oracle, evidence, deliberate implementation mutation result, and remaining gaps. For generated runs include the tool/version, seed or replay artifact, corpus/domain, accepted-case or execution count, actual duration and configured limits. State whether coverage was measured and which paths remain unexercised; never turn a coverage percentage or zero findings into a correctness claim. List relevant static checks separately, including their enabled rules and excluded scope.

For a rough review, list weak and vacuous tests with the failed check and the bug that would slip through, and the count of sound tests; mark these as review judgments, not mutation results. Show Lean definitions and theorem statements used, added criteria and removed tests. Distinguish your own checks from independent review. Unverified scope is a valid outcome; state it rather than adding tests to hide it.
