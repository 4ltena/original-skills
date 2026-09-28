# frontend-optimize

Four platform-specific skills for frontend runtime optimization.

Agent Skills for diagnosing and improving frontend **runtime performance**. These skills cover responsiveness, rendering, scheduling, memory, persistence boundaries, and measurement. They do not provide visual design or styling guidance.

| Skill | Scope |
| --- | --- |
| [`frontend-optimize-webapp`](skills/frontend-optimize-webapp/SKILL.md) | Browser apps, rendering, Workers, storage, and Web Vitals |
| [`frontend-optimize-apple`](skills/frontend-optimize-apple/SKILL.md) | SwiftUI, AppKit, UIKit, Core Animation, and Metal |
| [`frontend-optimize-windows`](skills/frontend-optimize-windows/SKILL.md) | Windows native UI and its execution/rendering pipeline |
| [`frontend-optimize-linux`](skills/frontend-optimize-linux/SKILL.md) | Qt, GTK, Wayland/X11, and Linux GUI profiling |

Each directory is an independent [Agent Skill](https://agentskills.io/specification) with a `SKILL.md` entry point. Detailed guidance lives in `references/`; reusable templates and synthetic examples live in `assets/`; optional local helpers live in `scripts/`. Choose skills for the apps you work on, regardless of your host operating system.

## Install in Codex

From this repository's root, copy all four skills into your user skill directory:

```sh
mkdir -p ~/.agents/skills
cp -R skills/frontend-optimize-* ~/.agents/skills/
```

Install a subset by naming the relevant skill directories instead. A Windows host can use the web app, Apple, or Linux skills when working on those targets. Restart Codex if an installed skill does not appear. Codex can select a skill from its description, or you can invoke one explicitly, for example: `$frontend-optimize-linux Profile the UI freeze when opening a large document.` [Codex skill locations](https://learn.chatgpt.com/docs/build-skills) are documented by OpenAI.

For other Agent Skills clients, place an individual skill directory in the location documented by that client. Keep each directory intact so links from `SKILL.md` to its resources continue to work.

## How to use

Describe a specific slow interaction, target platform, app version, device, and available traces. The skills ask the agent to establish a comparable baseline, identify the execution path and bottleneck, make a bounded change, and check both performance and correctness. They distinguish measured evidence from assumptions. A passing metric comparison does **not** by itself establish that an optimization is safe to accept.

The optional `compare_metrics.py` helper needs Python 3.10 or newer. The web app skill also includes an optional browser probe and a Chrome trace JSON summary helper. Platform profilers and target devices are needed for real performance claims; the bundled `synthetic-*` data is only a demonstration fixture.

## Provenance and license

The four skill directories were assembled from the matching `frontend-optimize-{apple,linux,webapp,windows}-v1.1.0.zip` source bundles. Their instructions and supporting material have been translated into English while retaining the technical contracts. This repository also adds a license declaration and `LICENSE` file to each skill, plus repository-level publishing files. External technical sources are linked and annotated in each skill's `references/sources.md`.

This repository is licensed under [MIT](LICENSE). The license applies to the repository contents, not to external pages linked in the source references.
