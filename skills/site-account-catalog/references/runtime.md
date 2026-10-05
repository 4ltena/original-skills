# Broker runtime

The agent selects IDs. A broker in a separate non-admin OS account uses credentials and returns fixed status codes. Registration, unlock, recovery, and key paths belong to a private UI in that broker account.

## Commands

Install the package with Python 3.10+ and `python -m pip install .`. Tkinter is required for the private UI. For a copied skill, run `python <skill>/scripts/accountctl.py ...`.

```text
accountctl find github.com
accountctl identity example username --site github
accountctl login example-test-web
accountctl run example-test-ssh health-check
```

The last two IDs are examples, not configured accounts. Configure the public client file `<Codex home>/account-catalog-client.json`:

```json
{"schema_version":1,"endpoint":"example-broker","broker_id":"<broker OS SID>"}
```

Windows uses a pipe ID. macOS/Linux use an absolute UNIX socket path and the broker's numeric UID as a string. This file contains no login name or secret. The client validates the broker's OS identity and accepts only the fixed response schema.

## Deployment boundary

Prepare a different non-admin account and protected runtime **before entering credentials**. OS account creation, permissions, services, and real credentials are a separate deployment operation. Verify all agent tools, including elevation and debugger paths; admin/root access invalidates the isolation requirement.

Protect the Python executable, search paths, dependencies, source, bindings, encrypted files, keys, backups, and session memory from agent modification/access. Startup checks reject root/admin execution, unsafe owners/permissions, and symlink/reparse paths. Same-user execution is not a secret boundary. The CLI may live in the agent's skill folder; the broker runtime must be installed separately in a protected location.

An administrator must provision `<vault>/deployment.json` with `schema_version: 1`, `broker_id`, and the exact `agent_ids` array. Its owner must be root (Unix) or SYSTEM/Administrators (Windows), with no broker/agent write permission. Startup rejects an absent policy, a mismatched broker, empty agent IDs, or the same identity in both roles. Target callers must belong to this policy. These checks depend on the administrator registering the actual identities of all agent tools; the program cannot discover every future elevation path automatically.

| OS | Initial key provider | Transport | Evidence required |
| --- | --- | --- | --- |
| Windows | Runner-user DPAPI or manual Argon2id | Local-only named pipe; caller SID and server SID | Separate accounts, explicit pipe DACL, ACL/process/elevation denial |
| macOS | Manual Argon2id | UNIX socket; `getpeereid` | Dedicated UID, protected runtime, private UI, peer/permission denial |
| Linux | Manual Argon2id or systemd credential | UNIX socket; `SO_PEERCRED` | Dedicated UID, runtime credential protection, peer/permission denial |

macOS user Keychain needs a signed app/login context. Daemons have different Keychain constraints. Keychain and Secret Service adapters are not implemented. The manual provider needs a human unlock after restart; no provider fallback is automatic.

For Unix, private directories require owner-only permissions and protected ancestry; use a separate broker-owned socket directory with client traversal but no client write permission. The execute socket permits the configured client group; the admin socket is inside the owner-only vault. Windows execute pipes grant caller SIDs only read/write data rights; the admin pipe grants only broker/SYSTEM access. Registration/unlock is never offered on the execution endpoint.

Example broker invocation in the protected broker account:

```text
account-broker --root <private vault directory> --endpoint <pipe ID or UNIX socket path>
```

The private directory must already exist and pass checks. The UI initializes a vault, saves the recovery key outside the vault, and generates an unlock phrase. Enter the phrase in the UI, then save credentials and register targets. UI closure locks the broker. For a background broker use `--headless`; open its private UI with the same command plus `--manage` from the broker account. Management traffic is authenticated to that same protected OS identity and may carry secrets internally; it never passes through `accountctl`.

## Registered providers

