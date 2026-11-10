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
    formulas = json.loads((DATA / "formulas.json").read_text(encoding="utf-8"))
    herbs = json.loads((DATA / "herbs.json").read_text(encoding="utf-8"))
    manifest = json.loads((DATA / "source_manifest.json").read_text(encoding="utf-8"))
    errors = []
    warnings = []

    ids = [item["id"] for item in formulas]
    names = [item["name"] for item in formulas]
    if len(ids) != len(set(ids)):
        errors.append("方剂 id 重复")
    if len(names) != len(set(names)):
        errors.append("方剂名重复")
    if len(herbs) != len({item["id"] for item in herbs}):
        errors.append("中药 id 重复")

    source_text = (ROOT / "sources" / "shanghan_juyi.txt").read_text(
        encoding="gb18030"
    ).splitlines()
    for item in formulas:
        if len(item["ingredients"]) != item["expected_count"]:
            errors.append(f"{item['name']} 整理味数与 expected_count 不一致")
        if not item["ingredients"]:
            errors.append(f"{item['name']} 无组成")
        if any(not row.get("dose") for row in item["ingredients"]):
            errors.append(f"{item['name']} 存在无剂量药味")
        line = item["source"]["line"]
        if not 1 <= line <= len(source_text):
            errors.append(f"{item['name']} 原文行号越界")
        elif item["name"] not in source_text[line - 1]:
            warnings.append(f"{item['name']} 行号未直接命中方名")
        if item["source_expected_count"] != len(item["source_ingredients"]):
            warnings.append(f"{item['name']} 原文计数与正文组成有版本差异")
        if any(url in json.dumps(item, ensure_ascii=False) for url in ("http://", "https://")):
            errors.append(f"{item['name']} 混入外部引用")

    for source in manifest["sources"]:
        path = ROOT / source["path"]
        if path.exists() and sha256(path) != source["sha256"]:
            errors.append(f"{source['path']} sha256 不匹配")

    report = {
        "formulas": len(formulas),
        "herbs": len(herbs),
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
