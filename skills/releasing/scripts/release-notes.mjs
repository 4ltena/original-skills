#!/usr/bin/env node
// release-notes.mjs — build GitHub Release notes from CHANGELOG.md.
//
// Drafts the user-facing sections (追加 / 変更 / 修正) of one version's CHANGELOG
// entry, prefixed by its summary. Optional download content must be supplied
// from independently verified release artifacts. Zero dependencies (Node 16+, ESM).
//
// Usage:
//   node scripts/release-notes.mjs [version] [options] > NOTES.md
//
// Arguments:
//   version            X.Y.Z (with or without leading v). Default: the topmost
//                      "## [x.y.z]" entry in the CHANGELOG.
// Options:
//   --changelog=PATH   CHANGELOG path (default ./CHANGELOG.md)
//   --sections=A,B     section headings to mirror (default: 追加,変更,修正)
//   --downloads-file=PATH  reviewed Markdown block for verified downloads
//   --no-downloads     compatibility option; downloads are omitted by default
//   -h, --help         show this help

import { readFileSync } from 'node:fs';

// Changelog headings → bilingual release-note headings.
const SECTION_LABELS = { '追加': '追加 / Added', '変更': '変更 / Changed', '修正': '修正 / Fixed' };

const USAGE = `release-notes.mjs — build GitHub Release notes from CHANGELOG.md

Usage:
  node scripts/release-notes.mjs [version] [options] > NOTES.md

Arguments:
  version            X.Y.Z (with or without leading v). Default: topmost entry.
Options:
  --changelog=PATH   CHANGELOG path (default ./CHANGELOG.md)
  --sections=A,B     section headings to mirror (default: 追加,変更,修正)
  --downloads-file=PATH  reviewed Markdown block for verified downloads
  --no-downloads     compatibility option; downloads are omitted by default
  -h, --help         show this help`;

function parseArgs(argv) {
  const opts = {
    version: null,
    changelog: 'CHANGELOG.md',
    sections: ['追加', '変更', '修正'],
    downloadsFile: null,
    noDownloads: false,
  };
  for (const a of argv) {
    if (a === '-h' || a === '--help') opts.help = true;
    else if (a === '--no-downloads') opts.noDownloads = true;
    else if (a.startsWith('--changelog=')) opts.changelog = a.slice(12);
    else if (a.startsWith('--downloads-file=')) {
      if (opts.downloadsFile !== null) fail('--downloads-file may be provided only once');
      opts.downloadsFile = a.slice(17);
    }
    else if (a.startsWith('--project=')) fail('--project no longer creates download claims; use a reviewed --downloads-file');
    else if (a.startsWith('--sections=')) opts.sections = a.slice(11).split(',').map((s) => s.trim()).filter(Boolean);
    else if (a.startsWith('-')) fail(`unknown option: ${a}`);
    else opts.version = a.replace(/^v/, '');
  }
  if (opts.noDownloads && opts.downloadsFile !== null) fail('--no-downloads cannot be combined with --downloads-file');
  if (opts.downloadsFile === '') fail('--downloads-file requires a path');
  return opts;
}

function fail(msg) {
  process.stderr.write(`release-notes: ${msg}\n`);
  process.exit(1);
}

// Split the CHANGELOG into { version, body } blocks keyed by "## [x.y.z]" headings.
function splitVersions(md) {
  const re = /^##\s*\[(\d+\.\d+\.\d+)\][^\n]*\n([\s\S]*?)(?=^##\s*\[|(?![\s\S]))/gm;
  const blocks = [];
  let m;
  while ((m = re.exec(md)) !== null) blocks.push({ version: m[1], body: m[2] });
  return blocks;
}

// From a version body, pull the lead summary paragraph and the "### <name>" subsections.
function parseBlock(body) {
  const firstSub = body.search(/^###\s+/m);
  const head = (firstSub === -1 ? body : body.slice(0, firstSub)).trim();
  const summary = head
    .split('\n')
    .map((l) => l.trim())
    .filter(Boolean)
    .join(' ');
  const sections = {};
  const re = /^###\s+(.+?)\s*\n([\s\S]*?)(?=^###\s+|(?![\s\S]))/gm;
  let m;
  while ((m = re.exec(body)) !== null) sections[m[1].trim()] = m[2].trim();
  return { summary, sections };
}

function main() {
  const opts = parseArgs(process.argv.slice(2));
  if (opts.help) {
    process.stdout.write(USAGE + '\n');
    return;
  }

  let md;
  try {
    md = readFileSync(opts.changelog, 'utf8');
  } catch {
    fail(`cannot read ${opts.changelog}`);
  }

  const blocks = splitVersions(md);
  if (blocks.length === 0) fail('no "## [x.y.z]" entries found');
  const block = opts.version
    ? blocks.find((b) => b.version === opts.version)
    : blocks[0];
  if (!block) fail(`version ${opts.version} not found in ${opts.changelog}`);

  const { summary, sections } = parseBlock(block.body);
  const out = [];
  const lead = summary ? `v${block.version}: ${summary}` : `v${block.version}`;
  out.push(lead, '');
  if (opts.downloadsFile !== null) {
    let downloads;
    try {
      downloads = readFileSync(opts.downloadsFile, 'utf8').trim();
    } catch {
      fail(`cannot read ${opts.downloadsFile}`);
    }
    if (!downloads) fail(`downloads file is empty: ${opts.downloadsFile}`);
    out.push(downloads, '');
  }
  for (const name of opts.sections) {
    if (!sections[name]) continue;
    out.push(`## ${SECTION_LABELS[name] || name}`, '', sections[name], '');
  }
  process.stdout.write(out.join('\n').replace(/\n{3,}/g, '\n\n').trim() + '\n');
}

main();
