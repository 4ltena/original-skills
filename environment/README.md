# Agent environment

Use [SETUP.md](SETUP.md) to install with the Claude or Codex agent already available.
A shared questionnaire selects the host, Skill/plugin scope, Git mode, hooks and
configuration changes. CLI-free preparation uses Python 3.10+ and no dependencies.

- [questions.json](questions.json): predefined questions and conditional choices.
- [install.py](install.py): next question, dry-run plan and reviewed-plan application.
- [HOSTS.md](HOSTS.md): all 46 Skill entrypoints and Claude adaptations.
- [skill-compatibility.json](skill-compatibility.json): maintained classification/fixture map.
- [profiles/manual-git.md](profiles/manual-git.md): explicit-request Git operation mode.
- [codex](codex): optional Codex sandbox/policy templates and configuration merger.
- [claude](claude): standalone Claude instructions and optional permission/hook templates.

Existing Skills and custom frontend-design are preserved. Third-party plugins,
superpowers, official frontend-design, LSP and commit helpers are opt-in external
features, absent from defaults. Skills are placed once; runtime packages contain
bound helpers/hooks. Source hooks are inert until a real interpreter is probed.
Source placement, host registration/trust and live runtime are reported separately.

The selected manual-git profile limits Git/GitHub writes to explicit requests;
automatic mode keeps the existing ordinary task policy and stricter safety gates.
Claude uses its actual permission mode, and Codex uses its actual review mechanism.
The installer does not rewrite security config, credentials or global Git identity.

Offline verification:

```text
<python-3.10+> -B -m unittest discover -s environment/tests -v
<python-3.10+> -B skills/growth-loop/tests/run.py
<python-3.10+> -B -m unittest discover -s plugins/goal-checkpoint/tests -v
```

These checks do not establish Windows/Claude live delivery or multi-day results.
