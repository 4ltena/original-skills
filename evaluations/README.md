# Skill selection and comparison

Use these cases to check whether an agent selects the intended skill, avoids
nearby false triggers, and stays within the task's reading and Git scope.
`skill-selection.json` supplies the same 16 requests for Codex and Claude.
The limits are case-specific acceptance conditions, not global reading limits.

Run each request in a clean native host session or an effectively verified
evaluation runner. Record actual skill invocations (including repeated loads),
extra reference-document loads, and Git writes. Catalog metadata itself is not
a document load. Keep the same task, fixture, model and runner across variants.
Missing observations are `null`; observed absence is `[]`. A trace reference
must identify the non-secret evidence behind the observation. Do not copy
credentials or full conversations into evaluation records.

`score_selection.py RECORDS.json` reads a JSON array of records with `version:1`,
`case`, `host`, `model`, `variant` (`none/current/improved`), `run`,
`invoked_skills`, `loaded_documents`, `git_writes`, `trace_ref`, `conditions` (fixture, runner, task),
and optional `elapsed_ms` / `token_usage`. It emits records compatible with
the [growth-loop comparison harness](../skills/growth-loop/e2e/README.md).
Exit 0 means every supplied selection observation passed; 1 means a failed or
unknown check; 2 means invalid input. An empty or incomplete batch is not proof
that all cases passed.

Selection is a process measure. Use the comparison harness's artifact checks
to measure task completion separately; a skill-free run is not a quality
failure merely because it did not invoke a skill. Model runs are opt-in and
use the host's existing authorization. An unavailable runner stays `not_run`;
there is no CLI, authentication or permission fallback.

Offline checks:

```text
python3 -B -m unittest discover -s evaluations/tests
```

These checks validate the grader using deliberate false triggers, repeated
reads and unrequested Git writes. They do not establish real model pass rates.

`score_checkpoint.py REVIEWS.json` grades supplied decisions against the three
[checkpoint scenarios](../plugins/goal-checkpoint/tests/review_cases.json).
Give the reviewer the scenario's goal/baseline/current/monitor and the checkpoint
skill, keeping `assessment` and `expected` hidden. Capture `case`, `decision`,
`verdict`, and `next_action_kind` from the review. The grader catches cosmetic
drift, rejection of necessary recovery work, and restarting a completed goal.
Check the reason and proposed action against raw evidence independently;
matching category labels alone do not establish good judgment.

The design follows OpenAI's [skill evaluation guide](https://developers.openai.com/blog/eval-skills)
and [September 2026 guidance on descriptions and instructions](https://developers.openai.com/blog/rethinking-skills-and-prompts-for-gpt-6-astra),
and Anthropic's [skill vs. no-skill comparison guidance](https://claude.com/resources/articles/improving-skill-creator-test-measure-and-refine-agent-skills).
The [September 2026 AGENTS.md study](https://arxiv.org/html/2602.11988v3)
does not evaluate security policy or this repository; preserve authorization
rules and test proposed instruction changes on representative tasks.
