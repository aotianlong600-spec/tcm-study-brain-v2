"""Check the local formula data before shipping it."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def main() -> int:
    shanghan = json.loads((DATA / "formulas.json").read_text(encoding="utf-8"))
    jinkui = json.loads((DATA / "jinkui_formulas.json").read_text(encoding="utf-8"))
    formulas = shanghan + jinkui
    herbs = json.loads((DATA / "herbs.json").read_text(encoding="utf-8"))
    evidence = json.loads((DATA / "formula_evidence.json").read_text(encoding="utf-8"))
    manifest = json.loads((DATA / "source_manifest.json").read_text(encoding="utf-8"))
    errors = []
    warnings = []

    ids = [item["id"] for item in formulas]
    if len(ids) != len(set(ids)):
        errors.append("方剂 id 重复")
    book_names = [(item.get("book"), item["name"]) for item in formulas]
    if len(book_names) != len(set(book_names)):
        errors.append("同书方剂名重复")
    if len(herbs) != len({item["id"] for item in herbs}):
        errors.append("中药 id 重复")

    source_text = (ROOT / "sources" / "shanghan_juyi.txt").read_text(
        encoding="gb18030"
    ).splitlines()
    for item in formulas:
        if len(item["ingredients"]) != item["expected_count"]:
            errors.append(f"{item['name']} 整理味数与 expected_count 不一致")
        if not item["ingredients"] and item.get("status") != "missing":
            errors.append(f"{item['name']} 无组成")
        missing_doses = sum(not row.get("dose") for row in item["ingredients"])
        if missing_doses:
            errors.append(f"{item['name']} 有 {missing_doses} 味缺剂量")
        if item.get("book") == "伤寒论":
            line = item["source"].get("line")
            if not line or not 1 <= line <= len(source_text):
                errors.append(f"{item['name']} 原文行号越界")
            elif item["name"] not in source_text[line - 1]:
                warnings.append(f"{item['name']} 行号未直接命中方名")
        elif not item["source"].get("page"):
            errors.append(f"{item['name']} 缺少金匮页码")
        if item["source_expected_count"] != len(item["source_ingredients"]):
            warnings.append(f"{item['name']} 原文计数与正文组成有版本差异")
        if any(url in json.dumps(item, ensure_ascii=False) for url in ("http://", "https://")):
            errors.append(f"{item['name']} 混入外部引用")
        if item["id"] not in evidence:
            errors.append(f"{item['name']} 缺少逐方校对记录")

    for source in manifest["sources"]:
        path = ROOT / source["path"]
        if not path.exists():
            errors.append(f"缺少来源文件 {source['path']}")
        elif sha256(path) != source["sha256"]:
            errors.append(f"{source['path']} sha256 不匹配")

    by_book = {}
    by_status = {}
    by_review = {}
    for item in formulas:
        by_book[item.get("book")] = by_book.get(item.get("book"), 0) + 1
        by_status[item.get("status")] = by_status.get(item.get("status"), 0) + 1
        review = evidence[item["id"]]["review_status"]
        by_review[review] = by_review.get(review, 0) + 1
    report = {
        "formulas": len(formulas),
        "herbs": len(herbs),
        "by_book": by_book,
        "by_status": by_status,
        "by_review": by_review,
        "errors": errors,
        "warnings": warnings,
        "status": "pass" if not errors else "fail",
    }
    with (DATA / "audit_report.json").open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
