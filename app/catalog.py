"""Read-only local catalog shared by the API and HTML app."""
from __future__ import annotations

from copy import deepcopy
from functools import lru_cache
import json
from pathlib import Path
import re

from etl.herb_alias import ALIAS


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"


def _read(name: str):
    return json.loads((DATA / name).read_text(encoding="utf-8"))


def _norm(value: str) -> str:
    return re.sub(r"[\s·・，,。；;（）()]+", "", value or "").lower()


def _resolve_herb(name: str, herbs_by_name: dict[str, dict]) -> dict | None:
    target = ALIAS.get(name, (name, ""))[0]
    return herbs_by_name.get(target) or herbs_by_name.get(name)


def _summary(formula: dict) -> dict:
    return {
        "id": formula["id"],
        "name": formula["name"],
        "type": formula["type"],
        "six_meridian": formula["six_meridian"],
        "ingredient_count": len(formula["ingredients"]),
        "source_line": formula["source"]["line"],
        "source_note": formula["source"].get("note", ""),
    }


@lru_cache(maxsize=1)
def _index() -> dict:
    formulas = _read("formulas.json")
    herbs = _read("herbs.json")
    herbs_by_name = {item["name"]: item for item in herbs}

    formula_links: dict[str, list[dict]] = {}
    for formula in formulas:
        for ingredient in formula["ingredients"]:
            herb = _resolve_herb(ingredient["name"], herbs_by_name)
            if herb:
                formula_links.setdefault(herb["id"], []).append(_summary(formula))

    return {
        "formulas": formulas,
        "formulas_by_id": {item["id"]: item for item in formulas},
        "herbs": herbs,
        "herbs_by_id": {item["id"]: item for item in herbs},
        "herbs_by_name": herbs_by_name,
        "formula_links": formula_links,
    }


def _formula_text(formula: dict) -> str:
    return " ".join(
        [
            formula["name"],
            formula.get("indication", ""),
            formula.get("composition_raw", ""),
            formula.get("decoction", ""),
            formula["source"].get("note", ""),
        ]
    )


def _herb_text(herb: dict) -> str:
    return " ".join([herb["name"], *herb.get("names", []), *herb.get("sections", {}).values()])


def list_formulas(query: str = "", kind: str = "", meridian: str = "", page: int = 1, page_size: int = 24) -> dict:
    query_norm = _norm(query)
    kind = kind.strip()
    meridian = meridian.strip()
    items = [
        item
        for item in _index()["formulas"]
        if (not kind or item["type"] == kind)
        and (not meridian or item["six_meridian"] == meridian)
        and (not query_norm or query_norm in _norm(_formula_text(item)))
    ]
    total = len(items)
    start = max(0, (page - 1) * page_size)
    return {
        "items": [_summary(item) for item in items[start : start + page_size]],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


def get_formula(formula_id: str) -> dict | None:
    formula = _index()["formulas_by_id"].get(formula_id)
    if not formula:
        return None
    result = deepcopy(formula)
    linked = []
    for ingredient in result["ingredients"]:
        herb = _resolve_herb(ingredient["name"], _index()["herbs_by_name"])
        if herb:
            ingredient["herb_id"] = herb["id"]
            ingredient["herb_name"] = herb["name"]
            linked.append({"id": herb["id"], "name": herb["name"]})
    result["related_herbs"] = linked
    return result


def list_herbs(query: str = "", category: str = "", page: int = 1, page_size: int = 24) -> dict:
    query_norm = _norm(query)
    category = category.strip()
    items = [
        item
        for item in _index()["herbs"]
        if (not category or category in item.get("sections", {}))
        and (not query_norm or query_norm in _norm(_herb_text(item)))
    ]
    total = len(items)
    start = max(0, (page - 1) * page_size)
    return {
        "items": [
            {
                "id": item["id"],
                "name": item["name"],
                "page": item["page_start"],
                "formula_count": len(_index()["formula_links"].get(item["id"], [])),
                "source": item.get("source", ""),
            }
            for item in items[start : start + page_size]
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


def get_herb(herb_id: str) -> dict | None:
    herb = _index()["herbs_by_id"].get(herb_id)
    if not herb:
        return None
    result = deepcopy(herb)
    result["formulas"] = deepcopy(_index()["formula_links"].get(herb_id, []))
    return result


def overview() -> dict:
    formulas = _index()["formulas"]
    report = _read("formulas_report.json")
    source_mismatches = [
        item["name"]
        for item in formulas
        if item["source_expected_count"] != len(item["source_ingredients"])
        or item["source_expected_count"] != len(item["ingredients"])
    ]
    return {
        "formulas": len(formulas),
        "herbs": len(_index()["herbs"]),
        "source_checked": len(formulas),
        "source_variants": source_mismatches,
        "source_pending": len(report.get("pending", [])),
        "modules": {
            "formulas": "ready",
            "herbs": "ready",
            "diagnosis": "not_imported",
            "acupuncture": "not_imported",
            "conditions": "not_imported",
        },
    }
