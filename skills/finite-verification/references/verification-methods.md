# Complementary verification methods

Mutation asks whether a check notices one deliberately introduced fault. Input generation explores more cases; an oracle judges their behavior. Combine these dimensions when they address different risks. Keep the criterion, bounded run and honest gap reporting from SKILL.md.

## Select by the behavior at risk

| Method | Use when | Required oracle or limitation |
| --- | --- | --- |
| Example/boundary/regression | A concrete result, limit or reproduced bug matters | Independent expected output/state; cover relevant equivalence classes and boundary neighbors. |
| Property-based | A rule should hold across a described input domain | A specification-derived invariant; include meaningful valid and invalid partitions. Passing samples do not prove universality. |
| Fuzzing | Parsers, decoders, protocols or other broad input surfaces need exploration | Explicit invariants, a differential oracle, or a stated no-crash/no-hang/memory-safety criterion. Random bytes alone do not judge correctness. |
| Differential | An independent reference or compatible implementation exists | Same semantics, domain and normalization; agreement may preserve a shared bug. A Lean reference follows lean-gate.md. |
| Metamorphic | Exact outputs are difficult but input/output relations are specified | A justified relation such as order invariance or idempotence where the specification requires it. Pair round trips with an independent anchor. |
| Stateful/model-based | Results depend on operation history or lifecycle | An independent state model and invariants after meaningful transitions, with bounded sequence length. |
| Integration/contract/E2E | Serialization, persistence, API boundaries or user workflows may break | Observe actual outputs and state across the relevant real boundary; mocks alone cannot establish integration. |
| Fault injection/concurrency | Recovery, retries, cancellation or ordering is a criterion | Inject the relevant failure or control the schedule; check final state, invariants and recovery, not only lack of exceptions. |
| Static analysis/types | Supported source patterns or type errors could expose faults cheaply | Existing enabled rules, target files and baseline. Diagnostics are tool findings; no diagnostics does not establish runtime correctness. |
| Dynamic sanitizers | Native memory errors, undefined behavior or data races are relevant | A supported instrumented build and exercised paths. Sanitizers are dynamic checks, not static analysis; separate incompatible modes as the tool requires. |

Prefer the project's framework and commands. Add a second method only for a named gap in the current evidence. Existing criteria determine which methods apply; a method's availability does not create a new requirement.

## Property and fuzz runs

Before running, name the subject and oracle and bound the work. Use the framework's finite example/execution limit and a wall-time limit; also cap input size, operation-sequence length and memory where relevant. Avoid unrestricted default fuzz loops. Use an external process deadline if a framework limit does not stop a hung subject.

- Seed with relevant examples, boundaries and previously observed failures. For structured inputs, include valid seeds or a structured generator as well as malformed cases; reaching only the rejection path is weak evidence for deeper semantics.
- Check generated values against specification-derived invariants or relations. Keep assumptions explicit and inspect rejected-case counts or health warnings. A run with no accepted cases is not a pass; a restrictive domain leaves the excluded behavior unverified.
- Prefer shrinking/minimization supported by the existing tool. Bound that work too. Preserve a non-secret failing input or operation sequence and the command, tool version, options and seed needed to replay it. A seed alone may not reproduce across versions or a changing corpus.
- Reproduce a found failure with its saved input before attributing it. An unexplained or non-reproducing crash/timeout stays inconclusive and is reported, not silently counted as a pass. Fix reproducible faults in scope and keep their minimal replay case as a criterion-linked regression; defer unrelated discoveries.
- For the required implementation mutation, replay a fixed case that exercises the mutated behavior. Fuzzer mutations of input data are not implementation mutations. One authored property/target gets one such check; its generated examples do not each need one.
- Report the actual accepted examples/executions and elapsed time. Replaying a corpus is regression evidence, not a fresh fuzz campaign. Search coverage can expose missed paths but is neither an oracle nor a proof that checks are strong.

For example, a parser change may need a valid boundary example, structured inputs with a semantic invariant, malformed-input fuzzing with a no-crash oracle, and one implementation mutation per new or changed test/target. A small fixed-output change may need only its focused examples and mutation. Choose the set from the actual criteria.

## Static checks and tool collections

Read [static-analysis-tools.md](static-analysis-tools.md) for the language-specific shortlist, cross-language analyzers, execution tools, selection procedure and required evidence. Use only its relevant rows.

Use the repository's existing lint, compiler/typecheck and analysis commands first. Keep checks diagnostic during verification; avoid applying bulk autofixes or enabling every rule just to obtain more findings. Toolchain/dependency, hook, CI and external-service changes keep their own authorization boundaries.

Static tools may inspect shipped code and relevant test source for suspicious constructs; that is allowed analysis, not new executable code testing a test suite. They do not replace the rough review or demonstrate that a behavioral assertion would detect a particular fault. Apply the mutation rule to authored tests/targets, not to each diagnostic emitted by a tool.

## Primary references

Consult these for tool-specific settings when using the corresponding method; they do not mandate installing a tool:

- [LLVM libFuzzer](https://llvm.org/docs/LibFuzzer.html): coverage-guided input generation, corpora, artifacts and finite run/resource options.
- [Hypothesis quickstart](https://hypothesis.readthedocs.io/en/latest/quickstart.html): generated properties, domains and finite example counts.
- Static tool sources are linked beside their selection guidance in [static-analysis-tools.md](static-analysis-tools.md).
