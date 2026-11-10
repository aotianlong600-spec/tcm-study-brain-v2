"""Attach per-formula usage and Ni Haixia evidence to the catalog.

The generated evidence file intentionally leaves `why` empty until a formula
has been reviewed. A name hit in a page is a candidate, not proof that the
surrounding paragraph explains the formula.
"""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
SOURCES = ROOT / "sources"
OUTPUT = DATA / "formula_evidence.json"
REPORT = DATA / "evidence_report.json"

SHANGHAN_BOOK = "sources/ni_shanghan_pages.jsonl"
JINKUI_BOOK = "sources/ni_jinkui_pages.jsonl"
JINKUI_VIDEO = "sources/ni_jinkui_transcript.jsonl"


def read_json(name: str):
    return json.loads((DATA / name).read_text(encoding="utf-8"))


def read_pages(path: str) -> list[dict]:
    return [json.loads(line) for line in (ROOT / path).open(encoding="utf-8")]


def write_json(path: Path, value) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def normalize(text: str) -> str:
    text = text.replace("\r", "")
    text = re.sub(r"(.)\1{3,}", r"\1", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{2,}", "\n", text)
    return text.strip()


def candidates(pages: list[dict], terms: list[str], limit: int = 4) -> list[dict]:
    found = []
    seen = set()
    for page in pages:
        if page.get("page", 0) <= 2:
            continue
        text = normalize(page.get("text", ""))
        for term in terms:
            at = text.find(term)
            if at < 0:
                continue
            excerpt = text[max(0, at - 420) : at + 1000]
            key = (page["page"], excerpt[:100])
            if key in seen:
                continue
            seen.add(key)
            found.append(
                {
                    "page": page["page"],
                    "term": term,
                    "excerpt": excerpt,
                }
            )
            break
        if len(found) >= limit:
            break
    return found


def reviewed_overrides():
    """The first two formulas reviewed manually from local source pages."""
    return {
        "shanghan:桂枝汤": {
            "review_status": "reviewed",
            "usage_status": "reviewed",
            "usage_plain": "以水七升，微火煮取三升，去滓，适寒温，服一升。服后片刻啜热稀粥一升余，温覆约一时许，以遍身微似有汗为佳，不可大汗；一服病解即停后服。",
            "why": "倪注把本方的主证抓在“有汗、恶风”：汗出会持续耗损津液，所以用桂枝、白芍调和营卫，姜、枣、甘草顾护肠胃津液。桂枝壮心阳、促进动脉运行，白芍使静脉回流，目的不是见感冒就一律发汗。",
            "usage_note": "用法按倪注页16的讲解整理；原方仍以《伤寒论辑义》第295行组成和煎服法为底本。",
            "review_sources": [
                {
                    "kind": "倪海厦伤寒论",
                    "title": "倪海厦人纪系列之伤寒论",
                    "page": 15,
                    "excerpt": "为什么设计这方子？因为仲圣知道病人津液不断的在丧失，所以桂枝汤证一定有汗，“桂枝汤”的主证是病人有汗而且恶风，如果无汗，病人感冒发烧高热且完全没汗，就不是“桂枝汤”证。",
                },
                {
                    "kind": "倪海厦伤寒论",
                    "title": "倪海厦人纪系列之伤寒论",
                    "page": 16,
                    "excerpt": "桂枝这药可以壮心阳……白芍轻用可以补血，重用可以活血、破血……红枣、甘草、生姜下去，跟感冒没有关系，只是固本。",
                },
                {
                    "kind": "倪海厦伤寒论",
                    "title": "倪海厦人纪系列之伤寒论",
                    "page": 16,
                    "excerpt": "用七碗水，用大火煮，古时候……煮成三碗，渣拿掉，等温了再喝，一次服一碗。服了以后，等一下再喝热稀饭一碗，来帮忙药力。被子盖起来，躺一时，差不多二个小时，全身微发汗。",
                },
            ],
            "video_status": "local_transcript_missing",
            "video_note": "本地文件夹没有《伤寒论》独立视频同步文稿；未用《金匮要略》视频文稿代替。",
        },
        "jinkui:四逆加人参汤": {
            "review_status": "reviewed",
            "usage_status": "reviewed",
            "usage_plain": "四逆汤内加人参一两，余依四逆汤服法；原文并载：以水三升，煮取一升二合，去滓，分温再服。",
            "why": "倪注抓住“利止、恶寒、脉微、复利”这一组亡阳亡血表现：此时不是单纯贫血，而是血寒、津液将脱，所以用四逆汤回阳救逆，再加人参补津液与中气。",
            "usage_note": "用法来自《金匮要略》页11，并与页10视频同步文稿对照。",
            "review_sources": [
                {
                    "kind": "倪海厦金匮要略",
                    "title": "倪海厦注金匮要略",
                    "page": 11,
                    "excerpt": "利止，恶寒脉微，而复利，亡血也，四逆加人参汤主之。四逆汤内加人参一两，余依四逆汤服法。",
                },
                {
                    "kind": "视频同步文稿",
                    "title": "《金匮要略》——倪海厦人纪教程简体整理稿",
                    "page": 10,
                    "excerpt": "这个条辨呢，后面“利止，恶寒脉微，而复利，亡血也，四逆加人参汤主之。”……四逆汤症。……病人恶寒脉微心脏力量不够了。",
                },
            ],
            "video_status": "reviewed",
            "video_note": "已核对《金匮要略》视频同步文稿页10。",
        },
    }


def main() -> int:
    formulas = read_json("formulas.json") + read_json("jinkui_formulas.json")
    shanghan_pages = read_pages(SHANGHAN_BOOK)
    jinkui_pages = read_pages(JINKUI_BOOK)
    video_pages = read_pages(JINKUI_VIDEO)
    overrides = reviewed_overrides()
    evidence = {}

    for formula in formulas:
        book = formula.get("book")
        if book == "伤寒论":
            book_candidates = candidates(
                shanghan_pages,
                [formula["name"], *formula.get("aliases", [])],
            )
            video_candidates = []
            video_status = "local_transcript_missing"
            video_note = "本地未找到《伤寒论》独立视频同步文稿，当前只列倪海厦伤寒论书本候选。"
        else:
            book_candidates = candidates(
                jinkui_pages,
                [formula["name"], *formula.get("aliases", [])],
            )
            video_candidates = candidates(
                video_pages,
                [formula["name"], *formula.get("aliases", [])],
            )
            video_status = "candidates" if video_candidates else "no_local_hit"
            video_note = (
                "视频同步文稿中已找到候选页，尚未人工判定是否直接解释本方。"
                if video_candidates
                else "视频同步文稿中未直接命中本方名，仍需人工按章节核对。"
            )

        usage = formula.get("decoction", "").strip()
        entry = {
            "usage_status": "source_text" if usage else "missing",
            "usage_plain": usage,
            "usage_note": "",
            "why": "",
            "review_status": "pending",
            "candidate_sources": {
                "book": book_candidates,
                "video": video_candidates,
            },
            "review_sources": [],
            "video_status": video_status,
            "video_note": video_note,
        }
        if formula["id"] in overrides:
            entry.update(deepcopy(overrides[formula["id"]]))
        evidence[formula["id"]] = entry

    write_json(OUTPUT, evidence)
    review_counts = {}
    usage_counts = {}
    for entry in evidence.values():
        review_counts[entry["review_status"]] = review_counts.get(entry["review_status"], 0) + 1
        usage_counts[entry["usage_status"]] = usage_counts.get(entry["usage_status"], 0) + 1
    write_json(
        REPORT,
        {
            "formulas": len(formulas),
            "review_status": review_counts,
            "usage_status": usage_counts,
            "reviewed_ids": [key for key, value in evidence.items() if value["review_status"] == "reviewed"],
        },
    )
    print(f"evidence={len(evidence)} review={review_counts} usage={usage_counts}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
