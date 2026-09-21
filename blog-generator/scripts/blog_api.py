#!/usr/bin/env python3
"""Read a Blog Generator inventory or publish a review-approved article.

No secret is accepted as an argument. Authentication comes only from the
project config's secret_env environment variable.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

VALIDATOR_PATH = Path(__file__).with_name("validate_project_config.py")
spec = importlib.util.spec_from_file_location("project_config", VALIDATOR_PATH)
project_config = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(project_config)

REQUIRED_CHECKS = {"dedupe", "facts", "scope", "structure", "internal_links"}


def load_config(path: Path) -> dict:
    config = json.loads(path.read_text(encoding="utf-8"))
    project_config.validate(config, allow_template_urls=False)
    return config


def load_json(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def get_secret(api: dict) -> str:
    env_name = api["auth"]["secret_env"]
    value = os.environ.get(env_name)
    if not value:
        raise ValueError(f"required environment variable {env_name} is not set")
    return value


def request(api: dict, *, query: dict | None = None, payload: dict | None = None) -> dict:
    secret = get_secret(api)
    url = api["url"]
    if query:
        url += ("&" if "?" in url else "?") + urlencode(query)
    headers = {api["auth"]["header"]: secret, "Accept": "application/json"}
    body = None
    if payload is not None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"
        headers[api["idempotency_header"]] = payload["idempotency_key"]
    try:
        with urlopen(Request(url, data=body, headers=headers, method=api["method"]), timeout=30) as response:
            result = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        raise RuntimeError(f"API returned HTTP {exc.code}") from exc
    except URLError as exc:
        raise RuntimeError("API request failed before a response was received") from exc
    if not isinstance(result, dict):
        raise ValueError("API response must be a JSON object")
    return result


def validate_inventory(payload: dict) -> None:
    coverage = payload.get("coverage")
    if not isinstance(coverage, dict) or coverage.get("status") != "complete":
        raise ValueError("inventory response is not complete")
    if not isinstance(payload.get("snapshot_id"), str) or not payload["snapshot_id"]:
        raise ValueError("inventory response has no snapshot_id")
    if not isinstance(payload.get("items"), list):
        raise ValueError("inventory response has no items list")


def validate_publish_payload(payload: dict, config: dict) -> None:
    if payload.get("schema_version") != "publish-blog-v1":
        raise ValueError("payload schema_version must be publish-blog-v1")
    if payload.get("project_id") != config["project_id"]:
        raise ValueError("payload project_id does not match config")
    for field in ("idempotency_key", "inventory_snapshot_id"):
        if not isinstance(payload.get(field), str) or not payload[field]:
            raise ValueError(f"payload {field} is required")
    article = payload.get("article")
    if not isinstance(article, dict):
        raise ValueError("payload article is required")
    for field in ("title", "slug", "excerpt", "content_markdown", "author", "tag", "read_time", "image"):
        if not isinstance(article.get(field), str) or not article[field].strip():
            raise ValueError(f"article.{field} is required")
    links = article.get("internal_links")
    if not isinstance(links, list) or len(links) < config["internal_link_policy"]["min_contextual_historical_links"]:
        raise ValueError("payload does not meet required historical internal links")
    for link in links:
        if not isinstance(link, dict) or not all(isinstance(link.get(k), str) and link[k] for k in ("target_content_id", "target_url", "anchor_text", "relation", "placement")):
            raise ValueError("every internal link needs content ID, URL, anchor, relation and placement")
    review = payload.get("review")
    if not isinstance(review, dict) or review.get("status") != "approved":
        raise ValueError("payload review.status must be approved")
    if not REQUIRED_CHECKS.issubset(set(review.get("checks_passed", []))):
        raise ValueError("payload review is missing required checks")
    dedupe = payload.get("dedupe")
    if not isinstance(dedupe, dict) or dedupe.get("content_disposition") not in {"new", "update"} or dedupe.get("body_reviewed") is not True:
        raise ValueError("payload must contain an approved body-level dedupe result")


def inventory_command(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    api = config["apis"]["history"]
    result = request(api, query=api.get("query", {}))
    validate_inventory(result)
    print(json.dumps({"snapshot_id": result["snapshot_id"], "coverage": result["coverage"], "item_count": len(result["items"])}, ensure_ascii=False))
    return 0


def publish_command(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    api = config["apis"]["publish"]
    payload = load_json(args.payload)
    validate_publish_payload(payload, config)
    if api["mode"] != "auto_after_review":
        raise ValueError("project publish mode is manual_review; refusing API call")
    summary = {"project_id": payload["project_id"], "slug": payload["article"]["slug"], "idempotency_key": payload["idempotency_key"], "content_chars": len(payload["article"]["content_markdown"])}
    if not args.execute:
        print(json.dumps({"status": "preflight_passed", **summary}, ensure_ascii=False))
        return 0
    result = request(api, payload=payload)
    if result.get("idempotency_key") != payload["idempotency_key"]:
        raise ValueError("publish response did not confirm the submitted idempotency key")
    print(json.dumps({"status": result.get("status"), "publication_id": result.get("publication_id"), "url": result.get("url"), "content_id": result.get("content_id"), "idempotency_key": result.get("idempotency_key")}, ensure_ascii=False))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    inventory = subparsers.add_parser("inventory")
    inventory.add_argument("--config", type=Path, required=True)
    inventory.set_defaults(func=inventory_command)
    publish = subparsers.add_parser("publish")
    publish.add_argument("--config", type=Path, required=True)
    publish.add_argument("--payload", type=Path, required=True)
    publish.add_argument("--execute", action="store_true", help="send the reviewed payload to the configured API")
    publish.set_defaults(func=publish_command)
    args = parser.parse_args()
    try:
        return args.func(args)
    except (OSError, json.JSONDecodeError, ValueError, RuntimeError) as exc:
        print(f"BLOCKED: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
