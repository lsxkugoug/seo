"""Offline behavioral tests; temporary fixtures never touch project state."""
import json
from pathlib import Path
import tempfile
import subprocess
import sys
import unittest

from seo_context import config, read_keywords, review_dates


class ConfigTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.words = {"primary": ["用户关键词"], "secondary": [], "excluded": [], "page_targets": {}}
        (self.root / "seo-keywords.json").write_text(json.dumps(self.words), encoding="utf-8")

    def test_defaults_and_empty_memory_are_not_adoption(self):
        value = config(self.root, {})
        self.assertEqual(value["review_policy"], {"interval_days": 20, "max_checks": 3})
        self.assertEqual(value["max_days_from_live_verification"], 60)
        self.assertFalse(value["memory_directory_exists"])
        self.assertNotIn("baseline_adopted", value)

    def test_env_precedence(self):
        (self.root / "config").write_text('SEO_REVIEW_INTERVAL_DAYS="10"\nSEO_REVIEW_MAX_CHECKS=4 # checks\n', encoding="utf-8")
        value = config(self.root, {"SEO_REVIEW_INTERVAL_DAYS": "7", "SECRET": "hidden"})
        self.assertEqual(value["max_days_from_live_verification"], 28)
        self.assertEqual(value["config_sources"]["SEO_REVIEW_INTERVAL_DAYS"], "process_environment")
        self.assertNotIn("hidden", json.dumps(value))

    def test_repository_configuration(self):
        self.assertIsNone(config(self.root, {})["repository_url"])
        (self.root / "config").write_text("SEO_REPOSITORY_URL=https://github.com/example/site\n", encoding="utf-8")
        self.assertEqual(config(self.root, {})["repository_url"], "https://github.com/example/site")
        with self.assertRaises(ValueError):
            config(self.root, {"SEO_REPOSITORY_URL": "https://github.com/example/other.git"})
        value = config(self.root, {})
        self.assertFalse(value["repository_access_verified"])

    def test_repository_credentials_and_invalid_urls_rejected(self):
        for url in ("https://token@github.com/example/site", "https://github.com/example/site?token=x",
                    "file:///tmp/site", "https://other.example/example/site", "git@github.com:example/site.git"):
            with self.subTest(url=url), self.assertRaises(ValueError):
                config(self.root, {"SEO_REPOSITORY_URL": url})

    def test_tracked_config_is_read_and_legacy_env_is_ignored(self):
        (self.root / "config").write_text("SEO_REVIEW_INTERVAL_DAYS=9\n", encoding="utf-8")
        (self.root / ".env").write_text("SEO_REVIEW_INTERVAL_DAYS=1\n", encoding="utf-8")
        value = config(self.root, {})
        self.assertEqual(value["review_policy"]["interval_days"], 9)
        self.assertEqual(value["config_sources"]["SEO_REVIEW_INTERVAL_DAYS"], "config")

    def test_invalid_intervals_fail(self):
        for raw in ("0", "-1", "", "1.5", "abc", "366", "$(echo 20)"):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                config(self.root, {"SEO_REVIEW_INTERVAL_DAYS": raw})

    def test_config_never_executes(self):
        marker = self.root / "must-not-exist"
        (self.root / "config").write_text("OTHER=$(touch " + str(marker) + ")\n", encoding="utf-8")
        config(self.root, {})
        self.assertFalse(marker.exists())

    def test_typo_and_duplicate_settings_fail(self):
        for content in ("SEO_REVEIW_INTERVAL_DAYS=2", "SEO_REVIEW_MAX_CHECKS=3\nSEO_REVIEW_MAX_CHECKS=4"):
            (self.root / "config").write_text(content, encoding="utf-8")
            with self.assertRaises(ValueError):
                config(self.root, {})

    def test_keyword_preservation_and_snapshot_change(self):
        original = config(self.root, {})
        self.assertEqual(original["keywords"]["primary"], ["用户关键词"])
        self.words["primary"].append("新方向")
        (self.root / "seo-keywords.json").write_text(json.dumps(self.words), encoding="utf-8")
        updated = config(self.root, {})
        self.assertNotEqual(original["keywords_hash"], updated["keywords_hash"])

    def test_keyword_conflict_and_bad_schema(self):
        for words in (
            {"primary": ["PDF  Tool"], "secondary": [], "excluded": ["pdf tool"]},
            {"primary": "wrong", "secondary": [], "excluded": []},
            {"primary": [], "secondary": [], "excluded": [], "page_targets": {"/x": [" "]}},
        ):
            (self.root / "seo-keywords.json").write_text(json.dumps(words), encoding="utf-8")
            with self.assertRaises(ValueError):
                config(self.root, {})

    def test_missing_file_and_duplicate_json_fail(self):
        with self.assertRaises(OSError):
            (self.root / "config").write_text("SEO_KEYWORDS_FILE=missing.json\n", encoding="utf-8")
            config(self.root, {})
        (self.root / "duplicate.json").write_text('{"primary": [], "primary": ["x"]}', encoding="utf-8")
        with self.assertRaises(ValueError):
            read_keywords(self.root / "duplicate.json")


