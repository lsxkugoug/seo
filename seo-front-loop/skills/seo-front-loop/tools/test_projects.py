"""Project isolation checks, entirely offline."""
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import collect_metrics as m
from list_projects import discover
from seo_context import config, project_path, resolved_settings


class ProjectTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        for name in ("a", "b"):
            folder = self.root / "projects" / name
            folder.mkdir(parents=True)
            (folder / "config").write_text("SEO_GSC_TOKEN_ENV=" + name.upper() + "_TOKEN\n", encoding="utf-8")
            (folder / "seo-keywords.json").write_text(json.dumps({"primary": [name], "secondary": [], "excluded": []}), encoding="utf-8")
        self.a = self.root / "projects/a"
        self.b = self.root / "projects/b"

    def test_list_does_not_read_keywords_or_memory(self):
        (self.a / "seo-keywords.json").write_text("invalid private data")
        self.assertEqual([p["name"] for p in discover(self.root)], ["a", "b"])

    def test_collection_cannot_silently_run_root_config(self):
        (self.root / "config").write_text("SEO_REVIEW_INTERVAL_DAYS=20")
        with self.assertRaises(ValueError):
            resolved_settings(self.root, {})

    def test_keywords_and_memory_are_separate(self):
        a, b = config(self.a, {}), config(self.b, {})
        self.assertEqual(a["keywords"]["primary"], ["a"])
        self.assertEqual(b["keywords"]["primary"], ["b"])
        self.assertNotEqual(a["memory_dir"], b["memory_dir"])

    def test_paths_cannot_escape(self):
        root = self.a.resolve()
        for value in ("../b/seo-keywords.json", str(self.b / ".seo-memory"), "."):
            with self.subTest(value=value), self.assertRaises(ValueError):
                project_path(root, value)
        (self.a / "link").symlink_to(self.b, target_is_directory=True)
        with self.assertRaises(ValueError):
            project_path(root, "link/history.md")

    def test_global_target_override_rejected_but_time_allowed(self):
        with self.assertRaises(ValueError):
            resolved_settings(self.a, {"SEO_MEMORY_DIR": str(self.b / ".seo-memory")})
        self.assertEqual(config(self.a, {"SEO_REVIEW_INTERVAL_DAYS": "7"})["review_policy"]["interval_days"], 7)

    def test_config_symlink_cannot_borrow_another_project(self):
        isolated = self.root / "projects/c"
        isolated.mkdir()
        (isolated / "config").symlink_to(self.a / "config")
        with self.assertRaises(ValueError):
            resolved_settings(isolated, {})

    def test_named_tokens_do_not_fall_back(self):
        cfg = m.settings(self.a, {})
        cfg["SEO_GSC_PROPERTY"] = "sc-domain:example.com"
        report = m.preflight(cfg, "gsc", {"B_TOKEN": "b", "GSC_ACCESS_TOKEN": "global"})
        self.assertTrue(report["missing"])
        with patch.dict(os.environ, {"A_TOKEN": "a", "B_TOKEN": "b"}, clear=True):
            self.assertEqual(m.token_for(cfg, "gsc"), "a")

    def test_missing_project_does_not_read_parent(self):
        blank = self.root / "projects/new"
        blank.mkdir()
        self.assertEqual(m.settings(blank, {})["SEO_GSC_TOKEN_ENV"], "")
        with self.assertRaises(OSError):
            config(blank, {})


if __name__ == "__main__":
    unittest.main()
