# Desktop artifacts

First read supported formats, minimum OS, signing/notarization/checksum policies and pinned builder version; infer no missing requirements. Build only supported targets.

Name files `{project}-{X.Y.Z}-{archToken}.{ext}` without `v`:

| Platform | Native names |
|---|---|
| Windows | `x64.exe`, `arm64.exe` |
| macOS | `universal.dmg`, `universal.zip` |
| Linux | `amd64.deb`, `x86_64.AppImage`, `x86_64.rpm`, `x86_64.pacman`; arm64 only if required |

Build in each target environment/CI. Verify names, architecture, package metadata, checksums, required signatures/notarization and every bundled native binary. Missing required evidence fails verification. Smoke-test install/launch where available; label other platforms unverified and seek a publication decision if policy leaves their blocking status undefined.

List only verified assets in download tables with English descriptions, architecture and brief install steps. Recommend a primary artifact only when established by the project; include unsigned/offline/checksum notes only when applicable.

Before changing electron-builder targets/names, read [electron-builder guidance](electron-builder.md).
