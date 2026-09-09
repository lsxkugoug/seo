"""Offline behavioral tests; temporary fixtures never touch project state."""
import json
from pathlib import Path
import tempfile
import unittest

from seo_context import config, read_keywords, schedule, timestamp


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
            config(self.root, {"SEO_KEYWORDS_FILE": "missing.json"})
        (self.root / "duplicate.json").write_text('{"primary": [], "primary": ["x"]}', encoding="utf-8")
        with self.assertRaises(ValueError):
            read_keywords(self.root / "duplicate.json")


class ScheduleTests(unittest.TestCase):
    def setUp(self):
        self.record = {"review_policy": {"interval_days": 20, "max_checks": 3},
                       "live_verified_at": "2026-09-09T10:00:00+08:00", "reviews": [], "status": "observing"}

    def test_exact_day_twenty(self):
        before = schedule(self.record, timestamp("2026-09-29T01:59:59Z"))
        self.assertEqual(before["state"], "waiting")
        due = schedule(self.record, timestamp("2026-09-29T02:00:00Z"))
        self.assertEqual(due["due_checkpoints"], [1])
        self.assertFalse(due["deadline_reached"])

    def test_frozen_policy_not_global_settings(self):
        self.record["review_policy"]["interval_days"] = 7
        value = schedule(self.record, timestamp("2026-09-16T02:00:00Z"))
        self.assertEqual(value["due_checkpoints"], [1])
        self.assertEqual(value["deadline_at"], "2026-09-30T02:00:00Z")

    def test_no_deployment_no_clock(self):
        self.record["live_verified_at"] = None
        value = schedule(self.record, timestamp("2026-11-09T02:00:00Z"))
        self.assertEqual(value["state"], "awaiting_live_verification")

    def test_completed_review_next_checkpoint(self):
        self.record["reviews"] = [{"checkpoint": 1, "reviewed_at": "2026-09-29T02:00:00Z"}]
        value = schedule(self.record, timestamp("2026-09-30T02:00:00Z"))
        self.assertEqual(value["next_review_at"], "2026-10-19T02:00:00Z")

    def test_overdue_does_not_auto_close(self):
        value = schedule(self.record, timestamp("2026-11-09T02:00:00Z"))
        self.assertTrue(value["deadline_reached"])
        self.assertEqual(value["recommended_checkpoint"], 3)
        self.assertEqual(value["next_review_at"], "2026-11-08T02:00:00Z")
        self.assertEqual(value["missed_earlier_checkpoints"], [1, 2])
        self.assertEqual(value["state"], "review_due")
        self.assertEqual(self.record["status"], "observing")

    def test_closed_stays_closed(self):
        self.record["status"] = "closed"
        value = schedule(self.record, timestamp("2026-11-09T02:00:00Z"))
        self.assertEqual(value["due_checkpoints"], [])
        self.assertIsNone(value["next_review_at"])

    def test_cancelled_unpublished_is_terminal(self):
        for status in ("cancelled", "rejected"):
            value = schedule({"status": status}, timestamp("2026-11-09T02:00:00Z"))
            self.assertEqual(value["state"], "closed")
            self.assertIsNone(value["next_review_at"])

    def test_invalid_frozen_and_timestamps_fail(self):
        with self.assertRaises(ValueError):
            schedule({}, timestamp("2026-11-09T02:00:00Z"))
        with self.assertRaises(ValueError):
            timestamp("2026-09-09T02:00:00")
        with self.assertRaises(ValueError):
            schedule(self.record, timestamp("2026-09-08T02:00:00Z"))

    def test_early_review_rejected(self):
        self.record["reviews"] = [{"checkpoint": 1, "reviewed_at": "2026-09-10T02:00:00Z"}]
        with self.assertRaises(ValueError):
            schedule(self.record, timestamp("2026-10-19T02:00:00Z"))


if __name__ == "__main__":
    unittest.main()
