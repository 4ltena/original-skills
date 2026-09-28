// The generator supports Node 16+; this node:test suite uses Node 18+.
import assert from 'node:assert/strict';
import { mkdtempSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import test from 'node:test';

const script = fileURLToPath(new URL('../scripts/release-notes.mjs', import.meta.url));
const directory = mkdtempSync(join(tmpdir(), 'release-notes-test-'));
const changelog = join(directory, 'CHANGELOG.md');
const downloads = join(directory, 'downloads.md');

writeFileSync(changelog, `# 変更履歴

## [0.12.0] - 2026-09-27

Polaris 0.12.0 adds a macOS workspace.

### 追加

- Adjustable workspace panes.

### 変更

- Clearer launch status.

### 修正

- Restore the draft on restart.
`);
writeFileSync(downloads, `## Download and install

| File | Requirement |
| --- | --- |
| polaris-0.12.0-arm64.dmg | Apple Silicon, macOS 13.5+ |

SHA-256: verified-value`);

function run(...args) {
  return spawnSync(process.execPath, [script, `--changelog=${changelog}`, ...args], {
    encoding: 'utf8',
    cwd: directory,
  });
}

test('default draft has user-facing changes but no invented downloads', () => {
  const result = run('0.12.0');
  assert.equal(result.status, 0, result.stderr);
  assert.match(result.stdout, /Polaris 0\.12\.0 adds a macOS workspace/);
  assert.match(result.stdout, /## 追加 \/ Added[\s\S]*## 変更 \/ Changed[\s\S]*## 修正 \/ Fixed/);
  assert.doesNotMatch(result.stdout, /Windows|Linux|universal\.dmg|fully offline|Unsigned build/);
});

test('draft lead identifies the selected version when the summary omits it', () => {
  const other = join(directory, 'NO-VERSION-LEAD.md');
  writeFileSync(other, '## [0.12.1] - 2026-09-28\n\nAdds a clearer workspace.\n');
  const result = spawnSync(process.execPath, [script, `--changelog=${other}`], {
    encoding: 'utf8',
    cwd: directory,
  });
  assert.equal(result.status, 0, result.stderr);
  assert.match(result.stdout, /^v0\.12\.1: Adds a clearer workspace\./);
});

test('a platform requirement containing the version digits cannot hide the release version', () => {
  const other = join(directory, 'PLATFORM-VERSION.md');
  writeFileSync(other, '## [0.12.0] - 2026-09-27\n\nRequires macOS 10.12.0. Adds a workspace.\n');
  const result = spawnSync(process.execPath, [script, `--changelog=${other}`], {
    encoding: 'utf8',
    cwd: directory,
  });
  assert.equal(result.status, 0, result.stderr);
  assert.match(result.stdout, /^v0\.12\.0: Requires macOS 10\.12\.0\./);
});

test('provided download facts appear between summary and changes', () => {
  const result = run('0.12.0', `--downloads-file=${downloads}`);
  assert.equal(result.status, 0, result.stderr);
  assert.ok(result.stdout.indexOf('Polaris 0.12.0') < result.stdout.indexOf('## Download and install'));
  assert.ok(result.stdout.indexOf('## Download and install') < result.stdout.indexOf('## 追加 / Added'));
  assert.match(result.stdout, /polaris-0\.12\.0-arm64\.dmg/);
});

test('conflicting download switches fail before emitting notes', () => {
  const result = run(`--downloads-file=${downloads}`, '--no-downloads');
  assert.notEqual(result.status, 0);
  assert.equal(result.stdout, '');
});

test('missing download file fails before emitting notes', () => {
  const result = run('--downloads-file=missing.md');
  assert.notEqual(result.status, 0);
  assert.equal(result.stdout, '');
});

test('empty download file fails before emitting notes', () => {
  const empty = join(directory, 'empty.md');
  writeFileSync(empty, '  \n');
  const result = run(`--downloads-file=${empty}`);
  assert.notEqual(result.status, 0);
  assert.equal(result.stdout, '');
});

test('duplicate download files fail instead of silently replacing the first', () => {
  const result = run(`--downloads-file=${downloads}`, `--downloads-file=${downloads}`);
  assert.notEqual(result.status, 0);
  assert.equal(result.stdout, '');
});

test('legacy project option fails with migration guidance', () => {
  const result = run('--project=polaris');
  assert.notEqual(result.status, 0);
  assert.match(result.stderr, /--downloads-file/);
  assert.equal(result.stdout, '');
});

test('legacy no-downloads switch retains the safe default', () => {
  const result = run('--no-downloads');
  assert.equal(result.status, 0, result.stderr);
  assert.doesNotMatch(result.stdout, /## Download and install/);
});
