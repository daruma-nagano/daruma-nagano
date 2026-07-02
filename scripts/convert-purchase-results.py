from pathlib import Path
import csv
import json
import re
import sys
from collections import defaultdict

# 実行場所に依存しないように、スクリプト位置からリポジトリ直下を判定します。
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
OUTPUT = REPO_ROOT / "assets" / "data" / "purchase-results.json"


def resolve_source() -> Path:
    """CSVの置き場所を柔軟に判定する。

    対応パターン:
    1. python scripts/convert-purchase-results.py path/to/file.csv
    2. リポジトリ直下 / 店頭買取ケース.csv
    3. scripts / 店頭買取ケース.csv
    4. リポジトリ直下または scripts にある 店頭買取ケース*.csv
    """
    candidates = []

    if len(sys.argv) >= 2:
        arg = Path(sys.argv[1])
        candidates.append(arg if arg.is_absolute() else (Path.cwd() / arg))

    candidates.extend([
        REPO_ROOT / "店頭買取ケース.csv",
        SCRIPT_DIR / "店頭買取ケース.csv",
    ])

    candidates.extend(sorted(REPO_ROOT.glob("店頭買取ケース*.csv")))
    candidates.extend(sorted(SCRIPT_DIR.glob("店頭買取ケース*.csv")))

    for candidate in candidates:
        if candidate.exists() and candidate.is_file():
            return candidate

    checked = "\n".join("- " + str(p) for p in candidates[:10])
    raise SystemExit(
        "買取実績CSVが見つかりません。次のいずれかで実行してください。\n"
        "1) scripts フォルダに 店頭買取ケース.csv を置いて実行\n"
        "2) リポジトリ直下に 店頭買取ケース.csv を置いて実行\n"
        "3) python scripts/convert-purchase-results.py scripts/店頭買取ケース.csv のようにCSVパスを指定\n\n"
        "確認した場所:\n" + checked
    )


def clean(value) -> str:
    if value is None:
        return ""
    return str(value).strip()


def category_label(cat) -> str:
    return clean(cat).replace(";", " / ") or "その他"


def item_title(cat: str, name: str, brand: str = "", manufacturer: str = "") -> str:
    s = " ".join([clean(cat), clean(name), clean(brand), clean(manufacturer)])
    if "ワンピース" in s or "ONE PIECE" in s.upper():
        return "ワンピースカード"
    if "ポケモン" in s or "POKEMON" in s.upper() or "POKÉMON" in s.upper():
        return "ポケモンカード"
    if "遊戯王" in s or "YU-GI-OH" in s.upper():
        return "遊戯王OCG"
    return "その他"


def item_type(cat: str, name: str) -> str:
    # 商品カテゴリを優先。鑑定品カテゴリに入っている商品は、商品名にBOX等が含まれても鑑定品として扱います。
    c = clean(cat)
    n = clean(name)
    s = f"{c} {n}"
    if "鑑定品" in c or re.search(r"\b(PSA|BGS|ARS|CGC)\b", s, re.I):
        return "PSA・鑑定品"
    if "ボックス" in c or "BOX" in c.upper() or "ボックス" in n or re.search(r"\bBOX\b", n, re.I):
        return "BOX"
    if "シングルカード" in c:
        return "シングルカード"
    if "パック" in c:
        return "パック"
    return "その他"


def read_rows(source: Path) -> list[dict]:
    # 元CSVはタブ区切り。UTF-8 BOMつきにも対応。
    text = source.read_text(encoding="utf-8-sig", errors="replace")
    sample = text[:4096]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters="\t,")
    except csv.Error:
        dialect = csv.excel_tab

    reader = csv.DictReader(text.splitlines(), dialect=dialect)
    return list(reader)


def is_public_product(name: str) -> bool:
    # サービス行・テスト行に見えるものは公開用実績から除外します。
    if not name or name == "教育データ":
        return False
    if "買取金額UP" in name:
        return False
    if "ストレージ販売" in name:
        return False
    if name.endswith("保証") or name in {"まとめ買い"}:
        return False
    return True


def main() -> None:
    source = resolve_source()
    rows = read_rows(source)

    required = ["ステータス名", "商品名", "商品完全カテゴリ名"]
    missing = [name for name in required if rows and name not in rows[0]]
    if missing:
        raise SystemExit("CSVの列名が想定と異なります。不足列: " + ", ".join(missing))

    # 同一商品は1商品としてまとめます。ただし件数・数量は公開用JSONには含めません。
    grouped: dict[tuple[str, str, str, str, str, str, str], int] = defaultdict(int)
    for row in rows:
        if clean(row.get("ステータス名")) != "買取完了":
            continue
        name = clean(row.get("商品名"))
        if not is_public_product(name):
            continue

        key = (
            name,
            clean(row.get("商品完全カテゴリ名")),
            clean(row.get("エキスパンション名(商品属性.custom_expansion)")),
            clean(row.get("レアリティ(商品属性.custom_rarity)")),
            clean(row.get("シリーズ(商品属性.custom_series)")),
            clean(row.get("ブランド(商品属性.brand)")),
            clean(row.get("メーカー(商品属性.manufacturer)")),
        )
        grouped[key] += 1

    private_rows = []
    for key, count in grouped.items():
        name, cat, expansion, rarity, series, brand, manufacturer = key
        private_rows.append({
            "privateCount": count,
            "name": name[:160],
            "category": category_label(cat),
            "title": item_title(cat, name, brand, manufacturer),
            "type": item_type(cat, name),
            "series": series[:80],
            "expansion": expansion[:80],
            "rarity": rarity[:80],
        })

    # 表示順だけ件数を参考にします。件数・数量は公開しません。
    # BOX、PSA・鑑定品、シングルカードに割り振れる実績のみ公開します。
    allowed_types = {"BOX", "PSA・鑑定品", "シングルカード"}
    private_rows = [row for row in private_rows if row["type"] in allowed_types]

    type_order = {"BOX": 0, "PSA・鑑定品": 1, "シングルカード": 2}
    private_rows.sort(key=lambda x: (-x["privateCount"], type_order.get(x["type"], 9), x["title"], x["name"]))

    items = []
    for index, row in enumerate(private_rows, start=1):
        items.append({
            "id": f"R{index:04d}",
            "name": row["name"],
            "category": row["category"],
            "title": row["title"],
            "type": row["type"],
            "series": row["series"],
            "expansion": row["expansion"],
            "rarity": row["rarity"],
        })

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps({
            "sourceFile": source.name,
            "note": "公開用データです。BOX、PSA・鑑定品、シングルカードに割り振れる実績のみを掲載します。買取価格、数量、件数、原価、粗利率、スタッフ名、ID類、鑑定品シリアルは含めていません。",
            "items": items,
        }, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"source: {source}")
    print(f"wrote : {OUTPUT}")
    print(f"items : {len(items)}")
    print("注意: 原本CSVは公開リポジトリに残さないでください。JSON生成後は削除推奨です。")
    print("公開用JSONには買取価格・数量・件数・内部ID・スタッフ名等を含めていません。")
    print("割り振り先のないデータ（パック、その他など）は公開用JSONから除外します。")


if __name__ == "__main__":
    main()
