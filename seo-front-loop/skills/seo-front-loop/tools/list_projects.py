#!/usr/bin/env python3
"""List immediate project configs without reading keywords, memory or credentials."""
import argparse
import json
from pathlib import Path


def discover(root):
    folder = Path(root).resolve(strict=True) / "projects"
    if not folder.is_dir():
        return []
    return [{"name": p.name, "project": str(p.resolve())} for p in sorted(folder.iterdir())
            if p.is_dir() and not p.is_symlink() and (p / "config").is_file()]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, help="SEO management collection directory")
    args = parser.parse_args()
    print(json.dumps({"projects": discover(args.root), "note": "请用户确认项目；不自动选择、不读取各项目内容。"}, ensure_ascii=False, indent=2))
