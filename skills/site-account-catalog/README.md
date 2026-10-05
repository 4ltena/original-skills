# Site Account Catalog

A Codex skill and local CLI for account identities, license wording, entitlements, and registered login actions.

Copy this directory to `<Codex home>/skills/site-account-catalog/` (`CODEX_HOME` or `~/.codex`). Add non-secret JSON using the [schema](references/schema.md). Install the CLI with `python -m pip install .`.

Login needs a protected broker in a separate OS account; see [runtime setup](references/runtime.md). Windows DPAPI and shared crypto have dummy tests. macOS/Linux isolation and real login remain unverified. Missing identity fields require one question; names are never guessed.

Licensed under MIT.
