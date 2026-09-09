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

    def test_editor_dates_remain_yaml_dates_for_topic_sorting(self):
        meta = {'updated': '2026-09-10', 'title': 'Test'}
        rendered = admin.serialize(meta, 'Body')
        parsed, _ = admin.frontmatter(rendered)
        self.assertEqual(parsed['updated'], admin.datetime.date(2026, 9, 10))
        self.assertEqual(meta['updated'], '2026-09-10')

    def test_delete_draft_preserves_backup_and_rejects_stale_delete(self):
        doc = admin.create({'group': 'articles', 'slug': 'test', 'title': 'Draft'})
        doc['body'] = 'Latest writing'
        saved = admin.save_draft(doc)
        with self.assertRaises(ValueError):
            admin.delete_draft(doc)
        admin.delete_draft(saved)
        self.assertFalse(admin.draft_path(doc['id']).exists())
        backup = next((admin.STATE / 'history').glob('deleted-*.json'))
        self.assertEqual(json.loads(backup.read_text())['body'], 'Latest writing')
        self.assertNotIn(doc['id'], [r['id'] for r in admin.records()])

    def test_delete_rejects_existing_site_content(self):
        doc = self.draft()
        with self.assertRaises(ValueError):
            admin.delete_draft(doc)
        self.assertTrue(admin.draft_path('home').exists())
        self.assertTrue((self.root / '_data/editorial.yml').exists())

    def test_external_edit_prevents_apply(self):
        self.draft()
        admin.atomic(self.root / '_data/editorial.yml', 'title: External\n')
        with self.assertRaisesRegex(ValueError, '冲突'):
            admin.materialize(['home'])

    def test_live_preview_does_not_save_or_apply(self):
        saved = self.draft()
        live = dict(saved, meta={'title': 'Unsaved preview'})
        before = admin.draft_path('home').read_bytes()
        def build(root, output):
            self.assertIn('Unsaved preview', (root / '_data/editorial.yml').read_text())
            output.mkdir()
            return 'ok'
        with patch.object(admin, 'jekyll', side_effect=build), patch.object(admin, 'start_preview', return_value='http://localhost:1234'):
            admin.preview([], live)
        self.assertEqual(admin.draft_path('home').read_bytes(), before)
        self.assertIn('Before', (self.root / '_data/editorial.yml').read_text())

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

    def test_release_error_survives_restart(self):
        class ImmediateThread:
            def __init__(self, target, **kwargs):
                self.target = target
            def start(self):
                self.target()
        def publish():
            raise ValueError('模拟推送失败')
        with patch.object(admin.threading, 'Thread', ImmediateThread):
            job = admin.task(publish)
        admin.JOBS.pop(job['job'])
        self.assertEqual(admin.last_release()['error'], '模拟推送失败')
        self.assertEqual(admin.last_release()['status'], 'failed')

    def test_interrupted_release_is_not_reported_as_success(self):
        admin.atomic(admin.STATE / 'last-release.json', admin.json_text({
            'job': 'old-process', 'status': 'running', 'stage': 'publish'}))
        self.assertEqual(admin.last_release()['status'], 'failed')
        self.assertIn('结果未知', admin.last_release()['error'])


if __name__ == '__main__':
    unittest.main()
