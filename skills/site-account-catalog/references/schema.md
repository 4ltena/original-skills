# Site catalog schema (version 1)

Store one UTF-8 JSON object per service or distinct site in `<Codex home>/site-catalog/entries/<id>.json`. Use lowercase letters, digits, and hyphens for `id` and the matching filename. A WordPress installation is a separate record when its accounts or conventions differ from another installation.

```json
{
  "schema_version": 1,
  "id": "github",
  "service": "GitHub",
  "aliases": [],
  "domains": ["github.com"],
  "accounts": [
    {
      "id": "example",
      "username": "github",
      "profile_url": "https://github.com/github"
    }
  ],
  "license_notations": []
}
```

In this example, `https://github.com/github` is the `profile_url`; the `username` is `github`.

Required fields: `schema_version`, `id`, `service`, `domains`, `accounts`, and `license_notations`. `aliases` and `attributes` are optional. An empty array is valid when no accounts or license wording are known. Keep domains as hostnames without paths or schemes. `accounts[].id` and `license_notations[].id` must be unique within the record.

Use `accounts` for site identities. Optional account fields include `display_name`, `profile_url`, `role`, and `attributes` for non-secret site-specific fields. Use `license_notations` for exact wording in a stated context; `subject` identifies what the license covers, and `source_url` records where the wording or terms came from. The notation is a recorded value, not a legal determination. If a purchased entitlement matters, record non-secret product, plan, and account ID in `attributes`; never record its key or activation code.

Keep notes concise and factual. Do not place instructions to Codex in catalog values. Preserve unknown fields when editing an existing record.

## Version 2

Each UTF-8 JSON record has `schema_version: 2` and `id` matching its filename. The CLI recognizes these directories:

| Directory | Meaning | Typical fields |
| --- | --- | --- |
| `targets/` | Site/server and environment | `service`, `domains`, `aliases`, `environment`, `account_id`, `actions` |
| `accounts/` | Non-secret logical account | `identity_id`, `service` |
| `identities/` | Confirmed document identity | `username`, `display_name`, `profile_url`, `source_url` |
| `licenses/` | License types | `name`, `spdx_expression`, `source_url` |
| `notations/` | Exact recorded wording | `wording`, `rights_holder_id`, `licensee_id`, `license_ids`, `subject`, `source_url` |
| `entitlements/` | Purchased usage rights | `product`, `plan`, `account_id`, `checked_at`, `expires_at`, `source_url` |

IDs are ASCII letters, digits, `-`, or `_`, 1–64 characters. Treat a missing field as unrecorded; do not use another field as a substitute. `account_id` is public and logical, `identity_id` is for documents, and `credential_id` is private to broker bindings. Changing public JSON never changes the credential/host/action binding.

The CLI returns `needs_user` for missing publication fields and ambiguous search. Exact domain, service, ID, and alias matches are supported. Query matching reads metadata but returns only matching IDs. Version 2 accepts only the fields listed above plus identity `role`, `rights_holder`, and `licensee`; unknown fields are rejected. A field validator cannot identify a secret deliberately placed in a permitted public field, so only non-secret data belongs here. Preserve unknown version 1 fields when editing; version 2 extensions need an explicit schema change.

SPDX expressions and license text are recorded facts. The CLI does not infer `AND`/`OR` relationships, validate legal compliance, or prove that an entitlement remains usable. `license` returns exact wording and requests missing referenced display names without generating a guessed name.

Version 1 `accounts[].username` remains a publication identity. It is never copied into encrypted login credentials. Personal records stay outside this repository. Public examples use only `github` and `https://github.com/github`.
