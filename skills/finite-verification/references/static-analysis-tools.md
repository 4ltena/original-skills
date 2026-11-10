# Static verification: tool selection and evidence

Official sources checked on 2026-10-27 (Asia/Tokyo). This is a shortlist for common ecosystems, not an installation list, exhaustive catalog or popularity ranking. Read only the rows relevant to the change. Installed versions, editions, enabled rules and repository configuration determine the actual checks available.

## Separate the kinds of evidence

- **Compiler/type checks** detect violations of the language or configured type model. Annotations, stubs, unchecked code and permissive settings limit the result.
- **Lint and bug analysis** detect suspicious constructs, API misuse and rule violations. Formatting success is style evidence, not behavioral evidence.
- **SAST** (static application security testing) looks for security-relevant patterns and data/control-flow paths. A finding is a candidate to assess in context; zero findings does not establish absence of vulnerabilities.
- **IaC/configuration checks** examine declared settings, not a deployed system's actual state.
- **Execution tools** run other checkers. Their value is consistent configuration and execution; wrapping one analyzer twice does not create two independent analyses.

Fuzzing, example/property tests and sanitizers exercise running code and belong to the dynamic methods in verification-methods.md. Dependency-vulnerability, license and secret scans answer other questions; report them separately if required. Ordinary static checks do not invoke a broader security audit by themselves.

## Language-specific shortlist

