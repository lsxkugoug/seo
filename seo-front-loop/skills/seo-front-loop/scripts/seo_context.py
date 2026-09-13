#!/usr/bin/env python3
"""Read config/keywords and optionally calculate dates. Never parse or write memory."""
import argparse
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import unicodedata

DATA_DEFAULTS = {
    "SEO_GSC_PROPERTY": "",
    "SEO_GSC_AUTH_MODE": "access_token",
    "SEO_POSTHOG_HOST": "",
    "SEO_POSTHOG_PROJECT_ID": "",
    "SEO_POSTHOG_CONVERSION_EVENTS": "",
    "SEO_GSC_TOKEN_ENV": "",
    "SEO_POSTHOG_KEY_ENV": "",
    "SEO_GSC_CREDENTIALS_ENV": "",
}

DEFAULTS = {
    "SEO_REVIEW_INTERVAL_DAYS": "20",
    "SEO_REVIEW_MAX_CHECKS": "3",
    "SEO_KEYWORDS_FILE": "seo-keywords.json",
    "SEO_MEMORY_DIR": ".seo-memory",
    "SEO_REPOSITORY_URL": "",
    **DATA_DEFAULTS,
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


def project_root(project):
    root = Path(project).resolve(strict=True)
    if not root.is_dir():
        raise ValueError("project must be a directory")
    if (root / "projects").is_dir() and any((p / "config").is_file() for p in (root / "projects").iterdir() if p.is_dir()):
        raise ValueError("This is a project collection; ask the user and pass the selected projects/<name> directory")
    return root


def project_path(root, value):
    path = (root / value).resolve()
    if path == root or root not in path.parents:
        raise ValueError("Keywords, memory and evidence must stay inside the selected project directory")
    return path


def resolved_settings(project, environ=None):
    environ = os.environ if environ is None else environ
    project = project_root(project)
    local = read_config(project_path(project, "config"))
    values, sources = {}, {}
    for key, default in DEFAULTS.items():
        # Only scheduling overrides are portable across projects, never identity or paths.
        override = key in ("SEO_REVIEW_INTERVAL_DAYS", "SEO_REVIEW_MAX_CHECKS") and key in environ
        if key in environ and not override and environ[key] != local.get(key, default):
            raise ValueError(key + " environment override conflicts with selected project; configure this project's config instead")
        source = "process_environment" if override else "config" if key in local else "default"
        values[key] = environ[key] if override else local.get(key, default)
        sources[key] = source
        if (not values[key] and key != "SEO_REPOSITORY_URL" and key not in DATA_DEFAULTS) or "$" in values[key] or "`" in values[key] or "\n" in values[key]:
            raise ValueError(key + " is blank or contains unsupported interpolation")
    for key in ("SEO_GSC_TOKEN_ENV", "SEO_POSTHOG_KEY_ENV", "SEO_GSC_CREDENTIALS_ENV"):
        if values[key] and not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", values[key]):
            raise ValueError(key + " must name an environment variable, not contain a credential")
    return project, values, sources


def config(project, environ=None):
    project, values, sources = resolved_settings(project, environ)
    repository = values["SEO_REPOSITORY_URL"]
    if repository and not re.fullmatch(r"https://github\.com/[A-Za-z0-9_-]+/[A-Za-z0-9_.-]+/?", repository):
        raise ValueError("SEO_REPOSITORY_URL must be a credential-free https://github.com/OWNER/REPO URL")
    interval = positive_int(values["SEO_REVIEW_INTERVAL_DAYS"], "review interval", 365)
    checks = positive_int(values["SEO_REVIEW_MAX_CHECKS"], "max checks", 12)
    keyword_file = project_path(project, values["SEO_KEYWORDS_FILE"])
    memory_dir = project_path(project, values["SEO_MEMORY_DIR"])
    keywords = read_keywords(keyword_file)
    return {
        "project": str(project), "config_sources": sources,
        "repository_url": repository or None,
        "repository_access_verified": False,
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


def review_dates(live_verified_at, interval_days, max_checks):
    """Pure date arithmetic; inputs must be confirmed from the narrative record."""
    live = timestamp(live_verified_at)
    interval = positive_int(interval_days, "review interval", 365)
    count = positive_int(max_checks, "max checks", 12)
    return [iso(live + timedelta(days=interval * i)) for i in range(1, count + 1)]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", required=True)
    parser.add_argument("--live-verified-at", help="Confirmed ISO-8601 deployment time with timezone")
    parser.add_argument("--interval-days", help="Interval explicitly read from the original narrative")
    parser.add_argument("--max-checks", help="Check count explicitly read from the original narrative")
    args = parser.parse_args()
    try:
        result = config(args.project)
        date_args = (args.live_verified_at, args.interval_days, args.max_checks)
        if any(value is not None for value in date_args):
            if not all(value is not None for value in date_args):
                raise ValueError("Date calculation requires all three explicit inputs; never infer old policy from current config")
            result["calculated_review_dates"] = review_dates(*date_args)
            result["date_calculation_notice"] = "Dates only: agent must read Markdown for status, completed reviews, restrictions and decisions."
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except (OSError, ValueError, TypeError, OverflowError) as error:
        print(json.dumps({"error": str(error)}, ensure_ascii=False), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