HTTPS Basic uses TLS certificate/hostname verification, one fixed HTTPS origin, two registered paths, and an expected 2xx status. Redirects are rejected. Its endpoints must actually require authentication; an always-public 200 endpoint is not proof of login. HTTP form/browser adapters are not included.

Protected binding example, entered by the user through the private UI:

```json
{"target_id":"example-test-web","credential_id":"example-credential","provider":"https-basic-v1","callers":["<agent OS SID or numeric UID>"],"config":{"origin":"https://example.com","login_path":"/private","health_path":"/health","expected_status":200}}
```

SSH binding uses `provider: ssh-key-v1`; config fields are `host`, `port`, `private_key_path`, `host_key_type`, `host_key_b64`, and a fixed `health_command`. Credentials contain `username` and optional `passphrase`. All original key copies and backups must remain inaccessible to the agent. Agent forwarding and discovery of other SSH keys are disabled. Host keys are pinned; `health-check` returns only whether the fixed command exited with code zero. It exposes no remote shell or raw output.

## Encryption, lock, and recovery

Credentials use AES-256-GCM. AAD is UTF-8 sorted-key compact JSON with namespace `account-catalog/credential/v1` and metadata `schema_version`, `credential_id`, `key_id`, `protection`. Each encryption generates a fresh 12-byte nonce. Within a generation, duplicate nonces are rejected; every restore/new writer gets a new 256-bit key and key ID.

Manual key wrapping uses Argon2id v19 with 16-byte salt, 64 MiB, 3 iterations, 4 lanes, and 32-byte output. These are the only accepted v1 parameters. Wrapped-key AAD uses `account-catalog/key-wrap/v1` with version/provider/key ID/KDF/salt. DPAPI is user-scope, never machine-scope. Memory erasure of Python strings is not guaranteed; credentials never use plaintext temporary files or agent-readable environment/argv.

Lock persists before clearing cached keys/sessions. Missing/corrupt state is locked. Unlock lasts at most 15 minutes and sessions last 5 minutes, bound to caller and target. Every broker start records a lock, including crash restart, for all providers. The private UI must explicitly unlock it. State is checked before and after external operations; an already-sent network operation cannot be undone by locking.

Recovery JSON contains `schema_version: 1`, `key_id`, and the Base64 32-byte key. It is a secret, not a public reference. The UI uses exclusive save, verifies the written copy, and refuses storage inside the vault. Windows temporary files receive an explicit protected DACL before any data is written, rather than inheriting a directory's child ACEs. Confirm that the chosen backup storage is independently protected from agent tools; the software does not provision that storage.

Restore needs the encrypted backup directory and corresponding offline recovery key. It does not need the old DPAPI/Keychain/TPM state. A new generation is encrypted with a new key; its recovery copy and all records are verified before the manifest switches. Old generations remain, and restored bindings are empty until re-registered. SSH key backup/ownership is separate. Use the restore UI for rotation too. Interruptions before the manifest switch preserve the old generation; after a switch, the new generation is locked until explicitly unlocked. Keep recovery keys for old backups.

Linux systemd mode expects a JSON key payload named `account-catalog-key` under `$CREDENTIALS_DIRECTORY`, delivered with `LoadCredentialEncrypted=` to the dedicated service. An administrator outside the agent must generate/provision a fresh random key and ID, encrypt it with a fixed `host` or `host+tpm2` policy, and protect unit/runtime paths. The UI can initialize/restore against that pre-provisioned key. Rotation requires a new runtime key/ID and restart; no plaintext/null-key mode or automatic TPM downgrade is used. Systemd provisioning and real runtime isolation have not been executed here.

## Verification status

Run `python -X utf8 -m unittest discover -s tests -v`. Tests use dummy values. Crypto/storage/broker tests include simulated boundary fixtures; they are not proof of separate OS accounts. Windows DPAPI also has a real local dummy round trip. Complete macOS/Linux, separate-account IPC, SSH/TLS service, private UI, process/dump, and OS-to-OS restore checks before using real credentials.
