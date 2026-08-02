#!/usr/bin/env python3
"""Update price-list-data.js from the public Google Sheets workbook.

Only updates stock, price and updateDate for variants where:
  type == "BOX" and condition == "✨ Shrink"

Images, item order, variants and all other fields are preserved.
"""
from __future__ import annotations

import argparse
import copy
import csv
import json
import re
import sys
import tempfile
import urllib.request
from collections import Counter, defaultdict
from datetime import date, datetime
from pathlib import Path
from typing import Any

from openpyxl import load_workbook

SHEET_ID = "1IXVH9SGgtwnFd3ni_Rg-scFaNEk7xQJMnvvj7Mdc4rQ"
EXPORT_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=xlsx"
TARGET_TYPE = "BOX"
TARGET_CONDITION = "✨ Shrink"

SECTIONS = {
    "Pokémon": {"item": 2, "type": 4, "condition": 5, "stock": 6, "price": 7, "date": 8},
    "One Piece": {"item": 10, "type": 12, "condition": 13, "stock": 14, "price": 15, "date": 16},
}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--js", default="en/price-list/price-list-data.js")
    p.add_argument("--xlsx", help="Use a local workbook instead of downloading the public sheet")
    p.add_argument("--report", default="price-list-update-report.csv")
    p.add_argument("--allow-new-items", action="store_true", help="Report new items but do not fail")
    return p.parse_args()


