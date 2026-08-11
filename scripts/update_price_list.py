#!/usr/bin/env python3
"""Update price-list-data.js from the public Google Sheets workbook.

Existing products:
  Only stock, price and updateDate are updated for variants where
  type == "BOX" and condition == "✨ Shrink".

New products:
  Products found in PRICE_LIST but not in price-list-data.js are added
  automatically. Their variants are created from the rows registered in the
  sheet, and image is initialized as an empty string.

Existing images, item order, non-target variants and all other fields are
preserved.
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
from collections import Counter, OrderedDict
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
    return p.parse_args()


def download_xlsx() -> Path:
    request = urllib.request.Request(
        EXPORT_URL,
        headers={"User-Agent": "Mozilla/5.0 GitHub-Actions-Price-Updater/2.0"},
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


def read_sheet_products(xlsx_path: Path) -> "OrderedDict[tuple[str, str], dict[str, Any]]":
    """Read products in sheet order, including all registered variants."""
    wb = load_workbook(xlsx_path, data_only=True, read_only=False)
    if "Price-List" not in wb.sheetnames:
        raise RuntimeError("Worksheet 'Price-List' was not found")
    ws = wb["Price-List"]

    products: "OrderedDict[tuple[str, str], dict[str, Any]]" = OrderedDict()

    for category, cols in SECTIONS.items():
        current_key: tuple[str, str] | None = None
        for row_no in range(6, ws.max_row + 1):
            item_cell = ws.cell(row_no, cols["item"]).value
            if item_cell not in (None, ""):
                item = str(item_cell).strip()
                current_key = (category, item)
                products.setdefault(current_key, {"variants": [], "target_rows": []})

            if current_key is None:
                continue

            row_type = str(ws.cell(row_no, cols["type"]).value or "").strip()
            condition = str(ws.cell(row_no, cols["condition"]).value or "").strip()
            if not row_type or not condition:
                continue

            variant = {
                "type": row_type,
                "condition": condition,
                "stock": normalize_value(ws.cell(row_no, cols["stock"]).value),
                "price": normalize_value(ws.cell(row_no, cols["price"]).value),
                "updateDate": normalize_date(ws.cell(row_no, cols["date"]).value),
            }
            products[current_key]["variants"].append(variant)

            if row_type == TARGET_TYPE and condition == TARGET_CONDITION:
                products[current_key]["target_rows"].append({
                    "stock": variant["stock"],
                    "price": variant["price"],
                    "updateDate": variant["updateDate"],
                    "excelRow": row_no,
                })

    # Drop accidental product headings that contain no actual variant rows.
    return OrderedDict((k, v) for k, v in products.items() if v["variants"])


def insert_new_group(groups: list[dict[str, Any]], group: dict[str, Any]) -> None:
    """Insert a new product at the end of its category block."""
    category = group["category"]
    last_category_index = -1
    for i, existing in enumerate(groups):
        if existing.get("category") == category:
            last_category_index = i
    if last_category_index >= 0:
        groups.insert(last_category_index + 1, group)
    else:
        groups.append(group)


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
    sheet_products = read_sheet_products(xlsx_path)

    existing_keys = {
        (str(g.get("category", "")), str(g.get("item", ""))) for g in groups
    }
    new_keys = [key for key in sheet_products if key not in existing_keys]

    # Add newly registered products first. Existing product ordering is preserved;
    # each new product is appended to the end of its category block.
    added_count = 0
    for key in new_keys:
        category, item = key
        info = sheet_products[key]
        new_group = {
            "category": category,
            "item": item,
            "image": "",
            "variants": copy.deepcopy(info["variants"]),
        }
        insert_new_group(groups, new_group)
        added_count += 1

    matched_items: set[tuple[str, str]] = set()
    missing_from_sheet: list[tuple[str, str]] = []
    update_count = 0
    report_rows: list[dict[str, Any]] = []

    # Update existing products only. Newly added products already contain the
    # complete sheet variant data and should not be counted as existing updates.
    original_keys = {
        (str(g.get("category", "")), str(g.get("item", ""))) for g in before
    }

    for group in groups:
        key = (str(group.get("category", "")), str(group.get("item", "")))
        info = sheet_products.get(key)

        if key in new_keys:
            report_rows.append({
                "category": key[0],
                "item": key[1],
                "status": "new_added",
                "details": json.dumps({"variants": len(group.get("variants", []))}, ensure_ascii=False),
            })
            continue

        targets = [
            variant
            for variant in group.get("variants", [])
            if variant.get("type") == TARGET_TYPE
            and variant.get("condition") == TARGET_CONDITION
        ]
        if not targets:
            continue

        source_rows = info["target_rows"] if info else []
        if not source_rows:
            missing_from_sheet.append(key)
            report_rows.append({
                "category": key[0], "item": key[1], "status": "missing_in_sheet", "details": ""
            })
            continue

        matched_items.add(key)
        for index, variant in enumerate(targets):
            src = source_rows[min(index, len(source_rows) - 1)]
            old = {field: variant.get(field) for field in ("stock", "price", "updateDate")}
            for field in ("stock", "price", "updateDate"):
                variant[field] = src[field]
            new = {field: variant.get(field) for field in ("stock", "price", "updateDate")}
            update_count += 1
            report_rows.append({
                "category": key[0],
                "item": key[1],
                "status": "updated" if old != new else "unchanged",
                "details": json.dumps({"old": old, "new": new}, ensure_ascii=False),
            })

    # Verify target fields for every product against the workbook.
    mismatches: list[str] = []
    for group in groups:
        key = (str(group.get("category", "")), str(group.get("item", "")))
        info = sheet_products.get(key)
        if not info:
            continue
        source_rows = info["target_rows"]
        targets = [
            variant
            for variant in group.get("variants", [])
            if variant.get("type") == TARGET_TYPE
            and variant.get("condition") == TARGET_CONDITION
        ]
        for index, variant in enumerate(targets):
            if not source_rows:
                continue
            src = source_rows[min(index, len(source_rows) - 1)]
            for field in ("stock", "price", "updateDate"):
                if variant.get(field) != src[field]:
                    mismatches.append(f"{key} variant={index} field={field}")

    # Verify newly added products exactly match all registered sheet variants.
    new_variant_mismatches: list[str] = []
    group_map = {
        (str(g.get("category", "")), str(g.get("item", ""))): g for g in groups
    }
    for key in new_keys:
        group = group_map[key]
        expected = sheet_products[key]["variants"]
        if group.get("image") != "":
            new_variant_mismatches.append(f"new image is not empty: {key}")
        if group.get("variants") != expected:
            new_variant_mismatches.append(f"new variants differ from sheet: {key}")

    # Verify existing images, product structure and non-target variants did not change.
    protected_changes: list[str] = []
    current_map = {
        (str(g.get("category", "")), str(g.get("item", ""))): g for g in groups
    }
    for old_group in before:
        key = (str(old_group.get("category", "")), str(old_group.get("item", "")))
        new_group = current_map.get(key)
        if not new_group:
            protected_changes.append(f"existing product removed: {key}")
            continue
        if old_group.get("image") != new_group.get("image"):
            protected_changes.append(f"image changed: {key}")
        if len(old_group.get("variants", [])) != len(new_group.get("variants", [])):
            protected_changes.append(f"variant count changed: {key}")
            continue
        for old_variant, new_variant in zip(old_group.get("variants", []), new_group.get("variants", [])):
            target = (
                new_variant.get("type") == TARGET_TYPE
                and new_variant.get("condition") == TARGET_CONDITION
            )
            if target:
                old_copy = copy.deepcopy(old_variant)
                for field in ("stock", "price", "updateDate"):
                    old_copy[field] = new_variant.get(field)
                if old_copy != new_variant:
                    protected_changes.append(f"protected target field changed: {key}")
            elif old_variant != new_variant:
                protected_changes.append(f"non-target variant changed: {key}")

    duplicate_items = [
        key
        for key, count in Counter(
            (str(g.get("category", "")), str(g.get("item", ""))) for g in groups
        ).items()
        if count > 1
    ]

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
    if new_variant_mismatches:
        errors.append(f"{len(new_variant_mismatches)} new-product mismatches")
    if protected_changes:
        errors.append(f"{len(protected_changes)} protected-field changes")
    if duplicate_items:
        errors.append(f"{len(duplicate_items)} duplicate items")

    print(f"Workbook: {xlsx_path}")
    print(f"Existing matched products: {len(matched_items)}")
    print(f"Existing target variants checked: {update_count}")
    print(f"New products added: {added_count}")
    for key in new_keys:
        print(f"  ADDED: {key[0]} / {key[1]}")
    print(f"Existing items missing from sheet: {len(missing_from_sheet)}")
    print(f"Mismatches: {len(mismatches)}")
    print(f"New-product mismatches: {len(new_variant_mismatches)}")
    print(f"Protected changes: {len(protected_changes)}")
    print(f"Report: {report_path}")

    if errors:
        print("Validation failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    write_js(js_path, groups)
    print(f"Updated: {js_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
