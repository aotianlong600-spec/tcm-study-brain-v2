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
    source = formula["source"]
    return {
        "id": formula["id"],
        "name": formula["name"],
        "book": formula.get("book", ""),
        "type": formula["type"],
        "status": formula.get("status", "complete"),
        "status_label": formula.get("status_label", ""),
        "six_meridian": formula["six_meridian"],
        "chapter": formula.get("chapter", ""),
        "ingredient_count": len(formula["ingredients"]),
        "locator": source.get("line") or source.get("page") or "",
        "source_title": source.get("title", ""),
        "source_note": source.get("note", ""),
        "review_status": formula.get("evidence", {}).get("review_status", "pending"),
    }


@lru_cache(maxsize=1)
def _index() -> dict:
    formulas = _read("formulas.json") + _read("jinkui_formulas.json")
    evidence = _read("formula_evidence.json")
    for formula in formulas:
        formula["evidence"] = evidence.get(formula["id"], {})
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
            formula.get("book", ""),
            formula.get("chapter", ""),
            formula.get("indication", ""),
            formula.get("composition_raw", ""),
            formula.get("decoction", ""),
            formula.get("notes", ""),
            " ".join(formula.get("aliases", [])),
            formula["source"].get("note", ""),
            formula.get("evidence", {}).get("usage_plain", ""),
            formula.get("evidence", {}).get("why", ""),
        ]
    )


def _herb_text(herb: dict) -> str:
    return " ".join([herb["name"], *herb.get("names", []), *herb.get("sections", {}).values()])


def list_formulas(
    query: str = "",
    kind: str = "",
    meridian: str = "",
    book: str = "",
    status: str = "",
    review: str = "",
    page: int = 1,
    page_size: int = 24,
) -> dict:
    query_norm = _norm(query)
    kind = kind.strip()
    meridian = meridian.strip()
    book = book.strip()
    status = status.strip()
    review = review.strip()
    items = [
        item
        for item in _index()["formulas"]
        if (not kind or item["type"] == kind)
        and (not meridian or item["six_meridian"] == meridian)
        and (not book or item.get("book") == book)
        and (not status or item.get("status") == status)
        and (not review or item.get("evidence", {}).get("review_status") == review)
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


def list_six_channels() -> dict:
    return {"items": deepcopy(_read("six_channels.json")["items"])}


def get_six_channel(channel_id: str) -> dict | None:
    channel = next(
        (item for item in _read("six_channels.json")["items"] if item["id"] == channel_id),
        None,
    )
    return deepcopy(channel) if channel else None


def overview() -> dict:
    formulas = _index()["formulas"]
    by_book = {}
    by_status = {}
    review_status = {}
    for item in formulas:
        book = item.get("book", "")
        status = item.get("status", "")
        by_book[book] = by_book.get(book, 0) + 1
        by_status[status] = by_status.get(status, 0) + 1
        review = item.get("evidence", {}).get("review_status", "pending")
        review_status[review] = review_status.get(review, 0) + 1
    return {
        "formulas": len(formulas),
        "herbs": len(_index()["herbs"]),
        "by_book": by_book,
        "by_status": by_status,
        "review_status": review_status,
        "source_pending": by_status.get("missing", 0),
        "six_channels": len(_read("six_channels.json")["items"]),
        "modules": {
            "formulas": "ready",
            "herbs": "ready",
            "diagnosis": "not_imported",
            "six_channels": "partial",
            "acupuncture": "not_imported",
            "conditions": "not_imported",
        },
    }