def download_xlsx() -> Path:
    request = urllib.request.Request(
        EXPORT_URL,
        headers={"User-Agent": "Mozilla/5.0 GitHub-Actions-Price-Updater/1.0"},
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            content_type = response.headers.get("Content-Type", "")
            data = response.read()
    except Exception as exc:
        raise RuntimeError(f"Google Sheet download failed: {exc}") from exc

    if len(data) < 1000 or data[:2] != b"PK":
        raise RuntimeError(
            f"Downloaded content is not an XLSX file: content-type={content_type!r}, bytes={len(data)}"
        )

    tmp = tempfile.NamedTemporaryFile(prefix="price-list-", suffix=".xlsx", delete=False)
    tmp.write(data)
    tmp.close()
    return Path(tmp.name)


def load_js(path: Path) -> list[dict[str, Any]]:
    text = path.read_text(encoding="utf-8")
    match = re.fullmatch(
        r"\s*window\.DARUMA_PRICE_GROUPS\s*=\s*(\[.*\])\s*;\s*",
        text,
        flags=re.S,
    )
    if not match:
        raise RuntimeError(f"Could not parse JavaScript data: {path}")
    return json.loads(match.group(1))


def normalize_value(value: Any) -> Any:
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return value


def normalize_date(value: Any) -> str:
    if value in (None, ""):
        return ""
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    text = str(value).strip()
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%m/%d/%Y"):
        try:
            return datetime.strptime(text, fmt).date().isoformat()
        except ValueError:
            pass
    raise RuntimeError(f"Unsupported update date value: {value!r}")


def read_source_rows(xlsx_path: Path) -> dict[tuple[str, str], list[dict[str, Any]]]:
    wb = load_workbook(xlsx_path, data_only=True, read_only=False)
    if "Price-List" not in wb.sheetnames:
        raise RuntimeError("Worksheet 'Price-List' was not found")
    ws = wb["Price-List"]

    source: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for category, cols in SECTIONS.items():
        current_item = ""
        for row_no in range(6, ws.max_row + 1):
            item_cell = ws.cell(row_no, cols["item"]).value
            if item_cell not in (None, ""):
                current_item = str(item_cell).strip()
            if not current_item:
                continue

            row_type = str(ws.cell(row_no, cols["type"]).value or "").strip()
            condition = str(ws.cell(row_no, cols["condition"]).value or "").strip()
            if row_type != TARGET_TYPE or condition != TARGET_CONDITION:
                continue

            source[(category, current_item)].append(
                {
                    "stock": normalize_value(ws.cell(row_no, cols["stock"]).value),
                    "price": normalize_value(ws.cell(row_no, cols["price"]).value),
                    "updateDate": normalize_date(ws.cell(row_no, cols["date"]).value),
                    "excelRow": row_no,
                }
            )
    return source


def write_js(path: Path, groups: list[dict[str, Any]]) -> None:
    path.write_text(
        "window.DARUMA_PRICE_GROUPS = "
        + json.dumps(groups, ensure_ascii=False, indent=2)
        + ";\n",
        encoding="utf-8",
    )


def main() -> int:
    args = parse_args()
    js_path = Path(args.js)
    report_path = Path(args.report)
    xlsx_path = Path(args.xlsx) if args.xlsx else download_xlsx()

    groups = load_js(js_path)
    before = copy.deepcopy(groups)
    source = read_source_rows(xlsx_path)
    source_only = set(source)
    missing_from_sheet: list[tuple[str, str]] = []
    matched_items: set[tuple[str, str]] = set()
    update_count = 0
    report_rows: list[dict[str, Any]] = []

    for group in groups:
        key = (str(group.get("category", "")), str(group.get("item", "")))
        targets = [
            variant
            for variant in group.get("variants", [])
            if variant.get("type") == TARGET_TYPE
            and variant.get("condition") == TARGET_CONDITION
        ]
        if not targets:
            continue

        source_rows = source.get(key, [])
        if not source_rows:
            missing_from_sheet.append(key)
            report_rows.append(
                {"category": key[0], "item": key[1], "status": "missing_in_sheet", "details": ""}
            )
            continue

        matched_items.add(key)
        source_only.discard(key)
        for index, variant in enumerate(targets):
            src = source_rows[min(index, len(source_rows) - 1)]
            old = {field: variant.get(field) for field in ("stock", "price", "updateDate")}
            for field in ("stock", "price", "updateDate"):
                variant[field] = src[field]
            new = {field: variant.get(field) for field in ("stock", "price", "updateDate")}
            update_count += 1
            report_rows.append(
                {
                    "category": key[0],
                    "item": key[1],
                    "status": "updated" if old != new else "unchanged",
                    "details": json.dumps({"old": old, "new": new}, ensure_ascii=False),
                }
            )

    # Verify every mapped field against the workbook.
    mismatches: list[str] = []
    for group in groups:
        key = (str(group.get("category", "")), str(group.get("item", "")))
        source_rows = source.get(key, [])
        if not source_rows:
            continue
        targets = [
            variant
            for variant in group.get("variants", [])
            if variant.get("type") == TARGET_TYPE
            and variant.get("condition") == TARGET_CONDITION
        ]
        for index, variant in enumerate(targets):
            src = source_rows[min(index, len(source_rows) - 1)]
            for field in ("stock", "price", "updateDate"):
                if variant.get(field) != src[field]:
                    mismatches.append(f"{key} variant={index} field={field}")

    # Verify that images, product structure and non-target variants did not change.
    protected_changes: list[str] = []
    for old_group, new_group in zip(before, groups):
        if old_group.get("category") != new_group.get("category"):
            protected_changes.append(f"category changed: {old_group.get('item')}")
        if old_group.get("item") != new_group.get("item"):
            protected_changes.append(f"item changed: {old_group.get('item')}")
        if old_group.get("image") != new_group.get("image"):
            protected_changes.append(f"image changed: {old_group.get('item')}")
        if len(old_group.get("variants", [])) != len(new_group.get("variants", [])):
            protected_changes.append(f"variant count changed: {old_group.get('item')}")
        for old_variant, new_variant in zip(old_group.get("variants", []), new_group.get("variants", [])):
            target = (
                new_variant.get("type") == TARGET_TYPE
                and new_variant.get("condition") == TARGET_CONDITION
            )
            if not target and old_variant != new_variant:
                protected_changes.append(f"non-target variant changed: {old_group.get('item')}")

    duplicate_items = [
        key
        for key, count in Counter(
            (str(g.get("category", "")), str(g.get("item", ""))) for g in groups
        ).items()
        if count > 1
    ]

    for key in sorted(source_only):
        report_rows.append(
            {"category": key[0], "item": key[1], "status": "new_in_sheet", "details": "not added"}
        )

    report_path.parent.mkdir(parents=True, exist_ok=True)
    with report_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=["category", "item", "status", "details"])
        writer.writeheader()
        writer.writerows(report_rows)

    errors: list[str] = []
    if missing_from_sheet:
        errors.append(f"{len(missing_from_sheet)} existing items are missing from the sheet")
    if mismatches:
        errors.append(f"{len(mismatches)} workbook mismatches")
    if protected_changes:
        errors.append(f"{len(protected_changes)} protected-field changes")
    if duplicate_items:
        errors.append(f"{len(duplicate_items)} duplicate items")
    if source_only and not args.allow_new_items:
        errors.append(f"{len(source_only)} new sheet items require manual review")

    print(f"Workbook: {xlsx_path}")
    print(f"Matched products: {len(matched_items)}")
    print(f"Target variants checked: {update_count}")
    print(f"New sheet items: {len(source_only)}")
    print(f"Existing items missing from sheet: {len(missing_from_sheet)}")
    print(f"Mismatches: {len(mismatches)}")
    print(f"Protected changes: {len(protected_changes)}")
    print(f"Report: {report_path}")

    if errors:
        print("Validation failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        if source_only:
            for key in sorted(source_only):
                print(f"  NEW: {key[0]} / {key[1]}", file=sys.stderr)
        return 1

    write_js(js_path, groups)
    print(f"Updated: {js_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
