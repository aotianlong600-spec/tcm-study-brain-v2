"""Normalize the source-traceable Jinkui extraction into the app schema.

No extracted formula is dropped. Records that lack a count anchor, have a
count mismatch, or contain missing doses stay in the catalog and are marked.
"""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "sources" / "jinkui_recipes_source.json"
OUTPUT = ROOT / "data" / "jinkui_formulas.json"
REPORT = ROOT / "data" / "jinkui_report.json"

ALIASES = {
    "灸甘草汤": ["炙甘草汤"],
    "栝篓桂枝汤": ["栝蒌桂枝汤", "瓜蒌桂枝汤"],
    "桂枝龙骨牡蛎汤": ["桂枝加龙骨牡蛎汤"],
    "桅子大黄汤": ["栀子大黄汤"],
    "猪膏髪煎": ["猪膏发煎"],
    "膏髪煎": ["膏发煎"],
    "烧裩散": ["烧裈散"],
    "大黄蟅虫丸": ["大黄䗪虫丸"],
}

KNOWN_SINGLE_HERB = {
    "一物瓜蒂汤",
    "矾石汤",
    "文蛤散",
    "诃黎勒散",
    "狼牙汤",
}

STATUS_LABELS = {
    "complete": "味数已核",
    "partial": "有缺口",
    "mismatch": "味数不符",
    "unchecked": "未找到校验锚点",
    "derived": "加味方",
    "missing": "原文缺",
}


def write_json(path: Path, value) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def status_for(item: dict) -> tuple[str, list[str]]:
    ingredients = item.get("ingredients") or []
    issues = []
    if not ingredients:
        return "missing", ["没有解析出组成"]
    if item.get("derivative"):
        derivative = item["derivative"]
        additions = "、".join(part.get("name", "") for part in derivative.get("additions", []))
        issues.append(f"加味方：基础方{derivative.get('base')}，加{additions}")
        return "derived", issues
    if item.get("count_ok") is False:
        issues.append(f"原文上{item.get('expected_count')}味，已解析{len(ingredients)}味")
        return "mismatch", issues
    if item.get("count_ok") is None:
        issues.append("原文未找到“上X味/右X味”校验锚点")
        return "unchecked", issues

    missing_doses = sum(not row.get("dose") for row in ingredients)
    suspects = sum(bool(row.get("suspect")) for row in ingredients)
    if missing_doses:
        issues.append(f"{missing_doses}味缺剂量")
    if suspects:
        issues.append(f"{suspects}味药名待核")
    if item["name"] == "乌头桂枝汤":
        issues.append("正文只抽到乌头，桂枝汤组成尚未展开")
        return "partial", issues
    if item["name"] not in KNOWN_SINGLE_HERB and len(ingredients) == 1 and item.get("expected_count") == 1:
        issues.append("单味记录可能来自加减法，需核对是否应展开基础方")
        return "partial", issues
    return ("partial" if issues else "complete"), issues


def convert(item: dict) -> dict:
    ingredients = []
    for row in item.get("ingredients") or []:
        ingredients.append(
            {
                "name": row.get("name") or row.get("herb_ref") or "",
                "dose": row.get("dose") or "",
                "processing": row.get("prep") or "",
                "raw": row.get("raw") or "",
                "herb_ref": row.get("herb_ref") or "",
                "suspect": bool(row.get("suspect")),
            }
        )
    status, issues = status_for(item)
    source_excerpt = "\n".join(
        part.strip()
        for part in (item.get("composition_raw", ""), item.get("decoction", ""))
        if part and part.strip()
    )
    return {
        "id": item["id"],
        "name": item["name"],
        "aliases": ALIASES.get(item["name"], []),
        "book": "金匮要略",
        "type": item["type"],
        "six_meridian": "",
        "status": status,
        "status_label": STATUS_LABELS[status],
        "chapter": item.get("chapter", ""),
        "indication": item.get("notes", "").split("\n", 1)[0][:180],
        "ingredients": ingredients,
        "source_ingredients": deepcopy(ingredients),
        "expected_count": len(ingredients),
        "source_expected_count": item.get("expected_count") or 0,
        "composition_raw": item.get("composition_raw", ""),
        "decoction": item.get("decoction", ""),
        "notes": item.get("notes", ""),
        "adjuncts": [],
        "derivative": deepcopy(item.get("derivative")),
        "quality": {
            "count_ok": item.get("count_ok"),
            "missing_doses": sum(not row["dose"] for row in ingredients),
            "suspects": sum(row["suspect"] for row in ingredients),
            "issues": issues,
        },
        "source": {
            "title": item.get("source", "倪海厦注金匮要略"),
            "page": item.get("page"),
            "chapter": item.get("chapter", ""),
            "path": "sources/jinkui_recipes_source.json",
            "excerpt": source_excerpt,
            "note": "；".join(issues) if issues else "同条“上X味/右X味”与解析味数一致。",
        },
    }


def main() -> int:
    source = json.loads(SOURCE.read_text(encoding="utf-8"))
    formulas = [convert(item) for item in source]
    counts: dict[str, int] = {}
    for item in formulas:
        counts[item["status"]] = counts.get(item["status"], 0) + 1
    write_json(OUTPUT, formulas)
    write_json(
        REPORT,
        {
            "source_records": len(source),
            "accepted_records": len(formulas),
            "status_counts": counts,
            "mismatch": [item["name"] for item in formulas if item["status"] == "mismatch"],
            "unchecked": [item["name"] for item in formulas if item["status"] == "unchecked"],
            "derived": [item["name"] for item in formulas if item["status"] == "derived"],
        },
    )
    print(f"jinkui accepted={len(formulas)} status={counts} output={OUTPUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