class DateMathTests(unittest.TestCase):
    def test_twenty_day_dates(self):
        self.assertEqual(review_dates("2026-09-09T10:00:00+08:00", 20, 3),
                         ["2026-09-29T02:00:00Z", "2026-10-19T02:00:00Z", "2026-11-08T02:00:00Z"])

    def test_explicit_original_policy(self):
        self.assertEqual(review_dates("2026-09-09T02:00:00Z", 7, 3)[-1],
                         "2026-09-30T02:00:00Z")

    def test_no_timezone_or_bad_date_fails(self):
        for value in ("2026-09-09T02:00:00", "last week", "2026-02-30T00:00:00Z", None):
            with self.subTest(value=value), self.assertRaises(ValueError):
                review_dates(value, 20, 3)

    def test_invalid_policy_fails(self):
        for interval, count in ((0, 3), (20, 0), (-1, 3), (1.5, 3), (20, 13), (True, 3)):
            with self.subTest(interval=interval, count=count), self.assertRaises(ValueError):
                review_dates("2026-09-09T02:00:00Z", interval, count)

    def test_utc_elapsed_days_across_dst(self):
        self.assertEqual(review_dates("2026-10-30T10:00:00-07:00", 7, 1),
                         ["2026-11-06T17:00:00Z"])


class CliTests(unittest.TestCase):
    setUp = ConfigTests.setUp
    def run_cli(self, *args):
        return subprocess.run([sys.executable, "-B", str(Path(__file__).with_name("seo_context.py")),
                               "--project", str(self.root), *args], capture_output=True, text=True)

    def test_narrative_memory_is_not_parsed_or_modified(self):
        memory = self.root / ".seo-memory"
        memory.mkdir()
        note = memory / "E001.md"
        original = "这次已取消。旧周期是二十天，不能按当前设置重新上线。"
        note.write_text(original, encoding="utf-8")
        result = self.run_cli("--live-verified-at", "2026-09-09T02:00:00Z",
                              "--interval-days", "20", "--max-checks", "3")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len(json.loads(result.stdout)["calculated_review_dates"]), 3)
        self.assertEqual(note.read_text(encoding="utf-8"), original)
        self.assertEqual(list(memory.iterdir()), [note])

    def test_partial_date_args_do_not_fall_back_to_config(self):
        result = self.run_cli("--live-verified-at", "2026-09-09T02:00:00Z")
        self.assertEqual(result.returncode, 2)
        self.assertNotIn("calculated_review_dates", result.stdout)

    def test_old_record_cli_is_rejected(self):
        result = self.run_cli("--record", "old-experiment.json")
        self.assertEqual(result.returncode, 2)
        self.assertIn("unrecognized arguments", result.stderr)


if __name__ == "__main__":
    unittest.main()
