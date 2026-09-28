# -*- coding: utf-8 -*-
"""update_price_list.py の単体テスト。

Google スプレッドシートにもネットワークにも触らない純粋関数だけを対象にする。

実行:
    python -m unittest discover -s scripts -p "test_*.py" -v
"""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import update_price_list as upl  # noqa: E402


def group(category: str, item: str, image: str = "", updated: str = "2026-09-23") -> dict:
    return {
        "category": category,
        "item": item,
        "image": image,
        "variants": [
            {"type": "BOX", "condition": "✨ Shrink", "stock": 1, "price": 1000, "updateDate": updated},
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


class LoadReleaseMapTest(unittest.TestCase):
    """発売日対応表の読み込み（2026-09-28 追加）。"""

    def _write(self, text: str) -> Path:
        path = Path(self.tmp.name) / "release-dates.json"
        path.write_text(text, encoding="utf-8")
        return path

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def test_ファイルが無ければ空で返す(self):
        # 対応表を置き忘れても更新を止めない
        missing = Path(self.tmp.name) / "no-such-file.json"
        self.assertEqual(upl.load_release_map(missing), {})

    def test_itemsとmanualItemsを両方読む(self):
        path = self._write(json.dumps({
            "items": {"Pokémon\tBattle Partners": "2025-01-24"},
            "manualItems": {"Pokémon\tStart Deck 100": "2021-12-17"},
        }, ensure_ascii=False))
        self.assertEqual(upl.load_release_map(path), {
            ("Pokémon", "Battle Partners"): "2025-01-24",
            ("Pokémon", "Start Deck 100"): "2021-12-17",
        })

    def test_手入力がマスタ由来を上書きする(self):
        path = self._write(json.dumps({
            "items": {"Pokémon\tA": "2020-01-01"},
            "manualItems": {"Pokémon\tA": "2019-12-31"},
        }, ensure_ascii=False))
        self.assertEqual(upl.load_release_map(path), {("Pokémon", "A"): "2019-12-31"})

    def test_壊れた行は黙って捨てる(self):
        # タブ区切りでないキー・空の日付・型違いは無視する
        path = self._write(json.dumps({
            "items": {"タブなし": "2020-01-01", "Pokémon\tA": "", "Pokémon\tB": 20200101,
                      "Pokémon\tC": "2020-01-01"},
        }, ensure_ascii=False))
        self.assertEqual(upl.load_release_map(path), {("Pokémon", "C"): "2020-01-01"})


class ApplyReleaseDatesTest(unittest.TestCase):
    """発売日の付与（2026-09-28 追加）。"""

    def test_一致した商品にだけ付与する(self):
        groups = [group("Pokémon", "Battle Partners"), group("Pokémon", "対応表に無い商品")]
        changed, mapped = upl.apply_release_dates(
            groups, {("Pokémon", "Battle Partners"): "2025-01-24"}, {})
        self.assertEqual((changed, mapped), (1, 1))
        self.assertEqual(groups[0]["releaseDate"], "2025-01-24")
        self.assertNotIn("releaseDate", groups[1])

    def test_日本語表記と英語表記が入れ替わっても一致する(self):
        # サイト側の商品名は日英で入れ替わることがあるため別名解決を通す
        groups = [group("Pokémon", "バトルパートナーズ")]
        name_map = {upl.normalize_name("バトルパートナーズ"): "Battle Partners"}
        changed, mapped = upl.apply_release_dates(
            groups, {("Pokémon", "Battle Partners"): "2025-01-24"}, name_map)
        self.assertEqual((changed, mapped), (1, 1))
        self.assertEqual(groups[0]["releaseDate"], "2025-01-24")

    def test_カテゴリが違えば付与しない(self):
        groups = [group("One Piece", "Battle Partners")]
        changed, mapped = upl.apply_release_dates(
            groups, {("Pokémon", "Battle Partners"): "2025-01-24"}, {})
        self.assertEqual((changed, mapped), (0, 0))
        self.assertNotIn("releaseDate", groups[0])

    def test_同じ発売日なら書き換え件数に数えない(self):
        groups = [group("Pokémon", "A")]
        groups[0]["releaseDate"] = "2025-01-24"
        changed, mapped = upl.apply_release_dates(
            groups, {("Pokémon", "A"): "2025-01-24"}, {})
        self.assertEqual((changed, mapped), (0, 1))

    def test_対応表が空なら何もしない(self):
        groups = [group("Pokémon", "A")]
        self.assertEqual(upl.apply_release_dates(groups, {}, {}), (0, 0))
        self.assertNotIn("releaseDate", groups[0])


class SortGroupsByReleaseDateTest(unittest.TestCase):
    """発売日順の並べ替え（2026-09-28 追加）。"""

    def test_発売日の新しい順に並ぶ(self):
        groups = [group("Pokémon", "古"), group("Pokémon", "新"), group("Pokémon", "中")]
        for g, d in zip(groups, ("2020-01-01", "2026-01-01", "2023-01-01")):
            g["releaseDate"] = d
        upl.sort_groups_by_release_date(groups)
        self.assertEqual([g["item"] for g in groups], ["新", "中", "古"])

    def test_発売日が無い商品は末尾に回る(self):
        groups = [group("Pokémon", "不明"), group("Pokémon", "既知")]
        groups[1]["releaseDate"] = "2020-01-01"
        upl.sort_groups_by_release_date(groups)
        self.assertEqual([g["item"] for g in groups], ["既知", "不明"])

    def test_発売日が無い商品同士は更新日の新しい順(self):
        groups = [group("Pokémon", "古更新", updated="2026-09-01"),
                  group("Pokémon", "新更新", updated="2026-09-27")]
        upl.sort_groups_by_release_date(groups)
        self.assertEqual([g["item"] for g in groups], ["新更新", "古更新"])

    def test_対応表が無いときは従来の更新日順と同じ(self):
        # releaseDate が付いていない状態では既存の並び順を壊さない
        items = [("A", "2026-09-10"), ("B", "2026-09-27"), ("C", "2026-09-01")]
        a = [group("Pokémon", i, updated=d) for i, d in items]
        b = [group("Pokémon", i, updated=d) for i, d in items]
        upl.sort_groups_by_release_date(a)
        upl.sort_groups_by_target_update_date(b)
        self.assertEqual([g["item"] for g in a], [g["item"] for g in b])

    def test_年月までの発売日も扱える(self):
        # 公表が「2025年9月」までの商品は YYYY-MM で持つ
        groups = [group("One Piece", "月まで"), group("One Piece", "日まで")]
        groups[0]["releaseDate"] = "2025-09"
        groups[1]["releaseDate"] = "2025-10-01"
        upl.sort_groups_by_release_date(groups)
        self.assertEqual([g["item"] for g in groups], ["日まで", "月まで"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
