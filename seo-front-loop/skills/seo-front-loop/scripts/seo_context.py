#!/usr/bin/env python3
"""Read SEO config/keywords and frozen review dates. No writes, network or shell eval."""
import argparse
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import unicodedata

DEFAULTS = {
    "SEO_REVIEW_INTERVAL_DAYS": "20",
    "SEO_REVIEW_MAX_CHECKS": "3",
    "SEO_KEYWORDS_FILE": "seo-keywords.json",
    "SEO_MEMORY_DIR": ".seo-memory",
}


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                    separators=(",", ":")).encode()).hexdigest()


def load_json(file):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("Duplicate JSON key: " + key)
            result[key] = value
        return result
    return json.loads(Path(file).read_text(encoding="utf-8"), object_pairs_hook=unique)


def read_config(file):
    result = {}
    if not file.exists():
        return result
    for number, raw in enumerate(file.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].strip()
        key, sep, value = line.partition("=")
        key = key.strip()
        if not key.startswith("SEO_"):
            continue  # Never return or execute unrelated settings/secrets.
        if not sep or key not in DEFAULTS or key in result:
            raise ValueError("Invalid/unknown/duplicate SEO setting at config line " + str(number))
        value = value.strip()
        if value.startswith(("'", '"')):
            if len(value) < 2 or value[-1] != value[0]:
                raise ValueError("Unclosed quote at config line " + str(number))
            value = value[1:-1]
        else:
            value = re.split(r"\s+#", value, maxsplit=1)[0].strip()
        result[key] = value
    return result


def positive_int(value, label, maximum):
    if isinstance(value, bool) or not re.fullmatch(r"[0-9]+", str(value)):
        raise ValueError(label + " must be a positive integer")
    number = int(value)
    if not 1 <= number <= maximum:
        raise ValueError(label + " outside supported range 1.." + str(maximum))
    return number


def normalized(word):
    return " ".join(unicodedata.normalize("NFKC", word).casefold().split())


def word_list(value, label):
    if not isinstance(value, list):
        raise ValueError(label + " must be an array of strings")
    if any(not isinstance(word, str) or not word.strip() for word in value):
        raise ValueError(label + " contains a blank/non-string keyword")
    return value  # Preserve the user's exact wording and order.


def read_keywords(file):
    data = load_json(file)
    allowed = {"primary", "secondary", "excluded", "page_targets", "notes"}
    if not isinstance(data, dict) or set(data) - allowed:
        raise ValueError("Unknown keyword fields or non-object keyword file")
    for name in ("primary", "secondary", "excluded"):
        word_list(data.get(name), name)
    targets = data.get("page_targets", {})
    if not isinstance(targets, dict):
        raise ValueError("page_targets must be an object")
    for page, words in targets.items():
        if not page.strip():
            raise ValueError("Empty page target")
        word_list(words, "page_targets entry")
    if not isinstance(data.get("notes", ""), str):
        raise ValueError("notes must be a string")
    included = data["primary"] + data["secondary"] + [w for ws in targets.values() for w in ws]
    excluded = {normalized(w) for w in data["excluded"]}
    if any(normalized(w) in excluded for w in included):
        raise ValueError("A keyword is both targeted and excluded; resolve the conflict")
    return data


