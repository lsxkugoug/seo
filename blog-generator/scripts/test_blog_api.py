import argparse
import copy
import importlib.util
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

import blog_api as api

ROOT = Path(__file__).resolve().parents[1]


def item(number):
    return {'content_id': 'blog_' + str(number), 'title': 'Article ' + str(number),
            'url': 'https://example.com/blog/' + str(number), 'status': 'live',
            'body': 'Distinct full article body ' + str(number)}


def page(items, total, cursor=None, snapshot='snapshot-1'):
    return {'snapshot_id': snapshot, 'coverage': {'status': 'complete', 'live': total,
            'archived': 0, 'merged': 0, 'redirected': 0, 'known_gaps': []},
            'items': items, 'next_cursor': cursor}


class BlogApiTests(unittest.TestCase):
    def setUp(self):
        self.config = json.loads((ROOT / 'config/projects/humanizer.example.json').read_text())

    def test_all_112_articles_are_fetched_and_saved(self):
        pages = [page([item(n) for n in range(1, 101)], 112, 'page-2'),
                 page([item(n) for n in range(101, 113)], 112)]
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / 'inventory.json'
            args = argparse.Namespace(config=Path('/unused'), output=output)
            with patch.object(api, 'load_config', return_value=self.config), patch.object(api, 'request', side_effect=pages) as request, redirect_stdout(io.StringIO()):
                self.assertEqual(api.inventory_command(args), 0)
            self.assertEqual(request.call_count, 2)
            self.assertEqual(request.call_args.kwargs['query']['cursor'], 'page-2')
            saved = json.loads(output.read_text())
            self.assertEqual(len(saved['items']), 112)
            self.assertEqual(saved['items'][-1]['body'], item(112)['body'])

    def test_incomplete_or_changing_inventory_fails_closed(self):
        scenarios = [
            [page([item(1)], 2)],
            [page([item(1)], 2, 'next'), page([item(2)], 2, snapshot='changed')],
            [page([item(1)], 2, 'next'), page([item(2)], 3)],
            [page([item(1)], 2, 'next'), page([item(1)], 2)],
            [page([item(1)], 3, 'next'), page([item(2)], 3, 'next')],
            [page([], 1, 'next')],
        ]
        for responses in scenarios:
            with self.subTest(responses=responses), patch.object(api, 'request', side_effect=responses):
                with self.assertRaises(ValueError):
                    api.fetch_inventory(self.config)

    def test_bad_coverage_and_missing_body_are_rejected(self):
        for change in [lambda p: p['coverage'].update(known_gaps=['missing archive']),
                       lambda p: p['coverage'].update(live=True),
                       lambda p: p['items'][0].pop('body'),
                       lambda p: p.update(next_cursor=[]),
                       lambda p: p['items'][0].update(status='unknown')]:
            p = page([item(1)], 1)
            change(p)
            with patch.object(api, 'request', return_value=p), self.assertRaises(ValueError):
                api.fetch_inventory(self.config)

    def test_archived_and_redirected_counts_must_match(self):
        p = page([item(1)], 1)
        p['coverage']['redirected'] = 1
        with self.assertRaises(ValueError):
            api.validate_complete_inventory(p)

    def test_empty_complete_inventory(self):
        with patch.object(api, 'request', return_value=page([], 0)):
            self.assertEqual(api.fetch_inventory(self.config)['items'], [])

    def test_redirects_never_forward_credentials(self):
        from urllib.request import Request
        req = Request('https://example.com/internal/blogs', headers={'X-Blog-API-Key': 'test-only'})
        for code in [301, 302, 303, 307, 308]:
            with self.subTest(code=code), self.assertRaises(RuntimeError):
                api.NoRedirects().redirect_request(req, None, code, '', {}, 'https://other.example/')

    def _payload(self):
        link = {'target_content_id': 'blog_1', 'target_url': item(1)['url'],
                'anchor_text': 'guide', 'relation': 'prerequisite', 'placement': 'intro'}
        return {'schema_version': 'publish-blog-v1', 'project_id': 'humanizer',
                'inventory_snapshot_id': 'snapshot-1', 'idempotency_key': 'key-1',
                'article': {'title': 'New article', 'slug': 'new-article', 'excerpt': 'excerpt',
                            'content_markdown': 'Read [guide](' + item(1)['url'] + ').',
                            'author': 'Editorial', 'tag': 'Writing', 'read_time': '2 min',
                            'image': 'https://example.com/image.png', 'internal_links': [link]},
                'review': {'status': 'approved', 'checks_passed': list(api.REQUIRED_CHECKS)},
                'dedupe': {'body_reviewed': True, 'content_disposition': 'new'}}

    def _publish(self, inventory, payload, execute, fresh=None):
        with tempfile.TemporaryDirectory() as folder:
            inventory_path, payload_path = Path(folder) / 'inventory.json', Path(folder) / 'payload.json'
            inventory_path.write_text(json.dumps(inventory)); payload_path.write_text(json.dumps(payload))
            args = argparse.Namespace(config=Path('/unused'), inventory=inventory_path,
                                      payload=payload_path, execute=execute)
            with patch.object(api, 'load_config', return_value=self.config), patch.object(api, 'fetch_inventory', return_value=fresh or inventory) as fetch, patch.object(api, 'request', return_value={'idempotency_key': 'key-1', 'status': 'published'}) as publish, redirect_stdout(io.StringIO()):
                try:
                    result = api.publish_command(args)
                    return result, fetch.call_count, publish.call_count
                except ValueError:
                    self.assertEqual(publish.call_count, 0)
                    raise

    def test_offline_preflight_does_not_publish(self):
        self.assertEqual(self._publish(page([item(1)], 1), self._payload(), False), (0, 0, 0))

    def test_execute_rechecks_inventory_before_post(self):
        self.assertEqual(self._publish(page([item(1)], 1), self._payload(), True), (0, 1, 1))

    def test_stale_or_incomplete_inventory_never_posts(self):
        inventory = page([item(1)], 1)
        with self.assertRaises(ValueError):
            self._publish(inventory, self._payload(), True, page([item(1)], 1, snapshot='new'))
        with self.assertRaises(ValueError):
            self._publish(page([item(1)], 2, 'page-2'), self._payload(), True)
        p = self._payload(); p['inventory_snapshot_id'] = 'old'
        with self.assertRaises(ValueError):
            self._publish(inventory, p, True)

    def test_update_and_wrong_project_never_post(self):
        for change in [lambda p: p.update(project_id='wrong'),
                       lambda p: p['dedupe'].update(content_disposition='update'),
                       lambda p: p['review'].update(checks_passed=[{}])]:
            p = self._payload(); change(p)
            with self.assertRaises(ValueError):
                self._publish(page([item(1)], 1), p, True)

    def test_missing_contextual_link_never_posts(self):
        p = self._payload(); p['article']['content_markdown'] = 'No link'
        with self.assertRaises(ValueError):
            self._publish(page([item(1)], 1), p, True)

    def test_manual_review_mode_never_posts(self):
        self.config['apis']['publish']['mode'] = 'manual_review'
        with self.assertRaises(ValueError):
            self._publish(page([item(1)], 1), self._payload(), True)

    def test_invalid_config_shapes_are_errors(self):
        for change in [lambda c: c.update(schema_version='other'),
                       lambda c: c['apis']['history'].update(query={'cursor': 'old'}),
                       lambda c: c['apis']['history'].update(query={'limit': True}),
                       lambda c: c['apis']['publish'].update(url='https://user:pass@example.com/publish'),
                       lambda c: c['internal_link_policy'].update(min_contextual_historical_links=True),
                       lambda c: c['apis']['publish'].update(mode=[])]:
            c = copy.deepcopy(self.config); change(c)
            with self.assertRaises(ValueError):
                api.project_config.validate(c, allow_template_urls=False)


if __name__ == '__main__':
    unittest.main()
