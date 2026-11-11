"""Report duplicate and cross-book formula relationships without deleting entries."""
from __future__ import annotations

from collections import defaultdict
import json
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"

NAME_REPLACEMENTS = str.maketrans(
    {
        "圓": "丸",
        "朮": "术",
        "黃": "黄",
        "陳": "陈",
        "梔": "栀",
        "蘗": "柏",
        "轺": "翘",
    }
)


def read_json(name: str):
    return json.loads((DATA / name).read_text(encoding="utf-8"))


def normalize_name(name: str) -> str:
    return re.sub(r"[（）()]", "", name.translate(NAME_REPLACEMENTS))


def fingerprint(formula: dict, include_dose: bool = True) -> tuple:
    rows = []
    for ingredient in formula.get("ingredients", []):
        name = ingredient["name"].translate(NAME_REPLACEMENTS)
        if include_dose:
            rows.append((name, ingredient.get("dose", "")))
        else:
            rows.append(name)
    return tuple(sorted(rows))


def grouped_by_name(formulas: list[dict]) -> dict[str, list[dict]]:
    groups = defaultdict(list)
    for formula in formulas:
        groups[normalize_name(formula["name"])].append(formula)
    return groups


def audit() -> dict:
    shanghan = read_json("formulas.json")
    jinkui = read_json("jinkui_formulas.json")
    all_formulas = shanghan + jinkui
    all_groups = grouped_by_name(all_formulas)

    shanghan_name_duplicates = {
        name: [row["id"] for row in rows]
        for name, rows in grouped_by_name(shanghan).items()
        if len(rows) > 1
    }
    exact_groups = defaultdict(list)
    herb_groups = defaultdict(list)
    for formula in shanghan:
        exact = fingerprint(formula, include_dose=True)
        herbs = fingerprint(formula, include_dose=False)
        if exact:
            exact_groups[exact].append(formula["id"])
        if herbs:
            herb_groups[herbs].append(formula["id"])

    cross_book = []
    for name, rows in sorted(all_groups.items()):
        books = {row["book"] for row in rows}
        if len(books) < 2:
            continue
        signatures = {
            row["book"]: fingerprint(row, include_dose=True)
            for row in rows
        }
        cross_book.append(
            {
                "name": name,
                "ids": [row["id"] for row in rows],
                "same_composition_and_dose": len(set(signatures.values())) == 1,
            }
        )

    same_herb_set = [
        ids for ids in herb_groups.values() if len(ids) > 1
    ]
    return {
        "status": "pass" if not shanghan_name_duplicates else "review",
        "book_records": len(all_formulas),
        "unique_normalized_names": len(all_groups),
        "cross_book_same_name": len(cross_book),
        "cross_book_exact_composition_and_dose": sum(
            row["same_composition_and_dose"] for row in cross_book
        ),
        "cross_book_needs_item_review": sum(
            not row["same_composition_and_dose"] for row in cross_book
        ),
        "within_shanghan_name_duplicates": shanghan_name_duplicates,
        "within_shanghan_exact_composition_duplicates": [
            ids for ids in exact_groups.values() if len(ids) > 1
        ],
        "within_shanghan_same_herb_set_different_dose_or_form": same_herb_set,
        "cross_book_groups": cross_book,
    }


def main() -> int:
    result = audit()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if result["within_shanghan_name_duplicates"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
