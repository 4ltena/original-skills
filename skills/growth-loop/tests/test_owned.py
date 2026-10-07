import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

BIN = Path(__file__).resolve().parents[1] / 'growth-loop/bin'
sys.path.insert(0, str(BIN))
sys.dont_write_bytecode = True
import owned


def payload(slug='demo', text='use a verified route'):
    return {'SKILL.md': '---\nname: ' + slug + '\ndescription: Repeat the verified route after a specific failure.\n---\n' + text,
            'scripts/example.txt': 'support'}


class OwnedTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name).resolve()
        self.root = self.base / 'skills'; self.root.mkdir(mode=0o700)
        self.data = self.base / 'data'; self.data.mkdir(mode=0o700)
        self.manager = owned.Manager(self.root, self.data, True)

    def tearDown(self):
        self.temp.cleanup()

    def create(self):
        return self.manager.create('demo', payload())['generation']

    def test_create_update_delete_whole_payload_and_no_contents_in_ledger(self):
        generation = self.create()
        self.assertEqual(self.manager.status('demo')['state'], 'active')
        self.manager.update('demo', generation, payload(text='corrected'))
        self.assertIn('corrected', (self.root / 'demo/SKILL.md').read_text())
        self.manager.delete('demo', generation, 'obsolete')
        self.assertFalse((self.root / 'demo').exists())
        with self.manager.transaction() as (_, _, ledger):
            entry = self.manager.entry(ledger, 'demo', generation)
            self.assertEqual(set(entry), {'root', 'slug', 'generation', 'state'})
        self.assertEqual(list(self.root.iterdir()), [])

    def test_collision_and_unowned_skill_are_never_adopted(self):
        (self.root / 'demo').mkdir()
        marker = self.root / 'demo/SKILL.md'; marker.write_text('manual')
        for operation in (lambda: self.create(), lambda: self.manager.delete('demo', 'a' * 32, 'obsolete')):
            with self.assertRaises((ValueError, OSError)):
                operation()
        self.assertEqual(marker.read_text(), 'manual')

    def test_body_cannot_supply_missing_or_mismatched_frontmatter(self):
        for document in ('---\nname: other\n---\nname: demo\ndescription: body',
                         '---\nname: demo\n---\ndescription: body',
                         '---\nname: demo\ndescription: missing delimiter'):
            with self.assertRaises(owned.OwnedError):
                self.manager.create('demo', {'SKILL.md': document})
        self.assertFalse((self.root / 'demo').exists())

    @unittest.skipIf(os.name == 'nt', 'POSIX fstat/atime regression')
    def test_read_atime_change_is_not_a_payload_mutation(self):
        self.create()
        real_fstat = os.fstat
        count = 0
        def changed_atime(fd):
            nonlocal count
            count += 1
            info = real_fstat(fd)
            fields = {key: getattr(info, key) for key in dir(info) if key.startswith('st_')}
            fields['st_atime_ns'] += count
            fields['st_atime'] += count
            return SimpleNamespace(**fields)
        with owned.PosixFS.root(self.root) as root:
            with root.directory('demo') as directory:
                with patch.object(owned.os, 'fstat', side_effect=changed_atime):
                    raw, record = directory.read('SKILL.md')
        self.assertEqual(raw.decode(), payload()['SKILL.md'])
        self.assertEqual(record['size'], len(raw))

    def test_tampered_added_file_and_stale_generation_refuse(self):
        generation = self.create()
        with self.assertRaises(owned.OwnedError):
            self.manager.delete('demo', 'b' * 32, 'obsolete')
        extra = self.root / 'demo/manual.txt'; extra.write_text('keep')
        with self.assertRaises(owned.OwnedError):
            self.manager.delete('demo', generation, 'obsolete')
        extra.unlink()
        (self.root / 'demo/SKILL.md').write_text('external change')
        with self.assertRaises(owned.OwnedError):
            self.manager.delete('demo', generation, 'obsolete')
        self.assertTrue((self.root / 'demo/manual.txt').exists() is False)
        self.assertTrue((self.root / 'demo/SKILL.md').exists())

    def test_symlink_hardlink_and_root_traversal_refuse(self):
        for slug in ('../manual', '.system', 'synced', 'vendor'):
            with self.assertRaises(owned.OwnedError):
                self.manager.create(slug, payload(slug))
        generation = self.create()
        external = self.base / 'keep.txt'; external.write_text('keep')
        try:
            os.symlink(external, self.root / 'demo/link')
        except OSError:
            self.skipTest('symlink privilege unavailable')
        with self.assertRaises((owned.OwnedError, OSError)):
            self.manager.delete('demo', generation, 'obsolete')
        self.assertEqual(external.read_text(), 'keep')

    def test_disabled_and_age_are_not_deletion_authority(self):
        generation = self.create()
        disabled = owned.Manager(self.root, self.data, False)
        with self.assertRaises(owned.OwnedError):
            disabled.delete('demo', generation, 'obsolete')
        with self.assertRaises(owned.OwnedError):
            self.manager.delete('demo', generation, 'old')

    def test_create_commit_boundaries(self):
        for point in ('create-reserved', 'create-prepared', 'create-published'):
            with self.subTest(point=point):
                manager = owned.Manager(self.root, self.data, True)
                slug = point
                with patch.dict(os.environ, {'GROWTH_LOOP_TEST_FAULT': point}):
                    with self.assertRaises(owned.OwnedError):
                        manager.create(slug, payload(slug))
                generation = manager.status(slug)['generation']
                if point == 'create-reserved':
                    with self.assertRaises(owned.OwnedError):
                        manager.recover(slug, generation)
                else:
                    self.assertEqual(manager.recover(slug, generation)['state'], 'active')
                    manager.delete(slug, generation, 'obsolete')

    def test_update_commit_boundaries(self):
        for point in ('update-reserved', 'update-prepared', 'update-old-moved', 'update-published'):
            slug = point
            generation = self.manager.create(slug, payload(slug))['generation']
            with patch.dict(os.environ, {'GROWTH_LOOP_TEST_FAULT': point}):
                with self.assertRaises(owned.OwnedError):
                    self.manager.update(slug, generation, payload(slug, 'corrected'))
            with self.assertRaises(owned.OwnedError):
                self.manager.delete(slug, generation, 'obsolete')
            if point == 'update-reserved':
                with self.assertRaises(owned.OwnedError):
                    self.manager.recover(slug, generation)
            else:
                self.assertEqual(self.manager.recover(slug, generation)['state'], 'active')
                self.manager.delete(slug, generation, 'obsolete')

    def test_delete_intent_precedes_move_and_recovers_each_boundary(self):
        for point in ('delete-intent', 'delete-moved', 'delete-removed'):
            slug = point
            generation = self.manager.create(slug, payload(slug))['generation']
            with patch.dict(os.environ, {'GROWTH_LOOP_TEST_FAULT': point}):
                with self.assertRaises(owned.OwnedError):
                    self.manager.delete(slug, generation, 'obsolete')
            self.assertEqual(self.manager.status(slug)['state'], 'deleting')
            self.assertEqual(self.manager.recover(slug, generation)['state'], 'deleted')
            self.assertFalse((self.root / slug).exists())

    def test_partial_delete_and_foreign_replacement(self):
        generation = self.create()
        original = owned.PosixFS.unlink if os.name != 'nt' else None
        if original is None:
            self.skipTest('POSIX partial-deletion fault fixture')
        count = []
        def interrupted(fs, name, expected):
            original(fs, name, expected); count.append(name)
            if len(count) == 1:
                raise owned.OwnedError('interrupt after first removal')
        with patch.object(owned.PosixFS, 'unlink', interrupted):
            with self.assertRaises(owned.OwnedError):
                self.manager.delete('demo', generation, 'obsolete')
        self.assertEqual(self.manager.recover('demo', generation)['state'], 'deleted')
        fresh = self.create()
        with self.assertRaises(owned.OwnedError):
            self.manager.delete('demo', generation, 'obsolete')
        self.assertEqual(self.manager.status('demo')['generation'], fresh)

    @unittest.skipIf(os.name == 'nt', 'POSIX directory race fixture')
    def test_directory_swap_during_move_preserves_foreign_payload(self):
        generation = self.create()
        other = self.root / 'foreign'; other.mkdir(mode=0o700)
        (other / 'SKILL.md').write_text('manual')
        real = owned.exclusive_rename
        def raced(fd, source, target):
            if source == 'demo':
                real(fd, 'demo', 'saved-owned')
                real(fd, 'foreign', 'demo')
            return real(fd, source, target)
        with patch.object(owned, 'exclusive_rename', raced):
            with self.assertRaises(owned.OwnedError):
                self.manager.delete('demo', generation, 'obsolete')
        self.assertTrue((self.root / 'saved-owned/SKILL.md').exists())
        self.assertEqual((self.root / ('.gl-delete-' + generation) / 'SKILL.md').read_text(), 'manual')

    @unittest.skipIf(os.name == 'nt', 'POSIX exclusive rename fixture')
    def test_exclusive_publish_does_not_replace_an_empty_foreign_directory(self):
        with owned.PosixFS.root(self.root) as fs:
            fs.mkdir('source'); fs.mkdir('manual')
            with fs.directory('source') as source:
                expected = source.ident()
            with self.assertRaises((owned.OwnedError, OSError)):
                fs.move('source', 'manual', expected)
            self.assertTrue((self.root / 'manual').is_dir())

    def test_corrupt_ledger_refuses(self):
        generation = self.create()
        if os.name == 'nt':
            from owned_windows import WindowsLedger
            path = self.data / 'growth-loop-owned' / WindowsLedger.NAME
        else:
            path = self.data / 'growth-loop-owned/ledger.json'
        path.write_text('{invalid')
        with self.assertRaises((ValueError, OSError)):
            self.manager.delete('demo', generation, 'obsolete')
        self.assertTrue((self.root / 'demo/SKILL.md').exists())

    def test_root_replacement_hardlink_and_concurrent_lock_refuse(self):
        generation = self.create()
        with self.manager.transaction():
            with self.assertRaises((owned.OwnedError, OSError)):
                self.manager.status('demo')
        os.link(self.root / 'demo/SKILL.md', self.base / 'keep-hardlink')
        with self.assertRaises((owned.OwnedError, OSError)):
            self.manager.delete('demo', generation, 'obsolete')
        self.assertTrue((self.base / 'keep-hardlink').exists())
        (self.base / 'keep-hardlink').unlink()
        self.root.rename(self.base / 'original-root')
        self.root.mkdir(mode=0o700)
        with self.assertRaises(owned.OwnedError):
            self.manager.status('demo')
        self.assertTrue((self.base / 'original-root/demo/SKILL.md').exists())


if __name__ == '__main__':
    unittest.main()
