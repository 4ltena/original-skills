# e2e — evidence-driven evaluation

This directory preserves the four behavioural cases that caught real
growth-loop defects: duplicate learning, confirmation-gated forgetting,
learn/journey target agreement, and dishonest profile writes. Their predicates
remain artifact-based: changed Skill directories, deterministic `gl-journey`
lookup, file existence, and persisted profile content. They do not grade prose.

## Three offline-safe stages

```text
python3 -B e2e/run_e2e.py prepare --host claude --output /private/tmp/growth-fixture
python3 -B e2e/run_e2e.py request --fixture /private/tmp/growth-fixture/fixture.json \
  --output /private/tmp/growth-request.json --host claude --model model-id --runner native-host \
  --runner-receipt '{"runner":"native-host","verified":true}'
python3 -B e2e/run_e2e.py grade-case --fixture /private/tmp/growth-fixture/fixture.json \
  --case learn-writes-where-journey-reads --native-result native-result.json
python3 -B e2e/run_e2e.py grade --records records.json --output score.json
```

`prepare` uses `environment.install` to place the current source in a new
fixture home/work tree for every preserved case, then inspects the installed
runtime/binding and `gl-run` inside those fixtures. It never writes an operator home, links/copies auth, or
registers/trusts a plugin. `request` only describes a future native-host or
effectively verified common benchmark-runner run. `grade-case` inspects declared
fixture artifacts and a structured native result; `grade` aggregates supplied
observations. None invokes Claude/Codex, a model CLI, or an
authentication store, captures raw logs/credentials, or changes permissions.
All requests remain `not_run`: this offline tool does not verify a host or runner.
`runner_support` distinguishes recognized-but-unverified from unsupported runners.
Caller-supplied receipt JSON cannot upgrade that status. An authorized native host
or the common runner must establish its effective scope before executing a request.
Journey grading checks installed helper bytes but runs only trusted source, never
code or importable modules written by the evaluated agent.

## Record contract

Each record is JSON with `version: 1`, `case`, `host`, `model`, `variant`
(`none`, `current`, or `improved`), `run`, `outcome` (`pass`, `fail`, or
`unknown`), `checks`, `invoked_skills`, `elapsed_ms`, `token_usage`, and
`conditions.fixture`, `.runner`, `.task`. A `pass` needs a supported passing
check with a non-empty artifact or trace `evidence`; an unsupported or not-run
host is `unknown`. `invoked_skills`, `loaded_documents`, and `git_writes` may
be `null` when unrecorded or `[]` when observed empty. Metrics are nullable and
missing values stay missing.

For the legacy structural report predicates, a native result supplies `routes`
and `slugs` arrays instead of stdout. Missing structured data is `unknown`, not
silently skipped. `grade-case` verifies the installed helper bytes against the
maintained source before its deterministic in-process `journey --locate` check.

The scorer reports supplied observations, not an independent verification of
the arbitrary claim behind a trace reference. It reports per-variant pass rate
over known pass/fail outcomes plus elapsed/token distributions. It labels a cell
incomparable until all three variants have a known result under the same case,
host, model, fixture, runner, and task. `source_revision` may identify a variant
but does not split those conditions. This keeps unequal conditions, missing
metrics, untriggered skills, and no-run records visible rather than converting
any into success.
