#!/usr/bin/env python3
"""Verify the published GitHub Pages price-list data matches the repository data.

The workflow calls this after git push. GitHub Pages deployment can lag behind the
push, so the verifier retries for a bounded period. It compares parsed JSON data,
not raw formatting, and therefore detects stale or partial publication.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.request
from pathlib import Path
from typing import Any

DEFAULT_URL = "https://daruma-nagano.github.io/daruma-nagano/en/price-list/price-list-data.js"


def parse_groups(text: str, source: str) -> list[dict[str, Any]]:
    match = re.fullmatch(
        r"\s*window\.DARUMA_PRICE_GROUPS\s*=\s*(\[.*\])\s*;\s*",
        text,
        flags=re.S,
    )
    if not match:
        raise RuntimeError(f"Could not parse price-list data from {source}")
    return json.loads(match.group(1))


def load_local(path: Path) -> list[dict[str, Any]]:
    return parse_groups(path.read_text(encoding="utf-8"), str(path))


def fetch_remote(url: str, timeout: int) -> list[dict[str, Any]]:
    cache_buster = int(time.time() * 1000)
    separator = "&" if "?" in url else "?"
    request = urllib.request.Request(
        f"{url}{separator}verify={cache_buster}",
        headers={
            "User-Agent": "GitHub-Actions-Price-Publish-Verifier/1.0",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        data = response.read().decode("utf-8")
    return parse_groups(data, url)


def summarize_difference(expected: list[dict[str, Any]], actual: list[dict[str, Any]]) -> str:
    expected_map = {
        (str(g.get("category", "")), str(g.get("item", ""))): g for g in expected
    }
    actual_map = {
        (str(g.get("category", "")), str(g.get("item", ""))): g for g in actual
    }
    missing = [key for key in expected_map if key not in actual_map]
    extra = [key for key in actual_map if key not in expected_map]
    changed = [key for key in expected_map if key in actual_map and expected_map[key] != actual_map[key]]
    return (
        f"missing={len(missing)} extra={len(extra)} changed={len(changed)} "
        f"sample_missing={missing[:3]} sample_extra={extra[:3]} sample_changed={changed[:3]}"
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--local", default="en/price-list/price-list-data.js")
    parser.add_argument("--url", default=DEFAULT_URL)
    parser.add_argument("--attempts", type=int, default=12)
    parser.add_argument("--interval", type=int, default=15)
    parser.add_argument("--timeout", type=int, default=20)
    args = parser.parse_args()

    expected = load_local(Path(args.local))
    last_error = ""

    for attempt in range(1, args.attempts + 1):
        try:
            actual = fetch_remote(args.url, args.timeout)
            if actual == expected:
                print(
                    f"Published price list verified successfully on attempt {attempt}: "
                    f"groups={len(actual)} url={args.url}"
                )
                return 0
            last_error = summarize_difference(expected, actual)
            print(
                f"Published data is not current yet. attempt={attempt}/{args.attempts} {last_error}",
                file=sys.stderr,
            )
        except Exception as exc:
            last_error = str(exc)
            print(
                f"Published verification request failed. attempt={attempt}/{args.attempts} error={exc}",
                file=sys.stderr,
            )

        if attempt < args.attempts:
            time.sleep(args.interval)

    print(f"Published price-list verification failed: {last_error}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
