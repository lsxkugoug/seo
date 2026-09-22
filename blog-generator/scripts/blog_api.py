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
from urllib.request import Request, HTTPRedirectHandler, build_opener

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


class NoRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # Never forward the shared secret to a redirected destination.
        raise RuntimeError('API redirects are not allowed; configure the final HTTPS endpoint')


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
        with build_opener(NoRedirects()).open(Request(url, data=body, headers=headers, method=api["method"]), timeout=30) as response:
            result = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        raise RuntimeError(f"API returned HTTP {exc.code}") from exc
    except URLError as exc:
        raise RuntimeError("API request failed before a response was received") from exc
    if not isinstance(result, dict):
        raise ValueError("API response must be a JSON object")
    return result


def validate_inventory(payload: dict) -> None:
    if not isinstance(payload, dict):
        raise ValueError("inventory response must be an object")
    coverage = payload.get("coverage")
    if not isinstance(coverage, dict) or coverage.get("status") != "complete":
        raise ValueError("inventory response is not complete")
    if coverage.get("known_gaps") != []:
        raise ValueError("inventory coverage has gaps or omits known_gaps")
    for field in ("live", "archived", "merged", "redirected"):
        if type(coverage.get(field)) is not int or coverage[field] < 0:
            raise ValueError("inventory coverage counts must be non-negative integers")
    if not isinstance(payload.get("snapshot_id"), str) or not payload["snapshot_id"]:
        raise ValueError("inventory response has no snapshot_id")
    if not isinstance(payload.get("items"), list):
        raise ValueError("inventory response has no items list")
    cursor = payload.get("next_cursor")
    if cursor is not None and (not isinstance(cursor, str) or not cursor):
        raise ValueError("invalid inventory cursor")
    for item in payload["items"]:
        if not isinstance(item, dict) or not all(isinstance(item.get(k), str) and item[k] for k in ("content_id", "url", "title")):
            raise ValueError("inventory item needs content_id, url and title")
        if item.get("status") not in ("live", "archived", "merged", "redirected"):
            raise ValueError("invalid inventory item status")
        if not isinstance(item.get("body"), str) or (item["status"] == "live" and not item["body"].strip()):
            raise ValueError("inventory item is missing the body needed for deduplication")


def validate_complete_inventory(payload: dict) -> None:
    validate_inventory(payload)
    if payload.get("next_cursor") is not None:
        raise ValueError("inventory has unread pages")
    seen = set()
    counts = dict.fromkeys(("live", "archived", "merged", "redirected"), 0)
    for item in payload["items"]:
        if item["content_id"] in seen:
            raise ValueError("inventory contains duplicate content IDs")
        seen.add(item["content_id"])
        counts[item["status"]] += 1
    if any(payload["coverage"][status] != count for status, count in counts.items()):
        raise ValueError("inventory item counts do not match declared coverage")


def fetch_inventory(config: dict) -> dict:
    api = config["apis"]["history"]
    query = dict(api.get("query", {}))
    if "cursor" in query:
        raise ValueError("history query must start at the first page")
    items, cursors, ids = [], set(), set()
    snapshot = coverage = None
    for _ in range(10000):
        page = request(api, query=query)
        validate_inventory(page)
        if snapshot is None:
            snapshot, coverage = page["snapshot_id"], page["coverage"]
        elif snapshot != page["snapshot_id"] or coverage != page["coverage"]:
            raise ValueError("inventory changed while reading pages; retrieve history again")
        for item in page["items"]:
            if item["content_id"] in ids:
                raise ValueError("inventory repeats a content ID across pages")
            ids.add(item["content_id"])
            items.append(item)
        cursor = page.get("next_cursor")
        if cursor is None:
            result = {"snapshot_id": snapshot, "coverage": coverage, "items": items, "next_cursor": None}
            validate_complete_inventory(result)
            return result
        if not page["items"] or cursor in cursors:
            raise ValueError("inventory cursor did not make progress")
        cursors.add(cursor)
        query["cursor"] = cursor
    raise ValueError("inventory exceeded pagination safety limit")


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
    checks = review.get("checks_passed")
    if not isinstance(checks, list) or not all(isinstance(check, str) for check in checks) or not REQUIRED_CHECKS.issubset(set(checks)):
        raise ValueError("payload review is missing required checks")
    dedupe = payload.get("dedupe")
    if not isinstance(dedupe, dict) or dedupe.get("content_disposition") != "new" or dedupe.get("body_reviewed") is not True:
        raise ValueError("payload must contain an approved body-level dedupe result for a new article; automated updates are disabled")


def inventory_command(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    result = fetch_inventory(config)
    serialized = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        args.output.write_text(serialized + "\n", encoding="utf-8")
        print(json.dumps({"snapshot_id": result["snapshot_id"], "item_count": len(result["items"]), "output": str(args.output)}, ensure_ascii=False))
    else:
        print(serialized)
    return 0


def publish_command(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    api = config["apis"]["publish"]
    payload = load_json(args.payload)
    validate_publish_payload(payload, config)
    inventory = load_json(args.inventory)
    validate_complete_inventory(inventory)
    if inventory["snapshot_id"] != payload["inventory_snapshot_id"]:
        raise ValueError("payload was reviewed against a different inventory")
    targets = {item["content_id"]: item for item in inventory["items"]}
    for link in payload["article"]["internal_links"]:
        target = targets.get(link["target_content_id"])
        if target is None or target["status"] != "live" or target["url"] != link["target_url"]:
            raise ValueError("internal link target is not in the reviewed inventory")
        if f"[{link['anchor_text']}]({link['target_url']})" not in payload["article"]["content_markdown"]:
            raise ValueError("internal link does not appear in the article body")
    if api["mode"] != "auto_after_review":
        raise ValueError("project publish mode is manual_review; refusing API call")
    summary = {"project_id": payload["project_id"], "slug": payload["article"]["slug"], "idempotency_key": payload["idempotency_key"], "content_chars": len(payload["article"]["content_markdown"])}
    if not args.execute:
        print(json.dumps({"status": "preflight_passed", **summary}, ensure_ascii=False))
        return 0
    fresh = fetch_inventory(config)
    if fresh["snapshot_id"] != inventory["snapshot_id"] or fresh["items"] != inventory["items"]:
        raise ValueError("inventory changed after review; retrieve history and review again")
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
    inventory.add_argument("--output", type=Path, help="save all validated articles for review and publication preflight")
    inventory.set_defaults(func=inventory_command)
    publish = subparsers.add_parser("publish")
    publish.add_argument("--config", type=Path, required=True)
    publish.add_argument("--payload", type=Path, required=True)
    publish.add_argument("--inventory", type=Path, required=True, help="complete inventory used for editorial review")
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
