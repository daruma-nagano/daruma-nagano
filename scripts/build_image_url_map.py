#!/usr/bin/env python3
"""Build data/image-url-map.json from shinsoku SQLite DB.

Only unambiguous category + English display-name mappings are exported.
If the same product name has multiple image URLs, it is listed under
"ambiguous" and is not applied automatically.
"""
from __future__ import annotations

import argparse
import json
import re
import sqlite3
from collections import defaultdict
from pathlib import Path


def normalize_category(value: object) -> str:
    text = str(value or "")
    if "ポケ" in text or "pokemon" in text.lower():
        return "Pokémon"
    if "ワン" in text or "one piece" in text.lower() or "onepiece" in text.lower():
        return "One Piece"
    return ""


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--db", default="data/shinsoku_shopify_sync.db")
    p.add_argument("--out", default="data/image-url-map.json")
    args = p.parse_args()

    db_path = Path(args.db)
    out_path = Path(args.out)
    if not db_path.exists():
        raise SystemExit(f"DB not found: {db_path}")

    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    try:
        tables = {
            r["name"] for r in con.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        table = "source_items_latest" if "source_items_latest" in tables else None
        if not table:
            raise RuntimeError("source_items_latest table was not found")
        rows = con.execute(f'SELECT raw_json FROM "{table}"').fetchall()
    finally:
        con.close()

    urls_by_key: dict[tuple[str, str], set[str]] = defaultdict(set)
    for row in rows:
        try:
            obj = json.loads(row["raw_json"])
        except Exception:
            continue
        category = normalize_category(obj.get("取得カテゴリ") or obj.get("brand"))
        item = str(obj.get("display_name_en") or obj.get("表示商品名") or "").strip()
        url = str(obj.get("img_url1") or "").strip()
        if category and item and url:
            urls_by_key[(category, item)].add(url)

    items: dict[str, str] = {}
    ambiguous: list[dict[str, object]] = []
    for (category, item), urls in sorted(urls_by_key.items()):
        if len(urls) == 1:
            items[f"{category}\t{item}"] = next(iter(urls))
        else:
            ambiguous.append({
                "category": category,
                "item": item,
                "urls": sorted(urls),
            })

    payload = {
        "source": f"{db_path.name} / {table}",
        "items": items,
        "ambiguous": ambiguous,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Image mappings: {len(items)}")
    print(f"Ambiguous products skipped: {len(ambiguous)}")
    print(f"Updated: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
