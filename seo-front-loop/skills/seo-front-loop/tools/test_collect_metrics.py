"""Offline contracts: no live network, no real credentials."""
import contextlib
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import urllib.error

import collect_metrics as m


class MetricsTests(unittest.TestCase):
    def setUp(self):
        self.cfg = dict(m.DATA_DEFAULTS, SEO_GSC_PROPERTY="sc-domain:example.com",
                        SEO_POSTHOG_HOST="https://us.posthog.com", SEO_POSTHOG_PROJECT_ID="42",
                        SEO_GSC_TOKEN_ENV="GSC_ACCESS_TOKEN", SEO_POSTHOG_KEY_ENV="POSTHOG_PERSONAL_API_KEY",
                        SEO_GSC_CREDENTIALS_ENV="PROJECT_GOOGLE_FILE")

    def test_missing_config_never_contacts_network(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {}, clear=True), patch.object(m, "request") as http:
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                code = m.main(["--project", tmp])
            self.assertEqual(code, 2)
            self.assertEqual(json.loads(out.getvalue())["status"], "needs_user_input")
            self.assertFalse(http.called)
            self.assertEqual(list(Path(tmp).iterdir()), [])

    def test_configuration_does_not_need_keywords(self):
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, "config").write_text("SEO_POSTHOG_PROJECT_ID=4\n", encoding="utf-8")
            self.assertEqual(m.settings(tmp, {})["SEO_POSTHOG_PROJECT_ID"], "4")
            with self.assertRaises(ValueError):
                m.settings(tmp, {"SEO_POSTHOG_PROJECT_ID": "5"})

    def test_preflight_no_secret_output(self):
        value = m.preflight(self.cfg, "gsc", {"GSC_ACCESS_TOKEN": "fake-secret"})
        self.assertFalse(value["missing"])
        self.assertNotIn("fake-secret", json.dumps(value))
        self.assertFalse(value["access_verified"])

    def test_optional_conversion_definition(self):
        report = m.preflight(self.cfg, "posthog", {"POSTHOG_PERSONAL_API_KEY": "fake"})
        self.assertFalse(report["missing"])
        self.assertTrue(report["conversion_definition_needed"])

    def test_adc_preflight_does_not_refresh_credentials(self):
        cfg = dict(self.cfg, SEO_GSC_AUTH_MODE="adc")
        with patch.object(m, "token_for") as tokens:
            report = m.preflight(cfg, "gsc", {"PROJECT_GOOGLE_FILE": "/private/credential.json"})
        self.assertFalse(tokens.called)
        self.assertFalse(report["missing"])
        self.assertFalse(report["access_verified"])

    def test_single_provider_ignores_other_missing_service(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {"GSC_ACCESS_TOKEN": "fake"}, clear=True):
            Path(tmp, "config").write_text("SEO_GSC_PROPERTY=sc-domain:example.com\nSEO_GSC_TOKEN_ENV=GSC_ACCESS_TOKEN\n", encoding="utf-8")
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                code = m.main(["--project", tmp, "--provider", "gsc"])
            self.assertEqual(code, 0)
            self.assertEqual(len(json.loads(out.getvalue())["checks"]), 1)

    def test_unsafe_hosts(self):
        for host in ("http://example.com", "https://token@example.com", "https://example.com/x", "https://example.com?key=x"):
            with self.subTest(host=host), self.assertRaises(m.ToolError):
                m.origin(host)

    def test_redirects_do_not_forward_credentials(self):
        with self.assertRaises(m.ToolError):
            m.NoRedirect().redirect_request(None, None, 302, "", {}, "https://other.example")

    def test_http_error_does_not_echo_body_or_token(self):
        error = urllib.error.HTTPError("https://api.example", 403, "fake-secret", {}, io.BytesIO(b"fake-secret"))
        with patch.object(m.urllib.request, "build_opener") as opener:
            opener.return_value.open.side_effect = error
            with self.assertRaises(m.ToolError) as caught:
                m.request("https://api.example", "fake-secret")
            self.assertNotIn("fake-secret", str(caught.exception))
            self.assertIn("403", str(caught.exception))

    def test_gsc_pagination_and_separate_totals(self):
        calls = []
        def http(url, token, body):
            calls.append(body)
            return {"rows": [{"clicks": 1}] * (25000 if len(calls) == 2 else 1)}
        value = m.collect_gsc(self.cfg, "fake", "2026-08-01", "2026-08-28", "https://example.com/", http=http)
        self.assertEqual([b["startRow"] for b in calls], [0, 0, 25000])
        self.assertEqual(calls[0]["dimensions"], ["date"])
        self.assertEqual(calls[1]["dataState"], "final")
        self.assertEqual(value["timezone"], "America/Los_Angeles")
        self.assertIn("dimensionFilterGroups", calls[0])

    def test_pagination_cap_is_error(self):
        with self.assertRaises(m.ToolError):
            m.collect_gsc(self.cfg, "fake", "2026-08-01", "2026-08-01", max_pages=1,
                          http=lambda *a: {"rows": [{}] * 25000})

    def test_empty_gsc_not_filled_with_zero(self):
        result = m.collect_gsc(self.cfg, "fake", "2026-08-01", "2026-08-02", http=lambda *a: {})
        self.assertEqual(result["batches"]["daily_totals"][0]["response"], {})

    def test_query_encoding(self):
        cfg = dict(self.cfg, SEO_GSC_PROPERTY="https://example.com/")
        self.assertTrue(m.gsc_url(cfg).endswith("https%3A%2F%2Fexample.com%2F"))

    def test_posthog_window_literal_and_aggregate_only(self):
        calls = []
        def http(url, token, body):
            calls.append(body)
            return {"results": [], "columns": ["day", "event", "event_count"]}
        cfg = dict(self.cfg, SEO_POSTHOG_CONVERSION_EVENTS="signup,pay'event")
        result = m.collect_posthog(cfg, "fake", "2026-08-01", "2026-08-28", http=http)
        sql = calls[0]["query"]["query"]
        self.assertIn("2026-08-29", sql)
        self.assertIn("pay\\'event", sql)
        self.assertIn("count()", sql)
        # HogQL rejects ClickHouse's optional second argument to toDate.
        self.assertIn("toDate(toTimeZone(timestamp, 'UTC'))", sql)
        self.assertNotIn("toDate(timestamp, 'UTC')", sql)
        self.assertNotIn("distinct_id", sql)
        self.assertFalse(calls[0]["async"])
        self.assertEqual(result["results"], [])

    def test_posthog_pending_error_and_truncation(self):
        for body in ({}, {"results": [], "query_status": {"complete": False}},
                     {"results": [], "error": "fail"}, {"results": [], "hasMore": True}):
            with self.subTest(body=body), self.assertRaises(m.ToolError):
                m.posthog_query(self.cfg, "fake", "SELECT 1", http=lambda *a: body)

    def test_access_checks_actual_resource(self):
        self.assertTrue(m.check_access(self.cfg, "gsc", "fake", http=lambda *a: {"permissionLevel": "siteFullUser"})["access_verified"])
        with self.assertRaises(m.ToolError):
            m.check_access(self.cfg, "gsc", "fake", http=lambda *a: {"permissionLevel": "siteUnverifiedUser"})

    def test_dates_bounded(self):
        for first, last in (("2026-08-28", "2026-08-01"), ("2020-01-01", "2026-08-01")):
            with self.assertRaises(m.ToolError):
                m.date_range(first, last)

    def test_snapshot_exclusive_private(self):
        with tempfile.TemporaryDirectory() as tmp:
            file = Path(tmp, "snapshot.json")
            m.save_snapshot(file, {"original": True})
            with self.assertRaises(FileExistsError):
                m.save_snapshot(file, {"replacement": True})
            self.assertEqual(json.loads(file.read_text()), {"original": True})
            self.assertEqual(file.stat().st_mode & 0o777, 0o600)

    def test_failed_collection_does_not_save(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {"GSC_ACCESS_TOKEN": "fake"}, clear=True):
            Path(tmp, "config").write_text("SEO_GSC_PROPERTY=sc-domain:example.com\nSEO_GSC_TOKEN_ENV=GSC_ACCESS_TOKEN\n", encoding="utf-8")
            file = Path(tmp, "snapshot.json")
            with patch.object(m, "check_access", side_effect=m.ToolError("denied")), contextlib.redirect_stderr(io.StringIO()):
                code = m.main(["--project", tmp, "--provider", "gsc", "--collect", "--start", "2026-08-01",
                               "--end", "2026-08-28", "--output", str(file)])
            self.assertEqual(code, 2)
            self.assertFalse(file.exists())

    def test_interrupted_snapshot_does_not_publish_partial_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            file = Path(tmp, "snapshot.json")
            def interrupted(value, stream, **kwargs):
                stream.write('{"partial":')
                raise OSError("disk full")
            with patch.object(m.json, "dump", side_effect=interrupted), self.assertRaises(OSError):
                m.save_snapshot(file, {"ok": True})
            self.assertEqual(list(Path(tmp).iterdir()), [])


if __name__ == "__main__":
    unittest.main()