| Target | Tools and primary sources | Choose for / inspect before accepting the result |
| --- | --- | --- |
| Python: lint | [Ruff](https://docs.astral.sh/ruff/), [rule families](https://docs.astral.sh/ruff/rules/) | Common errors and conventions. Ruff reimplements rules from multiple linters, including flake8-bugbear (`B`) and flake8-bandit (`S`); it does not run those original tools. Inspect selected/ignored rules, target Python version and excluded paths. |
| Python: types | [mypy](https://mypy.readthedocs.io/en/stable/) or [Pyright](https://microsoft.github.io/pyright/) | Type consistency. Prefer the checker already configured; use both only for a concrete additional requirement. Inspect strictness, untyped code, imports and stubs. Ruff lint success is not this evidence. |
| Python: security patterns | [Bandit](https://bandit.readthedocs.io/en/latest/) | AST-based security checks. Inspect plugins, severity/confidence filters and skips. Its checks overlap with Ruff's `S` family; compare effective coverage before adding a duplicate run. |
| JavaScript/TypeScript: types | [TypeScript compiler](https://www.typescriptlang.org/docs/handbook/intro.html) | Static type checking through the project's typecheck command. Inspect tsconfig, project references, JavaScript checking and excluded files; linting or transpiling alone does not establish that type checking ran. |
| JavaScript/TypeScript: lint | [ESLint](https://eslint.org/docs/latest/use/core-concepts/) or [Biome](https://biomejs.dev/linter/) | ESLint provides configurable rules/parsers/plugins; Biome provides its own static lint rules alongside formatting tools. Preserve the project's choice, framework support and enabled checks; do not assume the tools or their rule sets are interchangeable. Retain the applicable compiler/typecheck step. |
| Rust | [Clippy](https://doc.rust-lang.org/clippy/) | Common mistakes and code-quality checks alongside rustc. Match the intended workspace, targets, features and toolchain. Check enabled lint groups; do not enable every restriction/pedantic lint merely to increase findings. |
| C/C++: Clang checks | [clang-tidy](https://clang.llvm.org/extra/clang-tidy/), [Clang Static Analyzer](https://clang.llvm.org/docs/ClangStaticAnalyzer.html) | clang-tidy includes lint/bug checks and can invoke Clang Static Analyzer checks; the analyzer uses path-sensitive, interprocedural symbolic analysis. Preserve compilation-database flags, defines, headers and target. Do not count the same analyzer checks through both entrypoints as independent evidence. |
| C/C++: complementary analysis | [Cppcheck](https://cppcheck.sourceforge.io/) | Bug and undefined-behavior analysis that may complement compiler/Clang checks. Supply the project's build/configuration context and inspect exclusions. A partial configuration or unsupported construct limits the conclusion. |
| Go | [go vet](https://pkg.go.dev/cmd/vet), [Staticcheck](https://staticcheck.dev/) | Suspicious constructs and additional bug, simplification and performance checks. Match modules, build tags, platform and package scope. Both are static diagnostics; vet explicitly uses heuristics rather than guaranteeing correctness. |
| Java | [SpotBugs](https://spotbugs.readthedocs.io/en/stable/introduction.html) | Bug patterns in compiled Java bytecode. Confirm that the analyzed class files correspond to current sources and the intended build, dependencies and filters. A successful source compile and a successful bytecode analysis are different results. |
| C# / Visual Basic | [.NET/Roslyn analyzers](https://learn.microsoft.com/en-us/dotnet/fundamentals/code-analysis/overview) | Code-quality and style diagnostics in the .NET toolchain. Inspect SDK, target frameworks, analyzer packages, .editorconfig and rule severities. Editor suggestions and command-line build diagnostics can differ. |
| Swift | [SwiftLint](https://realm.github.io/SwiftLint/) | Swift style and conventions. Inspect rule configuration and selected mode; keep compiler/type checking separate. A style-clean result does not validate lifecycle, concurrency or UI behavior. |
| PHP | [PHPStan](https://phpstan.org/user-guide/getting-started) or [Psalm](https://psalm.dev/) | Static type/code analysis. Prefer the existing project tool; inspect analysis level, target PHP version, framework extensions/stubs, bootstrap configuration and baseline. A permissive baseline leaves those findings outside the current result. |
| Shell | [ShellCheck](https://www.shellcheck.net/) | Shell-script mistakes and suspicious constructs. Match the declared shell dialect and sourced-file context. A syntax/style pass does not show that commands produce the intended effects. |
| GitHub Actions | [actionlint](https://rhysd.github.io/actionlint/) | Static checking of workflow files. Use it when workflows change; validate against their actual configuration. It does not establish that actions, credentials, hosted environments or services work at runtime. |
| Infrastructure/configuration | [Checkov](https://www.checkov.io/1.Welcome/What%20is%20Checkov.html) | IaC misconfiguration policies for formats such as Terraform, Kubernetes and Dockerfiles. Select applicable frameworks and policies; declared configuration is not proof of deployed state. |

## Cross-language analysis

| Tool and primary source | When it adds evidence | Material limits |
| --- | --- | --- |
| [Semgrep](https://semgrep.dev/docs/semgrep-code/overview) | Existing rules for code/security patterns and supported data-flow checks across languages. | Record the exact engine/edition, rules and language support. Do not attribute hosted or commercial capabilities to a different local edition. Reuse reviewed local configuration rather than silently downloading or enabling a new ruleset. |
| [CodeQL](https://codeql.github.com/docs/codeql-overview/about-codeql/) | Queries over an extracted code database, including security and data-flow checks. | Match database/source revision, extraction/build context, language and query suite. Database creation may involve a build. Check existing availability and authorization; do not assume a tool or service is usable merely because its documentation is public. |
| [SonarQube](https://docs.sonarsource.com/sonarqube-server/) | An existing centralized code-quality/security analysis workflow with configured rules and profiles. | Inspect the actual project profile, edition, exclusions and analysis revision. A green configured quality gate establishes only that gate's conditions; it does not prove the task's acceptance criteria or authorize new publication/upload steps. |

These choices do not require running three security scanners on ordinary edits. Use an existing applicable analyzer when its rules address a named risk; add a further tool only for a specific evidence gap within scope.

## Tools that run multiple checks

| Tool and primary source | What it combines | What to inspect |
| --- | --- | --- |
| [MegaLinter](https://megalinter.io/latest/supported-linters/) | Multiple language, format and configuration linters, packaged together. | Actual flavor/image/version, enabled linters, included files, fix behavior and each tool's outcome. A summary can omit disabled or skipped checks. Avoid duplicate standalone runs of the same configured analyzer. |
| [golangci-lint](https://golangci-lint.run/) | Multiple Go linters with shared execution/configuration and caching. | Version-specific configuration, enabled linters, build tags, exclusions and per-linter results. Do not assume every advertised linter is enabled. |
| [pre-commit](https://pre-commit.com/) | Configured hooks and their environments across languages. | Hook revisions, entrypoints, selected files, skips and actual effects. Hooks can format files or download/build environments; this is not itself an analyzer or a guarantee of diagnostic-only execution. |

Choose the repository's current entrypoint rather than introducing another wrapper. A collection, hook framework or new CI workflow is an infrastructure choice, not a prerequisite for using this skill. No blanket all-tools/all-rules requirement follows from this catalog.

## Apply with a finite scope

1. **Read existing configuration.** Find the documented verification scripts/CI commands and only relevant config files. Identify language/runtime/compiler versions, analysis targets, effective rule families, exclusions and baselines. Inspect what a package script, plugin, bootstrap or hook will actually execute.
2. **Map checks to the change.** Choose the existing compiler/type checker, lint/bug analyzer and any security/configuration checks that address the affected behavior or boundary. Record what each adds and where it overlaps. Preserve the user's established choices.
3. **Bound execution.** Use the smallest valid target for iteration. Some type/data-flow analyses need package, project or compilation-unit context; do not force file-only checking if it loses required context. Set a wall-time limit and supported resource limits for expensive analysis. Use existing caches without confusing stale artifacts with a current result. Before completion, run the relevant existing verification scope once; do not keep rerunning green checks.
4. **Keep effects explicit.** Static describes the analysis, not all effects of its launcher. Build-backed analyzers, configuration/plugins and hook environments can execute code, write outputs or fetch dependencies. Prefer existing diagnostic modes; do not enable autofix, broad suppression, new dependencies, containers, hooks, uploads or CI changes solely to get a green report. Apply the host's ordinary execution/network/approval rules to the actual commands.
5. **Interpret findings.** Check the rule, source location and actual context before calling a diagnostic a defect. Fix confirmed in-scope problems and rerun the affected check; report suspected false positives with reasons. A tool/setup failure, empty applicable ruleset, skipped run, timeout or unsupported target is a gap, not a pass. Record unrelated/pre-existing findings without expanding the task. Do not weaken rules or enlarge baselines just to pass.
6. **Close against criteria.** Attach the static evidence to its criterion alongside any dynamic evidence. Report what was analyzed and what remains unknown, then use SKILL.md's stop condition. Static diagnostics do not need one implementation mutation each; authored behavioral tests and fuzz targets retain their own mutation requirement.

## Report the effective check

Record tool/version/edition, exact command, source revision or task snapshot, relevant configuration and rule selection, target/build context, excluded scope and baseline, exit status and substantive diagnostics. Include skips, setup errors and time/resource limits reached. Distinguish a source review, a successfully configured tool, a completed static run, a dynamic test and independent review. Never report that a tool ran or improved defect detection merely because it appears in this catalog.
