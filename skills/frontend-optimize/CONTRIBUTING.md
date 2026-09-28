# Contributing

Issues and pull requests for reproducible performance guidance are welcome.

- Keep each `skills/<name>/` directory independently usable. Put routing and essential decisions in `SKILL.md`, detailed platform material in `references/`, reusable output templates in `assets/`, and deterministic helpers in `scripts/`.
- State the platform, runtime, and version behind a technical claim. Add or update a primary source in that skill's `references/sources.md` when a claim depends on a changing API or tool.
- Do not present synthetic fixtures, tool exit codes, or a single trace as proof of a real performance improvement. Preserve correctness, accessibility, persistence, and resource guardrails.
- If you change the browser probe, run `node --check skills/frontend-optimize-webapp/scripts/runtime-probe.js` before submitting a change.
- Describe the observable behavior that changed and the measurements or limitations supporting it. Do not include private traces, credentials, or user data in examples.
