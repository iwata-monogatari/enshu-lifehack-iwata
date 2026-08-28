#!/usr/bin/env python3
"""Add and validate canonical URLs for every deployable HTML page."""

from __future__ import annotations

import argparse
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ORIGIN = "https://iwata.enshu-lifehack.com"
EXCLUDED_PARTS = {".git", "_audit", "_staging", "docs", "parts", "reports"}
CANONICAL_RE = re.compile(
    r'<link\s+rel=["\']canonical["\']\s+href=["\'][^"\']+["\']\s*/?>',
    re.IGNORECASE,
)


def is_deployable(path: Path) -> bool:
    relative = path.relative_to(ROOT)
    if relative.name == "404.html" or "_template" in relative.parts:
        return False
    return not any(part in EXCLUDED_PARTS for part in relative.parts)


def canonical_for(path: Path) -> str:
    relative = path.relative_to(ROOT).as_posix()
    if relative == "index.html":
        return f"{ORIGIN}/"
    if relative.endswith("/index.html"):
        relative = relative[: -len("index.html")]
    return f"{ORIGIN}/{relative}"


def update(path: Path, *, check: bool) -> bool:
    text = path.read_text(encoding="utf-8")
    expected = f'<link rel="canonical" href="{canonical_for(path)}">'
    matches = CANONICAL_RE.findall(text)
    if matches == [expected]:
        return False

    if matches:
        updated = CANONICAL_RE.sub(expected, text, count=1)
        updated = CANONICAL_RE.sub("", updated)
    else:
        marker = '<meta name="viewport"'
        position = text.find(marker)
        if position < 0:
            raise ValueError(f"viewport meta not found: {path.relative_to(ROOT)}")
        end = text.find(">", position)
        if end < 0:
            raise ValueError(f"invalid head markup: {path.relative_to(ROOT)}")
        updated = text[: end + 1] + expected + text[end + 1 :]

    if not check:
        path.write_text(updated, encoding="utf-8", newline="")
    return True


def ensure_404_noindex(*, check: bool) -> bool:
    path = ROOT / "404.html"
    text = path.read_text(encoding="utf-8")
    expected = '<meta name="robots" content="noindex,follow">'
    if expected in text:
        return False
    marker = '<meta name="viewport"'
    position = text.find(marker)
    end = text.find(">", position)
    if position < 0 or end < 0:
        raise ValueError("invalid 404 head markup")
    if not check:
        path.write_text(text[: end + 1] + expected + text[end + 1 :], encoding="utf-8", newline="")
    return True


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    pages = sorted(path for path in ROOT.rglob("*.html") if is_deployable(path))
    changed = [path for path in pages if update(path, check=args.check)]
    noindex_changed = ensure_404_noindex(check=args.check)
    if changed or noindex_changed:
        action = "need canonical updates" if args.check else "updated"
        print(f"{len(changed)} pages {action}; 404 noindex changed={noindex_changed}")
        return 1 if args.check else 0
    print(f"canonical OK: {len(pages)} deployable pages")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
