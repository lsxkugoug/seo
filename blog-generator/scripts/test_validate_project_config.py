#!/usr/bin/env python3
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

MODULE = Path(__file__).with_name("validate_project_config.py")
spec = importlib.util.spec_from_file_location("validator", MODULE)
validator = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(validator)

HUMANIZER_EXAMPLE = Path(__file__).parents[1] / "config" / "projects" / "humanizer.example.json"
TEMPLATE_EXAMPLE = Path(__file__).parents[1] / "config" / "projects" / "project.example.json"


class ProjectConfigTests(unittest.TestCase):
    def test_humanizer_example_is_valid_template(self):
        data = json.loads(HUMANIZER_EXAMPLE.read_text(encoding="utf-8"))
        validator.validate(data, allow_template_urls=True)

    def test_template_endpoint_cannot_be_used_as_live_config(self):
        data = json.loads(TEMPLATE_EXAMPLE.read_text(encoding="utf-8"))
        with self.assertRaises(ValueError):
            validator.validate(data, allow_template_urls=False)

    def test_auth_rejects_raw_secret_field(self):
        data = json.loads(HUMANIZER_EXAMPLE.read_text(encoding="utf-8"))
        data["apis"]["publish"]["auth"]["api_key"] = "do-not-store-this"
        with self.assertRaises(ValueError):
            validator.validate(data, allow_template_urls=True)

    def test_config_must_use_expected_idempotency_contract(self):
        data = json.loads(HUMANIZER_EXAMPLE.read_text(encoding="utf-8"))
        data["apis"]["publish"]["payload_contract"] = "unknown"
        with self.assertRaises(ValueError):
            validator.validate(data, allow_template_urls=True)


if __name__ == "__main__":
    unittest.main()
