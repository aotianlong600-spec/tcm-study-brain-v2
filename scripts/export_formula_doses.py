"""Export readable formula/dose indexes and the bundled book inventory."""
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
EXPORTS = ROOT / "exports"
BOOKS = ROOT / "books" / "ni-haixia-medicine"


def read_json(name: str):
    return json.loads((DATA / name).read_text(encoding="utf-8"))


def ingredient_text(formula: dict) -> str:
    if not formula.get("ingredients"):
        return "原方缺" if formula.get("status") == "missing" else "组成未载"
    parts = []
    for row in formula.get("ingredients", []):
        text = f"{row['name']} {row.get('dose', '剂量未注')}".strip()
        if row.get("processing"):
            text += f"（{row['processing']}）"
        parts.append(text)
    return "；".join(parts)


def source_text(formula: dict) -> tuple[str, str]:
    source = formula.get("source") or {}
    title = source.get("title", "")
    if source.get("line"):
        return title, f"第 {source['line']} 行"
    if source.get("page"):
        return title, f"第 {source['page']} 页"
    return title, source.get("path", "")


def write_csv(formulas: list[dict], evidence: dict) -> None:
    path = EXPORTS / "formulas_with_doses.csv"
    fields = [
        "id",
        "book",
        "name",
        "type",
        "six_meridian",
        "status",
        "review_status",
        "ingredient_count",
        "ingredients_with_doses",
        "decoction",
        "source_title",
        "source_locator",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for formula in formulas:
            source_title, source_locator = source_text(formula)
            writer.writerow(
                {
                    "id": formula["id"],
                    "book": formula.get("book", ""),
                    "name": formula["name"],
                    "type": formula.get("type", ""),
                    "six_meridian": formula.get("six_meridian", ""),
                    "status": formula.get("status_label", formula.get("status", "")),
                    "review_status": evidence.get(formula["id"], {}).get("review_status", "pending"),
                    "ingredient_count": len(formula.get("ingredients", [])),
                    "ingredients_with_doses": ingredient_text(formula),
                    "decoction": formula.get("decoction", ""),
                    "source_title": source_title,
                    "source_locator": source_locator,
                }
            )


def write_markdown(formulas: list[dict], evidence: dict) -> None:
    lines = [
        "# 经方与剂量总表",
        "",
        "按当前本地方剂目录逐条导出。药物和剂量保留原书单位；版本差异与安全说明在各方详情页和校对记录中。",
        "",
    ]
    for book in ("伤寒论", "金匮要略"):
        lines.extend([f"## {book}", "", "| 序号 | 方名 | 剂型 | 篇次 | 药物与剂量 | 逐方校 |", "|---:|---|---|---|---|---|"])
        rows = [formula for formula in formulas if formula.get("book") == book]
        for index, formula in enumerate(rows, 1):
            status = evidence.get(formula["id"], {}).get("review_status", "pending")
            lines.append(
                f"| {index} | {formula['name']} | {formula.get('type', '')} | "
                f"{formula.get('six_meridian', '')} | {ingredient_text(formula)} | "
                f"{'已校' if status == 'reviewed' else '待校'} |"
            )
        lines.append("")
    (ROOT / "docs" / "formula-dosage-index.md").write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def write_book_inventory() -> None:
    rows = []
    for path in sorted(item for item in BOOKS.rglob("*") if item.is_file()):
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        rows.append(
            f"| {path.name} | {path.stat().st_size:,} | `{digest}` |"
        )
    content = "\n".join(
        [
            "# 倪海厦医学资料",
            "",
            "| 文件 | 字节 | SHA-256 |",
            "|---|---:|---|",
            *rows,
            "",
        ]
    )
    (ROOT / "books" / "README.md").write_text(content, encoding="utf-8", newline="\n")


def main() -> int:
    EXPORTS.mkdir(exist_ok=True)
    formulas = read_json("formulas.json") + read_json("jinkui_formulas.json")
    evidence = read_json("formula_evidence.json")
    write_csv(formulas, evidence)
    write_markdown(formulas, evidence)
    write_book_inventory()
    print(
        json.dumps(
            {
                "formulas": len(formulas),
                "formula_csv": str(EXPORTS / "formulas_with_doses.csv"),
                "dose_index": str(ROOT / "docs" / "formula-dosage-index.md"),
                "books": sum(1 for path in BOOKS.rglob("*") if path.is_file()),
                "book_inventory": str(ROOT / "books" / "README.md"),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
