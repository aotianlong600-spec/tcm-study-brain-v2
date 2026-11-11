"""Validate isolated agent batches before they enter the main catalog."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
BATCHES = DATA / "curated_batches"
MANIFEST = DATA / "curated_batch_manifest.json"

REQUIRED = {
    "review_status",
    "review_level",
    "usage_status",
    "usage_plain",
    "why",
    "symptoms",
    "overview",
    "six_channel",
    "formula_original",
    "usage_original",
    "usage_modern",
    "page_reading",
    "rationale",
    "annotations",
    "proofreading",
    "editorial_note",
}
PLACEHOLDERS = ("本地文件夹未找到", "尚待逐方", "待整理", "原文页索引", "候选原文")
TOXIC_TERMS = ("生附子", "附子", "半夏", "乌头", "巴豆", "细辛", "人尿", "猪胆")


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def nonempty_list(value) -> bool:
    return isinstance(value, list) and bool(value)


def validate_entry(formula_id: str, entry: dict) -> list[str]:
    errors = []
    missing = sorted(REQUIRED - set(entry))
    if missing:
        return [f"missing fields: {', '.join(missing)}"]
    if entry["review_status"] != "reviewed":
        errors.append("review_status must be reviewed")
    missing_formula = "缺方" in str(entry["review_level"])
    allowed_usage = {"reviewed", "missing"} if missing_formula else {"reviewed"}
    if entry["usage_status"] not in allowed_usage:
        errors.append(f"usage_status must be one of {sorted(allowed_usage)}")
    if not str(entry["review_level"]).strip():
        errors.append("review_level is empty")
    if not str(entry["usage_plain"]).strip() or not str(entry["why"]).strip():
        errors.append("usage_plain or why is empty")
    if len(entry["symptoms"]) < 1:
        errors.append("symptoms are empty")

    overview = entry["overview"]
    if not str(overview.get("title", "")).strip() or len(overview.get("paragraphs", [])) < 4:
        errors.append("overview needs a title and at least four paragraphs")
    if not nonempty_list(overview.get("key_points")):
        errors.append("overview key_points are empty")

    six = entry["six_channel"]
    if not six.get("id") or not six.get("name") or not str(six.get("summary", "")).strip():
        errors.append("six_channel identity or summary is empty")
    if not nonempty_list(six.get("original")) or not nonempty_list(six.get("annotations")):
        errors.append("six_channel needs original text and annotations")

    formula = entry["formula_original"]
    if not str(formula.get("title", "")).strip() or not str(formula.get("text", "")).strip():
        errors.append("formula_original is incomplete")
    if not nonempty_list(formula.get("source_pages")):
        errors.append("formula_original source_pages are empty")

    ancient = entry["usage_original"]
    if not str(ancient.get("text", "")).strip() or not nonempty_list(ancient.get("source_pages")):
        errors.append("usage_original or its source_pages are empty")

    modern = entry["usage_modern"]
    if not str(modern.get("source_text", "")).strip():
        errors.append("usage_modern source_text is empty")
    if not nonempty_list(modern.get("cautions")):
        errors.append("usage_modern needs cautions")
    if not missing_formula and not nonempty_list(modern.get("steps")):
        errors.append("usage_modern needs steps")

    pages = entry["page_reading"]
    if not nonempty_list(pages):
        errors.append("page_reading is empty")
    elif any(not isinstance(row.get("page"), int) for row in pages):
        errors.append("page_reading contains a non-integer page")

    if len(str(entry["rationale"].get("full_text", "")).strip()) < 200:
        errors.append("rationale.full_text is too short for a reviewed module")
    if not nonempty_list(entry["annotations"]) or not nonempty_list(entry["proofreading"]):
        errors.append("annotations or proofreading are empty")
    if not str(entry["editorial_note"]).strip():
        errors.append("editorial_note is empty")

    searchable = "\n".join(
        [
            str(formula.get("text", "")),
            str(ancient.get("text", "")),
            str(modern.get("source_text", "")),
        ]
    )
    if any(term in searchable for term in TOXIC_TERMS):
        caution_text = " ".join(modern.get("cautions", []))
        if not re.search(r"毒|风险|专业|医师|炮制|不可|禁|监护", caution_text):
            errors.append("toxic or high-risk material lacks a usable caution")

    combined = json.dumps(entry, ensure_ascii=False)
    found = [phrase for phrase in PLACEHOLDERS if phrase in combined]
    if found:
        errors.append(f"contains placeholder language: {', '.join(found)}")
    if not formula_id:
        errors.append("formula id is empty")
    return errors


def validate_all(accepted_only: bool = False) -> tuple[int, list[str]]:
    formulas = read_json(DATA / "formulas.json") + read_json(DATA / "jinkui_formulas.json")
    known_ids = {row["id"] for row in formulas}
    seen = set()
    errors = []
    count = 0
    paths = sorted(BATCHES.glob("*.json"))
    if accepted_only:
        accepted = read_json(MANIFEST).get("accepted", [])
        paths = [BATCHES / name for name in accepted]
    for path in paths:
        batch = read_json(path)
        if not isinstance(batch, dict) or not batch:
            errors.append(f"{path.name}: expected a non-empty object")
            continue
        for formula_id, entry in batch.items():
            count += 1
            if formula_id in seen:
                errors.append(f"{formula_id}: duplicate across batch files")
            seen.add(formula_id)
            if formula_id not in known_ids:
                errors.append(f"{formula_id}: id is not in the formula catalog")
            if not isinstance(entry, dict):
                errors.append(f"{formula_id}: module is not an object")
                continue
            for error in validate_entry(formula_id, entry):
                errors.append(f"{formula_id}: {error}")
    return count, errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--accepted", action="store_true")
    args = parser.parse_args()
    count, errors = validate_all(accepted_only=args.accepted)
    mode = "accepted" if args.accepted else "all"
    print(json.dumps({"mode": mode, "batches": count, "errors": errors}, ensure_ascii=False, indent=2))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
