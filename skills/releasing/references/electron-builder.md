# electron-builder artifact naming

`${version}` is already bare `X.Y.Z`. Do not assume `${arch}` behaves identically for every target; verify names with the installed electron-builder version. Prefer literal tokens for single-architecture Linux targets and use `${arch}` only where one target distinguishes multiple architectures.

```jsonc
{
  "win": {
    "target": [{ "target": "nsis", "arch": ["x64", "arm64"] }],
    "artifactName": "${name}-${version}-${arch}.${ext}"
  },
  "mac": {
    "target": [
      { "target": "dmg", "arch": ["universal"] },
      { "target": "zip", "arch": ["universal"] }
    ],
    "artifactName": "${name}-${version}-universal.${ext}"
  },
  "linux": { "target": ["AppImage", "deb", "rpm", "pacman"] },
  "appImage": { "artifactName": "${name}-${version}-x86_64.${ext}" },
  "deb": { "artifactName": "${name}-${version}-amd64.${ext}" },
  "rpm": { "artifactName": "${name}-${version}-x86_64.${ext}" },
  "pacman": { "artifactName": "${name}-${version}-x86_64.${ext}" }
}
```

After building, compare the actual filenames and embedded architecture metadata with the release plan. Treat a mismatch as a failed verification, not a documentation-only issue.
