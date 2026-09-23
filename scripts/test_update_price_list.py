# -*- coding: utf-8 -*-
"""update_price_list.py の単体テスト。

Google スプレッドシートにもネットワークにも触らない純粋関数だけを対象にする。

実行:
    python -m unittest discover -s scripts -p "test_*.py" -v
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import update_price_list as upl  # noqa: E402


def group(category: str, item: str, image: str = "") -> dict:
    return {
        "category": category,
        "item": item,
        "image": image,
        "variants": [
            {"type": "BOX", "condition": "✨ Shrink", "stock": 1, "price": 1000, "updateDate": "2026-09-23"},
        ],
    }


class PruneMissingGroupsTest(unittest.TestCase):
    """シートから消えた商品の削除（2026-09-23 追加）。

    スプレッドシート側で重複ブロックや旧表記を整理すると、
    サイト側のJSにだけ残った商品が検証エラーで更新を止めてしまう。
    """

    def test_対象商品だけを取り除く(self):
        groups = [group("Pokémon", "Battle Partners"), group("Pokémon", "Journey Together")]
        kept, pruned = upl.prune_missing_groups(groups, [("Pokémon", "Journey Together")])
        self.assertEqual([g["item"] for g in kept], ["Battle Partners"])
        self.assertEqual(pruned, [("Pokémon", "Journey Together")])

    def test_対象が無ければ何も変えない(self):
        groups = [group("Pokémon", "A"), group("Pokémon", "B")]
        kept, pruned = upl.prune_missing_groups(groups, [])
        self.assertIs(kept, groups)
        self.assertEqual(pruned, [])

    def test_カテゴリが違えば消さない(self):
        # 同じ商品名でもカテゴリが違えば別商品として扱う
        groups = [group("Pokémon", "Shield"), group("One Piece", "Shield")]
        kept, pruned = upl.prune_missing_groups(groups, [("One Piece", "Shield")])
        self.assertEqual([(g["category"], g["item"]) for g in kept], [("Pokémon", "Shield")])
        self.assertEqual(pruned, [("One Piece", "Shield")])

    def test_バルク商品は指定しない限り残る(self):
        # バルクはBOX行を持たないため missing 判定の対象外。念のため固定する。
        groups = [group("Bulk", "RR Bulk"), group("Pokémon", "Journey Together")]
        kept, pruned = upl.prune_missing_groups(groups, [("Pokémon", "Journey Together")])
        self.assertEqual([g["item"] for g in kept], ["RR Bulk"])

    def test_残る商品の順序と中身を変えない(self):
        groups = [group("Pokémon", "A", "a.webp"), group("Pokémon", "X"), group("Pokémon", "B", "b.webp")]
        kept, _ = upl.prune_missing_groups(groups, [("Pokémon", "X")])
        self.assertEqual([(g["item"], g["image"]) for g in kept], [("A", "a.webp"), ("B", "b.webp")])

    def test_存在しないキーを指定しても落ちない(self):
        groups = [group("Pokémon", "A")]
        kept, pruned = upl.prune_missing_groups(groups, [("Pokémon", "存在しない商品")])
        self.assertEqual([g["item"] for g in kept], ["A"])
        self.assertEqual(pruned, [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
