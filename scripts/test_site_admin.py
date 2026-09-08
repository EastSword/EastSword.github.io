import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import site_admin as admin


class AdminTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name).resolve() / 'site'
        self.root.mkdir()
        self.patches = [patch.object(admin, 'SITE', self.root),
                        patch.object(admin, 'STATE', Path(self.temp.name) / 'state')]
        for p in self.patches:
            p.start()
        admin.atomic(self.root / 'scripts/articles.json', '{"articles": []}')
        admin.atomic(self.root / '_data/editorial.yml', 'title: Before\n')
        admin.run(['git', 'init', '-q'])
        admin.run(['git', 'config', 'user.email', 'test@example.invalid'])
        admin.run(['git', 'config', 'user.name', 'Test'])
        admin.run(['git', 'add', '.'])
        admin.run(['git', 'commit', '-qm', 'fixture'])

    def tearDown(self):
        for p in reversed(self.patches):
            p.stop()
        self.temp.cleanup()

    def draft(self):
        doc = admin.document('home')
        doc['meta']['title'] = 'After'
        return admin.save_draft(doc)

    def test_draft_isolation_and_stale_revision(self):
        old = admin.document('home')
        self.draft()
        self.assertIn('Before', (self.root / '_data/editorial.yml').read_text())
        with self.assertRaises(ValueError):
            admin.save_draft(old)

    def test_external_edit_prevents_apply(self):
        self.draft()
        admin.atomic(self.root / '_data/editorial.yml', 'title: External\n')
        with self.assertRaisesRegex(ValueError, '冲突'):
            admin.materialize(['home'])

    def test_failed_apply_restores_files_and_keeps_draft(self):
        self.draft()
        def fail(doc, root, real=False):
            admin.atomic(root / '_data/editorial.yml', 'damaged')
            admin.atomic(root / 'unexpected.txt', 'new')
            raise ValueError('failure')
        with patch.object(admin, 'preview'), patch.object(admin, 'apply_document', side_effect=fail):
            with self.assertRaises(ValueError):
                admin.materialize(['home'])
        self.assertIn('Before', (self.root / '_data/editorial.yml').read_text())
        self.assertFalse((self.root / 'unexpected.txt').exists())
        self.assertTrue(admin.document('home')['draft'])

    def test_release_checks_only_selected_files_without_staging(self):
        admin.atomic(self.root / '_data/editorial.yml', 'title: Selected\n')
        admin.atomic(self.root / 'unselected.txt', 'private draft')
        selected = [r for r in admin.changes() if r['path'] == '_data/editorial.yml']
        def build(root, output):
            self.assertFalse((root / 'unselected.txt').exists())
            self.assertIn('Selected', (root / '_data/editorial.yml').read_text())
            return 'build passed'
        with patch.object(admin, 'jekyll', side_effect=build):
            result = admin.release_check({'files': selected})
        self.assertTrue(result['proof'])
        self.assertEqual(admin.run(['git', 'diff', '--cached', '--name-only']), '')
        admin.atomic(self.root / '_data/editorial.yml', 'title: Changed again\n')
        with self.assertRaises(ValueError):
            admin.reviewed_paths({'files': selected})


if __name__ == '__main__':
    unittest.main()