def config(project, environ=None):
    environ = os.environ if environ is None else environ
    project = Path(project).resolve(strict=True)
    if not project.is_dir():
        raise ValueError("project must be a directory")
    local = read_config(project / "config")
    values, sources = {}, {}
    for key, default in DEFAULTS.items():
        source = "process_environment" if key in environ else "config" if key in local else "default"
        values[key] = environ[key] if key in environ else local.get(key, default)
        sources[key] = source
        if not values[key] or "$" in values[key] or "`" in values[key] or "\n" in values[key]:
            raise ValueError(key + " is blank or contains unsupported interpolation")
    interval = positive_int(values["SEO_REVIEW_INTERVAL_DAYS"], "review interval", 365)
    checks = positive_int(values["SEO_REVIEW_MAX_CHECKS"], "max checks", 12)
    keyword_file = (project / values["SEO_KEYWORDS_FILE"]).resolve()
    memory_dir = (project / values["SEO_MEMORY_DIR"]).resolve()
    keywords = read_keywords(keyword_file)
    return {
        "project": str(project), "config_sources": sources,
        "review_policy": {"interval_days": interval, "max_checks": checks},
        "max_days_from_live_verification": interval * checks,
        "keywords_file": str(keyword_file), "keywords": keywords,
        "keywords_hash": digest(keywords), "memory_dir": str(memory_dir),
        "memory_directory_exists": memory_dir.is_dir(),
        "notice": "Read-only config, not history validation, SEO evaluation or publishing permission.",
    }


def timestamp(value):
    if not isinstance(value, str):
        raise ValueError("Timestamp must be an ISO-8601 string with timezone")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("Timestamp requires an explicit timezone")
    return parsed.astimezone(timezone.utc)


def iso(value):
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def schedule(record, now):
    if not isinstance(record, dict):
        raise ValueError("Experiment record must be an object")
    if record.get("status") in {"closed", "cancelled", "rejected"}:
        return {"state": "closed", "next_review_at": None, "due_checkpoints": []}
    policy = record.get("review_policy")
    if not isinstance(policy, dict):
        raise ValueError("Missing frozen review_policy; do not substitute current config")
    interval = positive_int(policy.get("interval_days"), "frozen interval", 365)
    count = positive_int(policy.get("max_checks"), "frozen max checks", 12)
    if not record.get("live_verified_at"):
        return {"state": "awaiting_live_verification", "next_review_at": None}
    live = timestamp(record["live_verified_at"])
    if live > now:
        raise ValueError("live_verified_at is in the future")
    dates = [live + timedelta(days=interval * i) for i in range(1, count + 1)]
    reviews = record.get("reviews", [])
    if not isinstance(reviews, list):
        raise ValueError("reviews must be an array")
    done = set()
    for review in reviews:
        if not isinstance(review, dict):
            raise ValueError("Each review must be an object")
        point = positive_int(review.get("checkpoint"), "review checkpoint", count)
        reviewed = timestamp(review.get("reviewed_at"))
        if point in done or reviewed < dates[point - 1] or reviewed > now:
            raise ValueError("Duplicate, early or future checkpoint review")
        done.add(point)
    due = [i for i, date in enumerate(dates, 1) if date <= now and i not in done]
    pending = [i for i in range(1, count + 1) if i not in done]
    next_point = max(due) if due else pending[0] if pending else None
    return {
        "state": "review_due" if due else "waiting" if pending else "decision_required",
        "review_policy": policy, "checkpoint_dates": [iso(date) for date in dates],
        "due_checkpoints": due,
        "recommended_checkpoint": max(due) if due else None,
        "next_review_at": None if next_point is None else iso(dates[next_point - 1]),
        "missed_earlier_checkpoints": due[:-1] if due else [],
        "deadline_at": iso(dates[-1]), "deadline_reached": now >= dates[-1],
        "notice": "Overdue checkpoints do not require duplicate reviews; never auto-close or unlock resources.",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", required=True)
    parser.add_argument("--record", help="Explicit experiment JSON path; never modified")
    parser.add_argument("--now", help="ISO-8601 time override for offline tests only")
    args = parser.parse_args()
    try:
        result = config(args.project)
        if args.record:
            now = timestamp(args.now) if args.now else datetime.now(timezone.utc)
            result["schedule"] = schedule(load_json(args.record), now)
            result["test_clock_override"] = args.now is not None
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except (OSError, ValueError, TypeError, OverflowError) as error:
        print(json.dumps({"error": str(error)}, ensure_ascii=False), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
