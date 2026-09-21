#!/usr/bin/env python3
"""Validate a Blog Generator project configuration without reading secrets."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from urllib.parse import urlparse

REQUIRED = {
    "schema_version", "project_id", "site", "content_scope", "keywords",
    "internal_link_policy", "apis",
}


def fail(message: str) -> None:
    raise ValueError(message)


def require_string(value: object, path: str) -> str:
    if not isinstance(value, str) or not value.strip():
        fail(f"{path} must be a non-empty string")
    return value


def validate_url(value: object, path: str, allow_template_urls: bool) -> None:
    url = require_string(value, path)
    if "<" in url or ">" in url:
        if allow_template_urls:
            return
        fail(f"{path} contains a template host; replace it before use")
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.netloc:
        fail(f"{path} must be an HTTPS URL")


def validate_auth(value: object, path: str) -> None:
    if not isinstance(value, dict):
        fail(f"{path} must be an object")
    require_string(value.get("header"), f"{path}.header")
    secret_env = require_string(value.get("secret_env"), f"{path}.secret_env")
    if not secret_env.endswith(("_KEY", "_TOKEN", "_SECRET")):
        fail(f"{path}.secret_env must name an environment variable, not contain a secret")
    forbidden = set(value) - {"header", "secret_env"}
    if forbidden:
        fail(f"{path} has unsupported fields: {', '.join(sorted(forbidden))}")


def validate(config: dict, allow_template_urls: bool) -> None:
    missing = REQUIRED - set(config)
    if missing:
        fail(f"missing root fields: {', '.join(sorted(missing))}")
    require_string(config["schema_version"], "schema_version")
    require_string(config["project_id"], "project_id")
    site = config["site"]
    if not isinstance(site, dict):
        fail("site must be an object")
    validate_url(site.get("base_url"), "site.base_url", allow_template_urls)
    for name in ("language", "country", "product_facts_source"):
        require_string(site.get(name), f"site.{name}")
    for section in ("content_scope", "keywords", "internal_link_policy"):
        if not isinstance(config[section], dict):
            fail(f"{section} must be an object")
    min_links = config["internal_link_policy"].get("min_contextual_historical_links")
    if not isinstance(min_links, int) or min_links < 0:
        fail("internal_link_policy.min_contextual_historical_links must be a non-negative integer")
    apis = config["apis"]
    if not isinstance(apis, dict) or set(apis) != {"history", "publish"}:
        fail("apis must contain exactly history and publish")
    for name, expected_method in (("history", "GET"), ("publish", "POST")):
        api = apis[name]
        if not isinstance(api, dict):
            fail(f"apis.{name} must be an object")
        validate_url(api.get("url"), f"apis.{name}.url", allow_template_urls)
        if api.get("method") != expected_method:
            fail(f"apis.{name}.method must be {expected_method}")
        validate_auth(api.get("auth"), f"apis.{name}.auth")
    publish = apis["publish"]
    if publish.get("mode") not in {"manual_review", "auto_after_review"}:
        fail("apis.publish.mode must be manual_review or auto_after_review")
    require_string(publish.get("idempotency_header"), "apis.publish.idempotency_header")
    if publish.get("payload_contract") != "publish-blog-v1":
        fail("apis.publish.payload_contract must be publish-blog-v1")
    if apis["history"].get("response_contract") != "inventory-v1":
        fail("apis.history.response_contract must be inventory-v1")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("config", type=Path)
    parser.add_argument("--allow-template-urls", action="store_true")
    args = parser.parse_args()
    try:
        data = json.loads(args.config.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            fail("root must be a JSON object")
        validate(data, args.allow_template_urls)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"INVALID: {exc}", file=sys.stderr)
        return 1
    print(f"VALID: {data['project_id']} ({data['apis']['publish']['mode']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
