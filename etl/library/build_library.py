"""Build data/library/{catalog,cross_links}.json and Stage 5A data/relations/{syndrome_clusters,unified_network}.json."""
from __future__ import annotations

from collections import defaultdict
import json
from pathlib import Path
import re
from typing import Any

import zhconv


ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"
SOURCES_DIR = ROOT / "sources"
LIB_SOURCES_DIR = SOURCES_DIR / "library"
LIB_DATA_DIR = DATA_DIR / "library"
REL_DATA_DIR = DATA_DIR / "relations"


SHELF_META = {
    "renji_core": {"label": "人纪四大经典与教程", "order": 1, "description": "倪海厦人纪针灸、神农本草、黄帝内经、伤寒论、金匮要略核心原文与视频文稿"},
    "hantang_clinical": {"label": "汉唐临床方剂与医案", "order": 2, "description": "汉唐经方讲解（HT系列）、汉唐经典文章与医案集、传统中医跟诊实录"},
    "classical_companions": {"label": "古籍注疏与经方辅注", "order": 3, "description": "血证论、石室秘录、伤寒论辑义、大冢敬节解说、证因方论集要及影印古籍"},
}


BOOK_REGISTRY: list[dict[str, Any]] = [
    {
        "book_id": "ni-acupuncture-v2-20100703",
        "title": "倪海厦人纪系列之针灸教程",
        "short_title": "人纪·针灸教程",
        "author_era": "倪海厦（2010年校订版）",
        "shelf": "renji_core",
        "tradition_layer": "ni_lecture",
        "module_affinities": ["acupuncture"],
        "description": "针灸大成讲授、十二经络与奇经八脉穴位定位、五行五俞穴、子午流注及常见急慢症配穴治法。",
    },
    {
        "book_id": "ni-bencao-pdf",
        "title": "倪海厦注神农本草经（清晰版）",
        "short_title": "人纪·神农本草经",
        "author_era": "神农本经原文 · 倪海厦讲注",
        "shelf": "renji_core",
        "tradition_layer": "ni_lecture",
        "module_affinities": ["herbs"],
        "description": "上中下三品本草原文、药性味毒及倪海厦经方配伍发挥与真假药材临床辨析。",
    },
    {
        "book_id": "ni-neijing-vol1-pdf",
        "title": "倪海厦人纪系列之《黄帝内经》上册",
        "short_title": "人纪·黄帝内经上册",
        "author_era": "《素问》选讲 · 倪海厦视频同步整理",
        "shelf": "renji_core",
        "tradition_layer": "ni_lecture",
        "module_affinities": ["neijing"],
        "description": "素问上古天真论至六节藏象、脉要精微与阴阳五行脏腑经络病机讲解。",
    },
    {
        "book_id": "ni-neijing-vol2-pdf",
        "title": "倪海厦人纪系列之《黄帝内经》下册",
        "short_title": "人纪·黄帝内经下册",
        "author_era": "《素问》后半与专题 · 倪海厦视频同步整理",
        "shelf": "renji_core",
        "tradition_layer": "ni_lecture",
        "module_affinities": ["neijing"],
        "description": "痹论、痿论、热论、刺法刺禁、五运六气与重实杂病临证发挥。",
    },
    {
        "book_id": "ni-shanghan-pdf",
        "title": "倪海厦人纪系列之伤寒论",
        "short_title": "人纪·伤寒论",
        "author_era": "张仲景原文 · 倪海厦人纪讲授",
        "shelf": "renji_core",
        "tradition_layer": "ni_lecture",
        "module_affinities": ["formulas"],
        "description": "六经辨证（太阳、阳明、少阳、太阴、少阴、厥阴）全本条文、方剂组成与经方煎服临证思路。",
    },
    {
        "book_id": "ni-jinkui-pdf",
        "title": "倪海厦人纪系列之金匮要略（注释版）",
        "short_title": "人纪·金匮要略注释",
        "author_era": "张仲景原文 · 倪海厦注释",
        "shelf": "renji_core",
        "tradition_layer": "ni_lecture",
        "module_affinities": ["formulas"],
        "description": "脏腑经络先后至妇人杂病二十二篇杂病脉证并治原文与倪海厦精解。",
    },
    {
        "book_id": "ni-jinkui-video-pdf",
        "title": "《金匮要略》人纪教程视频同步文稿",
        "short_title": "金匮·视频同步文稿",
        "author_era": "倪海厦视频口述逐字整理",
        "shelf": "renji_core",
        "tradition_layer": "ni_lecture",
        "module_affinities": ["formulas"],
        "description": "与金匮视频课程同步之口述详解、临床医案补充及历节、胸痹、水气病细节发挥。",
    },
    {
        "book_id": "ni-hantang-formulas-pdf",
        "title": "倪海厦 · 汉唐中医方剂讲解",
        "short_title": "汉唐方剂讲解（HT系列）",
        "author_era": "倪海厦（汉唐中医诊所）",
        "shelf": "hantang_clinical",
        "tradition_layer": "hantang_clinical",
        "module_affinities": ["formulas", "herbs"],
        "description": "HT-1至HT-93汉唐常用经验方剂讲解、适应症对比及伤寒金匮经方临床转化思路（供文献学习，不可替代个人处方）。",
    },
    {
        "book_id": "ni-hantang-articles-cases-pdf",
        "title": "倪海厦汉唐中医经典文章医案集",
        "short_title": "汉唐文章与医案集",
        "author_era": "倪海厦（汉唐中医网辑录）",
        "shelf": "hantang_clinical",
        "tradition_layer": "hantang_clinical",
        "module_affinities": ["formulas", "acupuncture", "neijing"],
        "description": "佛州临床真实诊疗医案集锦、诊疗六大健康标准问答及经方与针灸配伍实战记录。",
    },
    {
        "book_id": "ni-hantang-clinic-notes-pdf",
        "title": "倪海厦传统中医跟诊过程（心得）",
        "short_title": "传统中医跟诊实录",
        "author_era": "人纪弟子跟诊笔记",
        "shelf": "hantang_clinical",
        "tradition_layer": "hantang_clinical",
        "module_affinities": ["formulas", "acupuncture"],
        "description": "跟诊佛州汉唐诊所临证十问、望色切脉、下针次序与急症处理心得实录。",
    },
    {
        "book_id": "tang-rongchuan-xuezhenglun-pdf",
        "title": "《血证论》",
        "short_title": "唐容川·血证论",
        "author_era": "清·唐容川（唐宗海）",
        "shelf": "classical_companions",
        "tradition_layer": "commentary",
        "module_affinities": ["formulas", "herbs", "neijing"],
        "description": "治血四法（止血、消瘀、宁血、补虚）与水火气血升降精义，经方治失血、瘀血、咳血之重要辅参。",
    },
    {
        "book_id": "chen-shiduo-shishimilu-txt",
        "title": "《石室秘录》",
        "short_title": "陈士铎·石室秘录",
        "author_era": "清·陈士铎",
        "shelf": "classical_companions",
        "tradition_layer": "commentary",
        "module_affinities": ["formulas", "herbs"],
        "description": "正治、反治、顺治、逆治与脏腑疑难杂症辨治方论，补临床变证与药味配伍之参。",
    },
    {
        "book_id": "shanghan-juyi-book-txt",
        "title": "《伤寒论辑义》",
        "short_title": "丹波元珍·伤寒论辑义",
        "author_era": "日本·丹波元珍（多纪元简）",
        "shelf": "classical_companions",
        "tradition_layer": "commentary",
        "module_affinities": ["formulas", "herbs"],
        "description": "博采唐宋元明清诸家伤寒注本与药物考证，保留各家异同说而不偏废。",
    },
    {
        "book_id": "otsuka-shanghan-docx",
        "title": "《大冢敬节伤寒论解说》",
        "short_title": "大冢敬节·伤寒论解说",
        "author_era": "日本汉方·大冢敬节",
        "shelf": "classical_companions",
        "tradition_layer": "commentary",
        "module_affinities": ["formulas"],
        "description": "日本汉方腹诊与伤寒条文实证讲解，提供经方临床抓主证的另一视角。",
    },
    {
        "book_id": "wang-rulin-zhengyinfanglun-doc",
        "title": "《证因方论集要》",
        "short_title": "汪汝麟·证因方论集要",
        "author_era": "清·汪汝麟",
        "shelf": "classical_companions",
        "tradition_layer": "commentary",
        "module_affinities": ["formulas"],
        "description": "从证求因、从因立法集要选录（OLE旧版文档结构化抽出22节全文）。",
    },
    {
        "book_id": "xu-lingtai-collection-pdf",
        "title": "《明清名医全书大成·徐灵胎医学全书》",
        "short_title": "徐灵胎医学全书（影印扫描）",
        "author_era": "清·徐灵胎（徐大椿）",
        "shelf": "classical_companions",
        "tradition_layer": "commentary",
        "module_affinities": ["formulas", "neijing", "herbs"],
        "description": "原书434页扫描影印版（当前未执行虚假OCR，支持逐页高清扫描浏览与目录线索查阅）。",
    },
    {
        "book_id": "huangdi-waijing-pdf",
        "title": "《黄帝外经》",
        "short_title": "黄帝外经（影印扫描）",
        "author_era": "古传外经本（影印扫描）",
        "shelf": "classical_companions",
        "tradition_layer": "commentary",
        "module_affinities": ["neijing", "acupuncture"],
        "description": "原书85页扫描影印版（当前未执行虚假OCR，支持逐页高清影印原件浏览）。",
    },
]


# Prevent overly generic words or ambiguous 2-char phrases from generating noise in entity auto-linking
AMBIGUOUS_ENTITY_NAMES = {
    "前言", "目录", "附录", "总论", "大论", "太阳", "阳明", "少阳", "太阴", "少阴", "厥阴",
    "中药", "方剂", "水肿", "头痛", "咳嗽", "失眠", "中风", "眩晕", "喘", "黄疸", "消渴",
    "阴", "阳", "血", "气", "水", "火", "肺", "心", "脾", "肝", "肾", "胃", "胆", "肠",
    "大豆", "小麦", "大枣", "生姜", "干姜", "甘草", "蜂蜜", "白蜜", "清酒", "白酒", "苦酒",
    "白", "青", "黄", "赤", "黑", "寒", "热", "风", "湿", "燥", "虚", "实",
    "太阳经", "阳明经", "少阳经", "太阴经", "少阴经", "厥阴经",
    "大青", "白兔", "人乳", "发", "水", "盐",
}


def _norm_simp(text: str) -> str:
    return zhconv.convert(text or "", "zh-cn")


def _extract_chapters_from_jsonl(book_id: str, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    chapters: list[dict[str, Any]] = []
    seen_titles: set[str] = set()
    for row in rows:
        headings = row.get("headings") or []
        pno = int(row["page_no"])
        for h in headings:
            clean_h = re.sub(r"\s+", " ", h).strip()
            if not clean_h or clean_h in seen_titles or len(clean_h) > 40:
                continue
            seen_titles.add(clean_h)
            chapters.append({"title": clean_h, "page_no": pno, "unit_label": row.get("unit_label", "")})
        if not headings and row.get("section_title"):
            sec = re.sub(r"\s+", " ", str(row["section_title"])).strip()
            if sec and sec not in seen_titles and sec != "扫描影像页（未执行虚假OCR）" and len(sec) <= 40:
                seen_titles.add(sec)
                chapters.append({"title": sec, "page_no": pno, "unit_label": row.get("unit_label", "")})
    return chapters[:200]


def _load_book_rows(book_id: str) -> list[dict[str, Any]]:
    path = LIB_SOURCES_DIR / f"{book_id}.jsonl"
    return [json.loads(ln) for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]


def _collect_entities() -> list[dict[str, Any]]:
    entities: list[dict[str, Any]] = []

    # 1. Formulas (Shanghan 113 + Jinkui 186 = 299)
    for fn_name in ("formulas.json", "jinkui_formulas.json"):
        raw = json.loads((DATA_DIR / fn_name).read_text(encoding="utf-8"))
        formulas_list = raw if isinstance(raw, list) else raw.get("formulas", [])
        for f in formulas_list:
            name = (f.get("name") or "").strip()
            if len(name) < 2 or name in AMBIGUOUS_ENTITY_NAMES:
                continue
            aliases = [name]
            # Normalize variants like 五苓散 / 五苓散方
            if name.endswith(("汤", "散", "丸", "膏", "饮")):
                aliases.append(zhconv.convert(name, "zh-tw"))
            entities.append(
                {
                    "entity_id": f["id"],
                    "module": "formulas",
                    "kind": f.get("book", "经方"),
                    "label": name,
                    "terms": list(dict.fromkeys(_norm_simp(a) for a in aliases if len(_norm_simp(a)) >= 2)),
                    "priority": 100 + len(name) * 2,
                }
            )

    # 2. Bencao (385 herbs)
    raw_bencao = json.loads((DATA_DIR / "bencao" / "entries.json").read_text(encoding="utf-8"))
    bencao_list = raw_bencao if isinstance(raw_bencao, list) else raw_bencao.get("items", [])
    classical_herb_aliases = {
        "bencao:茈胡": ["柴胡"],
        "bencao:芎穷": ["川芎"],
        "bencao:瓜篓根": ["栝蒌根", "天花粉"],
        "bencao:檗木": ["黄柏", "黄檗"],
        "bencao:梅实": ["乌梅"],
        "bencao:署豫": ["薯蓣", "山药"],
        "bencao:茵陈": ["茵陈蒿"],
        "bencao:ch3-薤白": ["薤白"],
        "bencao:ch3-艾叶": ["艾叶"],
        "bencao:ch3-鸡子黄": ["鸡子黄"],
    }
    for h in bencao_list:
        name = (h.get("short_name") or h.get("name") or "").strip()
        if len(name) < 2 or name in AMBIGUOUS_ENTITY_NAMES:
            continue
        aliases = [name] + classical_herb_aliases.get(h["id"], [])
        # Only unambiguous 2+ char herb names cleanly match body text
        entities.append(
            {
                "entity_id": h["id"],
                "module": "bencao",
                "kind": h.get("grade") or "本草",
                "label": name,
                "terms": list(dict.fromkeys(_norm_simp(a) for a in aliases if len(_norm_simp(a)) >= 2)),
                "priority": 70 + len(name) * 2,
            }
        )

    # 3. Acupuncture Points (387), Meridians (15), Conditions (34)
    for pt in json.loads((DATA_DIR / "acupuncture" / "acupoints.json").read_text(encoding="utf-8")).get("items", []):
        name = (pt.get("canonical_name") or "").strip()
        if len(name) < 2 or name in AMBIGUOUS_ENTITY_NAMES:
            continue
        entities.append(
            {
                "entity_id": pt["id"],
                "module": "acupuncture",
                "kind": "穴位",
                "label": name,
                "terms": [_norm_simp(name)],
                "priority": 80 + len(name) * 2,
            }
        )
    for mer in json.loads((DATA_DIR / "acupuncture" / "meridians.json").read_text(encoding="utf-8")).get("items", []):
        name = (mer.get("canonical_name") or "").strip()
        if len(name) >= 3:
            entities.append(
                {
                    "entity_id": mer["id"],
                    "module": "acupuncture",
                    "kind": "经络",
                    "label": name,
                    "terms": [_norm_simp(name)],
                    "priority": 75 + len(name),
                }
            )

    # 4. Neijing Chapters (74)
    for ch in json.loads((DATA_DIR / "neijing" / "chapters.json").read_text(encoding="utf-8")).get("chapters", []):
        title = (ch.get("title") or "").strip()
        short = re.sub(r"^第[\u4e00-\u9fff\d]+篇\s*", "", title).strip()
        if len(short) < 3 or short in AMBIGUOUS_ENTITY_NAMES:
            continue
        entities.append(
            {
                "entity_id": ch["id"],
                "module": "neijing",
                "kind": "内经篇目",
                "label": title,
                "terms": [_norm_simp(short)],
                "priority": 85 + len(short),
            }
        )

    return entities


def _build_cross_links(catalog_books: list[dict[str, Any]], entities: list[dict[str, Any]]) -> dict[str, Any]:
    """Detect entities on every indexed book page and index reverse links per entity."""
    # Precompile combined regex over terms sorted longest-first to avoid partial shadows
    term_to_entities: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for ent in entities:
        for t in ent["terms"]:
            if len(t) >= 2:
                term_to_entities[t].append(ent)

    all_terms = sorted(term_to_entities.keys(), key=len, reverse=True)
    # Build single multi-alternation regex (safe up to a few thousand short strings in Python `re`)
    pattern = re.compile("|".join(re.escape(t) for t in all_terms))

    page_links: dict[str, list[dict[str, Any]]] = {}
    entity_refs_raw: dict[str, list[dict[str, Any]]] = defaultdict(list)

    shelf_rank = {"hantang_clinical": 1, "classical_companions": 2, "renji_core": 3}

    for book in catalog_books:
        if book["search_index_status"] != "indexed":
            continue
        book_id = book["book_id"]
        rows = _load_book_rows(book_id)
        for row in rows:
            stext = row.get("search_text") or ""
            body = row.get("body_text") or ""
            if not stext or not body:
                continue
            stext_cmp = re.sub(r"[\s「」『』《》【】〔〕]+", "", stext)
            found_terms = list(dict.fromkeys(pattern.findall(stext_cmp)))
            if not found_terms:
                continue

            page_ents: list[dict[str, Any]] = []
            seen_eid: set[str] = set()
            for term in found_terms:
                for ent in term_to_entities[term]:
                    eid = ent["entity_id"]
                    if eid in seen_eid:
                        continue
                    seen_eid.add(eid)
                    page_ents.append(
                        {
                            "entity_id": eid,
                            "module": ent["module"],
                            "kind": ent["kind"],
                            "label": ent["label"],
                            "matched_term": term,
                            "priority": ent["priority"],
                        }
                    )
                    # Build clean snippet around the matched term in verbatim body
                    idx = stext.find(term)
                    if idx < 0 and len(term) >= 2:
                        m_idx = re.search(r"[\s「」『』《》]*".join(re.escape(ch) for ch in term), stext)
                        idx = m_idx.start() if m_idx else 0
                    start = max(0, idx - 32)
                    end = min(len(body), idx + 64)
                    snippet = re.sub(r"\s+", " ", body[start:end]).strip()
                    snippet = re.sub(r"(?<=[\u4e00-\u9fff，。；：、！？])\s+(?=[\u4e00-\u9fff])", "", snippet)
                    entity_refs_raw[eid].append(
                        {
                            "book_id": book_id,
                            "book_title": book["short_title"],
                            "shelf": book["shelf"],
                            "tradition_layer": book["tradition_layer"],
                            "page_no": row["page_no"],
                            "unit_label": row["unit_label"],
                            "section_title": row.get("section_title", ""),
                            "snippet": snippet,
                            "text_sha256": row["text_sha256"],
                            "_rank": (shelf_rank.get(book["shelf"], 9), row["page_no"]),
                        }
                    )
            page_ents.sort(key=lambda x: (-x["priority"], x["entity_id"]))
            page_key = f"{book_id}:{row['page_no']}"
            page_links[page_key] = [{k: v for k, v in pe.items() if k != "priority"} for pe in page_ents[:24]]

    # Trim and deduplicate reverse links per entity: preserve top matches from each shelf!
    entity_refs: dict[str, list[dict[str, Any]]] = {}
    for eid, refs in entity_refs_raw.items():
        refs.sort(key=lambda r: r["_rank"])
        chosen: list[dict[str, Any]] = []
        per_book_cap: dict[str, int] = defaultdict(int)
        for r in refs:
            if per_book_cap[r["book_id"]] >= 3:
                continue
            per_book_cap[r["book_id"]] += 1
            chosen.append({k: v for k, v in r.items() if k != "_rank"})
            if len(chosen) >= 18:
                break
        entity_refs[eid] = chosen

    return {"page_links": page_links, "entity_refs": entity_refs}


# Stage 5A: 20 Core Cross-Classic Syndrome Clusters tying all 4 modules + Book Library
CLUSTER_SPECS: list[dict[str, Any]] = [
    {
        "id": "syndrome:taiyang-zhongfeng",
        "title": "太阳表虚中风证（营卫不和·桂枝汤群）",
        "keywords": ["太阳", "中风", "恶风", "发热", "汗出", "脉浮缓", "项强", "自汗"],
        "neijing_concept_ids": ["concept:nj:yin-yang-biao-li-han-re", "concept:nj:rebing-liujing-chuanbian"],
        "neijing_chapter_ids": ["nj:suwen:31", "nj:suwen:05"],
        "formula_ids": ["shanghan:桂枝汤", "shanghan:桂枝加葛根汤", "shanghan:桂枝加厚朴杏仁汤"],
        "bencao_ids": ["bencao:牡桂", "bencao:芍药", "bencao:甘草", "bencao:大枣"],
        "acupuncture_condition_ids": ["cond:ch6:s272"],
        "acupuncture_point_ids": ["acupoint:gb20:风池", "acupoint:lu07:列缺", "acupoint:li04:合谷"],
        "clinical_reasoning": "表气受风邪疏泄而营弱卫强，当调和营卫、解肌发汗，服粥温覆以助胃气蒸腾津液，忌峻发大汗。",
        "differentials": "有汗脉缓用桂枝汤；有汗项背强加葛根；兼微喘加厚朴杏仁；若无汗脉浮紧则转属麻黄汤表实证。",
        "version_conflicts": "历代对《本经》“牡桂/菌桂”对应现代桂枝与肉桂有文字变迁考证，人纪临证强调发散风寒解肌用桂枝、温肾阳下焦用肉桂。",
        "safety_note": "酒客忌甘味（桂枝汤禁酒客）；表热里实、脉数烦渴者禁用温辛解表剂。",
    },
    {
        "id": "syndrome:taiyang-shanghan-jing",
        "title": "太阳表实伤寒与项背强痉（麻黄/葛根汤群）",
        "keywords": ["伤寒", "无汗", "恶寒", "脉浮紧", "身疼", "腰痛", "骨节疼痛", "项背强", "麻黄"],
        "neijing_concept_ids": ["concept:nj:rebing-liujing-chuanbian", "concept:nj:ke-tong-bi-wei-bingji"],
        "neijing_chapter_ids": ["nj:suwen:31", "nj:suwen:35"],
        "formula_ids": ["shanghan:麻黄汤", "shanghan:葛根汤", "shanghan:大青龙汤"],
        "bencao_ids": ["bencao:麻黄", "bencao:牡桂", "bencao:杏核仁", "bencao:葛根"],
        "acupuncture_condition_ids": ["cond:ch6:头部与脑瘤治症"],
        "acupuncture_point_ids": ["acupoint:du14:大椎", "acupoint:gb20:风池", "acupoint:lu07:列缺", "acupoint:li04:合谷"],
        "clinical_reasoning": "寒邪束表、卫闭营郁，毛窍闭塞则无汗喘满；开肺腠以散外寒（麻黄），津不上输项背强则助阳明津液升达（葛根）。",
        "differentials": "纯粹恶寒无汗体痛用麻黄汤；兼项背强几几或下利用葛根汤；外寒无汗兼烦躁口渴用大青龙汤；咽喉干燥、淋家、疮家、衄家、亡血家皆禁麻黄发汗。",
        "version_conflicts": "《伤寒》表证严守“先去麻黄之煎沫”及中病即止；各家对麻黄生用/炙用及杏仁用量略异，按原书各立。",
        "safety_note": "亡血、阴虚、尺中脉微、心脏重度衰竭者严禁峻发汗，恐生亡阳戴阳变证。",
    },
    {
        "id": "syndrome:taiyang-xushui-wuling",
        "title": "太阳蓄水证与膀胱气化不利（五苓散群）",
        "keywords": ["蓄水", "小便不利", "渴欲饮水", "水逆", "水入即吐", "消渴", "浮肿", "五苓散"],
        "neijing_concept_ids": ["concept:nj:fengshui-shuinie-ni", "concept:nj:kaiguimen-shuiyurexue-cire"],
        "neijing_chapter_ids": ["nj:suwen:08", "nj:suwen:61"],
        "formula_ids": ["shanghan:五苓散", "jinkui:猪苓散", "shanghan:猪苓汤"],
        "bencao_ids": ["bencao:茯苓", "bencao:猪苓", "bencao:泽泻", "bencao:白术", "bencao:牡桂"],
        "acupuncture_condition_ids": ["cond:ch6:s284"],
        "acupuncture_point_ids": ["acupoint:ren04:关元", "acupoint:sp09:阴陵泉", "acupoint:st36:足三里"],
        "clinical_reasoning": "外邪循经入膀胱之腑致气化不行，水道壅滞则小便不利而上不承津故渴欲饮水，水停胃下则水入即吐（水逆）。",
        "differentials": "五苓散属太阳蓄水兼表（桂枝助阳化气、多饮暖水汗出愈）；猪苓汤属阴虚有热兼水停（配阿胶滑石育阴利水）；真武汤属少阴肾阳衰微水泛。",
        "version_conflicts": "《本经》原称“术”，后世分化白术、苍术；古方“五苓散”皆以方寸匕散服并多饮暖水，切不可改作水煎失其药势。",
        "safety_note": "若少腹急结如狂而小便自利者，属蓄血证（桃核承气/抵当汤），非本证。",
    },
    {
        "id": "syndrome:taiyang-xuxue-yuxue",
        "title": "太阳蓄血证与下焦瘀血血证（桃核承气/抵当/血证论互参）",
        "keywords": ["蓄血", "少腹急结", "少腹硬满", "小便自利", "发狂", "喜忘", "如狂", "瘀血", "便黑"],
        "neijing_concept_ids": ["concept:nj:jing-qi-shen-xue", "concept:nj:xushi-hanyin-yu-liujingjue"],
        "neijing_chapter_ids": ["nj:suwen:39", "nj:suwen:62"],
        "formula_ids": ["shanghan:桃核承气汤", "shanghan:抵当汤", "jinkui:下瘀血汤"],
        "bencao_ids": ["bencao:桃核仁", "bencao:大黄", "bencao:水蛭", "bencao:蜚虻"],
        "acupuncture_condition_ids": ["cond:ch6:s285", "cond:ch6:s282"],
        "acupuncture_point_ids": ["acupoint:sp10:血海", "acupoint:sp06:三阴交", "acupoint:bl40:委中"],
        "clinical_reasoning": "表邪化热与瘀血互结下焦胞宫/大肠之间，必验“小便自利”以别蓄水，佐“如狂、喜忘、屎黑”及少腹按之急结硬满；合参唐容川《血证论》消瘀为治血第一要法。",
        "differentials": "初结少腹急结、其人如狂（热多瘀微）用桃核承气；久结少腹硬满、发狂喜忘、脉沉结（瘀重热结）用抵当汤；妇人产后少腹刺痛用下瘀血汤。",
        "version_conflicts": "虫类破血药（水蛭、虻虫、蟅虫）生用与炒炙及现代药典替代标准历代争议较大，务必严核来源与炮制。",
        "safety_note": "高危警示：峻下逐瘀方严禁用于孕妇、经期误诊及内出血未止之休克急症！",
    },
    {
        "id": "syndrome:shaoyang-shuji",
        "title": "少阳枢机不利与热入血室（小柴胡/大柴胡群）",
        "keywords": ["少阳", "往来寒热", "胸胁苦满", "口苦", "咽干", "目眩", "心烦喜呕", "热入血室", "期门"],
        "neijing_concept_ids": ["concept:nj:san-yin-san-yang-kaihe", "concept:nj:hanre-nveji-wanglai"],
        "neijing_chapter_ids": ["nj:suwen:06", "nj:suwen:35"],
        "formula_ids": ["shanghan:小柴胡汤", "shanghan:大柴胡汤", "shanghan:柴胡桂枝汤", "shanghan:柴胡加龙骨牡蛎汤"],
        "bencao_ids": ["bencao:茈胡", "bencao:黄芩", "bencao:半夏", "bencao:人参", "bencao:大黄"],
        "acupuncture_condition_ids": ["cond:ch6:s279"],
        "acupuncture_point_ids": ["acupoint:lv14:期门", "acupoint:gb34:阳陵泉", "acupoint:sj05:外关", "acupoint:sj06:支沟"],
        "clinical_reasoning": "少阳主半表半里三焦胆腑枢机，正邪分争则往来寒热、胸胁苦满、默默不欲饮食、心烦喜呕；《伤寒》特明“但见一证便是，不必悉具”，经水适断之热入血室常配刺期门与小柴胡。",
        "differentials": "纯少阳枢机用小柴胡；兼表发热支节烦疼用柴胡桂枝汤；兼阳明腑实呕不止心下急用大柴胡汤；误下烦惊谵语用柴胡加龙骨牡蛎汤。",
        "version_conflicts": "柴胡用量（原方半斤约八两与现代临床剂量比例）及小柴胡加减七法去滓再煎规制极关药力。",
        "safety_note": "少阳禁汗、禁吐、禁纯下；切忌仅凭往来寒热误当作纯表寒滥用发汗。",
    },
    {
        "id": "syndrome:yangming-qire-baihu",
        "title": "阳明经分大热大渴（白虎/竹叶石膏群）",
        "keywords": ["阳明", "大热", "大汗", "大渴", "脉洪大", "白虎", "石膏", "烦渴", "燥热"],
        "neijing_concept_ids": ["concept:nj:taiyin-yangming-biaoli", "concept:nj:rebing-liujing-chuanbian"],
        "neijing_chapter_ids": ["nj:suwen:31", "nj:suwen:32"],
        "formula_ids": ["shanghan:白虎汤", "shanghan:白虎加人参汤", "shanghan:竹叶石膏汤"],
        "bencao_ids": ["bencao:石膏", "bencao:知母", "bencao:甘草"],
        "acupuncture_condition_ids": ["cond:ch6:s284"],
        "acupuncture_point_ids": ["acupoint:li11:曲池", "acupoint:li04:合谷", "acupoint:du14:大椎"],
        "clinical_reasoning": "邪传阳明气分，胃经实热充斥内外而无燥屎阻结，故大汗、大烦渴、脉洪大或滑而厥（热深厥深），取辛寒重剂石膏配知母直清阳明胃热。",
        "differentials": "大热脉洪无汗虚用白虎汤；大汗后大渴舌上干燥烦渴欲饮水数升用白虎加人参汤；病愈后余热未清气津两伤欲吐用竹叶石膏汤。",
        "version_conflicts": "仲景石膏以“鸡子大”碎绵裹煮，后世常误小用不敢过一两或误与阳明腑实混同。",
        "safety_note": "严防真寒假热（脉浮紧无汗、下利清谷）误投白虎汤致胃阳骤熄！须确认无表寒实证。",
    },
    {
        "id": "syndrome:yangming-fushi-chengqi",
        "title": "阳明腑实燥屎痞满（三承气/麻子仁丸群）",
        "keywords": ["阳明", "腑实", "潮热", "日晡", "谵语", "不大便", "燥屎", "痞满", "大便硬", "承气"],
        "neijing_concept_ids": ["concept:nj:taiyin-yangming-biaoli", "concept:nj:xushi-hanyin-yu-liujingjue"],
        "neijing_chapter_ids": ["nj:suwen:29", "nj:suwen:11"],
        "formula_ids": ["shanghan:大承气汤", "shanghan:小承气汤", "shanghan:调胃承气汤", "shanghan:麻子仁丸"],
        "bencao_ids": ["bencao:大黄", "bencao:朴消", "bencao:厚朴", "bencao:枳实", "bencao:甘草"],
        "acupuncture_condition_ids": ["cond:ch6:s285"],
        "acupuncture_point_ids": ["acupoint:st25:天枢", "acupoint:sj06:支沟", "acupoint:st36:足三里", "acupoint:li04:合谷"],
        "clinical_reasoning": "胃家实热与宿食津枯相搏成燥屎，治法首辨“痞、满、燥、实”四字轻重及煎煮先后（先煮枳朴还是大黄、芒硝溶服），急下存阴以保肾津胃液。",
        "differentials": "痞满燥实俱重（日晡潮热、谵语、转矢气、手足濈然汗出）用大承气；微烦满而未全燥用小承气（试与微和之）；燥实不痞满而胃热心烦用调胃承气；脾约大便坚小便数用麻子仁丸润下。",
        "version_conflicts": "“先煮厚朴枳实，后纳大黄，临服纳芒硝”煎法决定攻下部位之峻缓，不可一锅乱煮。",
        "safety_note": "高危警示：剧烈腹痛需先排外急腹症穿孔/肠梗阻绞窄！老弱虚秘及无燥屎者误攻大承气恐致脱阳下利不止。",
    },
    {
        "id": "syndrome:taiyin-xuhan-lizhong",
        "title": "太阴脾胃虚寒与中焦建中（理中/小建中/吴茱萸群）",
        "keywords": ["太阴", "腹满而吐", "食不下", "自利益甚", "时腹自痛", "理中", "虚寒", "喜温", "中焦"],
        "neijing_concept_ids": ["concept:nj:taiyin-yangming-biaoli", "concept:nj:wugu-weiyang-yinshi-jiankang"],
        "neijing_chapter_ids": ["nj:suwen:29", "nj:suwen:19"],
        "formula_ids": ["shanghan:理中丸", "shanghan:小建中汤", "jinkui:大建中汤"],
        "bencao_ids": ["bencao:干姜", "bencao:人参", "bencao:白术", "bencao:甘草", "bencao:牡桂"],
        "acupuncture_condition_ids": ["cond:ch6:s281", "cond:ch6:s283"],
        "acupuncture_point_ids": ["acupoint:ren12:中脘", "acupoint:st36:足三里", "acupoint:sp04:公孙", "acupoint:bl20:脾俞"],
        "clinical_reasoning": "脾家虚寒、中阳不运，腹满时痛、自利不渴、食不下、吐利交作；治以温中健脾、甘温建立中气，切忌寒凉苦泄误作胃实下之。",
        "differentials": "呕吐下利、寒多不用水用理中丸/汤；腹中急痛、喜温喜按、虚劳悸衄用小建中汤（倍芍药加饴糖）；心胸大寒痛呕不能饮食、腹中寒上冲皮起见头足用大建中汤。",
        "version_conflicts": "《伤寒》理中作丸以蜜和温水研服或作汤；《金匮》人参汤即理中汤而用主胸痹中虚之证，两书保留各自原注。",
        "safety_note": "若兼下利清谷、四肢厥冷、脉微欲绝者，已属太阴转少阴，单用理中力薄，当急转四逆汤类。",
    },
    {
        "id": "syndrome:shaoyin-hanhua-sini",
        "title": "少阴寒化亡阳四逆（四逆/真武/通脉四逆/附子汤群）",
        "keywords": ["少阴", "脉微细", "但欲寐", "四肢厥逆", "下利清谷", "恶寒", "亡阳", "附子", "背恶寒"],
        "neijing_concept_ids": ["concept:nj:yin-yang-gangji", "concept:nj:xushi-hanyin-yu-liujingjue"],
        "neijing_chapter_ids": ["nj:suwen:03", "nj:suwen:05"],
        "formula_ids": ["shanghan:四逆汤", "shanghan:通脉四逆汤", "shanghan:真武汤", "shanghan:附子汤"],
        "bencao_ids": ["bencao:附子", "bencao:干姜", "bencao:茯苓", "bencao:芍药", "bencao:人参"],
        "acupuncture_condition_ids": ["cond:ch6:s295"],
        "acupuncture_point_ids": ["acupoint:ren04:关元", "acupoint:ren06:气海", "acupoint:du04:命门", "acupoint:ki03:太溪"],
        "clinical_reasoning": "肾中真阳衰微、心火不温，见脉微细、但欲寐、背恶寒、下利清谷、手足厥逆；急以生附子温少阴肾阳、干姜温太阴脾阳，配灸关元气海回阳固脱。",
        "differentials": "回阳救逆第一方用四逆汤（生附子+干姜+炙草）；真阳格拒（身反不恶寒、面赤）用通脉四逆加葱白；少阴水气悸眩小便不利加茯苓芍药白术（真武汤，用炮附子）；骨节痛背恶寒脉沉（附子汤配人参炮附子）。",
        "version_conflicts": "生附子与炮附子之辨极为严格：《伤寒》《金匮》救逆回阳多用“生附子”，镇痛化水多用“炮附子”，煎煮久煎去毒是生死分界。",
        "safety_note": "高危警示：乌头/附子属强毒性剧药（含乌头碱），严禁自购生品试服！脉微欲绝属危重急症应立即急诊救治。",
    },
    {
        "id": "syndrome:shaoyin-rehua-xinfan",
        "title": "少阴热化心肾不交与懊憹不眠（黄连阿胶/栀子豉群）",
        "keywords": ["少阴", "心中烦", "不得卧", "心肾不交", "虚烦", "懊憹", "失眠", "黄连阿胶", "舌红"],
        "neijing_concept_ids": ["concept:nj:shier-guan-shenming", "concept:nj:wuzang-wushen-wuzou"],
        "neijing_chapter_ids": ["nj:suwen:08", "nj:suwen:46"],
        "formula_ids": ["shanghan:黄连阿胶汤", "shanghan:栀子豉汤", "shanghan:猪苓汤"],
        "bencao_ids": ["bencao:黄连", "bencao:黄芩", "bencao:阿胶", "bencao:栀子", "bencao:ch3-鸡子黄"],
        "acupuncture_condition_ids": ["cond:ch6:s273"],
        "acupuncture_point_ids": ["acupoint:ht07:神门", "acupoint:pc06:内关", "acupoint:ki03:太溪", "acupoint:sp06:三阴交"],
        "clinical_reasoning": "少阴肾水亏竭、君火亢炎而心肾不交（鸡子黄以血肉之情降君火、阿胶滋肾水、芩连直折心热），与胸膈郁热之栀子豉汤虚烦懊憹相对。",
        "differentials": "少阴病二三日以上心中烦不得卧（阴虚火亢、脉细数）用黄连阿胶汤（鸡子黄须待汤温后搅入）；汗吐下后虚烦不得眠、心中懊憹（无形郁热在胸膈）用栀子豉汤；兼小便不利渴欲饮水用猪苓汤。",
        "version_conflicts": "鸡子黄须待药液去滓微温时再纳搅匀以免煮熟结块失效；淡豆豉用黑豆制或青蒿香豉各家有考。",
        "safety_note": "少阴热化与寒化同见“但欲寐”或烦躁，若见手足逆冷脉微切不可误作阴虚清热。",
    },
    {
        "id": "syndrome:jueyin-wumei-hanre",
        "title": "厥阴寒热错杂与上热下寒（乌梅丸/当归四逆群）",
        "keywords": ["厥阴", "消渴", "气上撞心", "饥而不欲食", "食则吐蛔", "寒热错杂", "乌梅丸", "当归四逆", "血虚寒凝"],
        "neijing_concept_ids": ["concept:nj:yinyang-shengjiang-jieli", "concept:nj:san-yin-san-yang-kaihe"],
        "neijing_chapter_ids": ["nj:suwen:05", "nj:suwen:45"],
        "formula_ids": ["shanghan:乌梅丸", "shanghan:当归四逆汤", "shanghan:干姜黄连黄芩人参汤"],
        "bencao_ids": ["bencao:梅实", "bencao:细辛", "bencao:黄连", "bencao:蜀椒", "bencao:当归"],
        "acupuncture_condition_ids": ["cond:ch6:s284"],
        "acupuncture_point_ids": ["acupoint:lv03:太冲", "acupoint:pc06:内关", "acupoint:st36:足三里", "acupoint:ren04:关元"],
        "clinical_reasoning": "厥阴居两阴交尽而阳气初萌之位，最易现上热下寒、阴阳胜复、蛔厥或久利；当酸收苦降辛温并用（乌梅丸），若血虚肝寒四肢寒厥脉细则温养血脉（当归四逆）。",
        "differentials": "上热（烦呕消渴）与下寒（吐蛔久利）同见用乌梅丸；单纯血虚寒凝手足厥寒脉细欲绝用当归四逆汤（重用桂枝细辛通草当归）；寒格食入即吐用干姜黄芩黄连人参汤。",
        "version_conflicts": "细辛自古“不过钱”之争议与仲景原方大剂（《伤寒》《金匮》细辛入汤药多两计），现代临床需按法定毒理安全剂量严格甄别。",
        "safety_note": "高危警示：乌梅丸含附子、细辛，严禁自行超量；厥阴阴阳胜复需密切观测热复与厥脱变化。",
    },
    {
        "id": "syndrome:xiongbi-xintong",
        "title": "胸痹心痛短气（栝蒌薤白群与膻中巨阙）",
        "keywords": ["胸痹", "胸痛", "心痛彻背", "背痛彻心", "短气", "喘息", "不得卧", "心脏", "薤白", "栝蒌"],
        "neijing_concept_ids": ["concept:nj:shier-guan-shenming", "concept:nj:se-mai-he-can-yu-sizhen"],
        "neijing_chapter_ids": ["nj:suwen:03", "nj:suwen:22"],
        "formula_ids": ["jinkui:栝蒌薤白白酒汤", "jinkui:栝蒌薤白半夏汤", "jinkui:枳实薤白桂枝汤", "jinkui:乌头赤石脂丸"],
        "bencao_ids": ["bencao:瓜篓根", "bencao:ch3-薤白", "bencao:半夏", "bencao:牡桂", "bencao:枳实"],
        "acupuncture_condition_ids": ["cond:ch6:s276"],
        "acupuncture_point_ids": ["acupoint:pc06:内关", "acupoint:ren14:巨阙", "acupoint:ren17:膻中", "acupoint:bl15:心俞"],
        "clinical_reasoning": "《金匮》总纲“阳微阴弦”（上焦胸阳不振，下焦阴寒痰饮上逆），先以栝蒌涤痰开胸、薤白滑利通阳，佐酒气走窜（白酒/醪糟酒）；针刺内关、巨阙、膻中以宽胸行气。",
        "differentials": "喘息咳唾胸背痛短气用栝蒌薤白白酒汤；痰饮甚不得卧心痛彻背加半夏；气结胸胁逆抢心偏实者用枳实薤白桂枝汤、偏虚寒者用人参汤（理中）；背痛彻心手足冷甚者用乌头赤石脂丸。",
        "version_conflicts": "汉代“白酒”多指米酒/浊醪糟酿，非现代高浓度蒸馏烈酒（现代煎方或用黄酒、甜酒酿），且赤石脂乌头丸极寒阴证方可微丸试探。",
        "safety_note": "高危紧急警示：急性心痛彻背、压榨痛伴大汗手足厥冷属急性冠脉综合征/心梗极高危急症，必须立即拨打急救，不可延误！",
    },
    {
        "id": "syndrome:feike-tanyin-chuan",
        "title": "肺咳喘哮与寒饮射肺（小青龙/麻杏石甘/射干麻黄群）",
        "keywords": ["咳嗽", "喘", "哮喘", "痰多", "白痰", "黄痰", "喉中水鸡声", "不得卧", "小青龙", "肺胀"],
        "neijing_concept_ids": ["concept:nj:ke-tong-bi-wei-bingji", "concept:nj:fengshui-shuinie-ni"],
        "neijing_chapter_ids": ["nj:suwen:38", "nj:suwen:43"],
        "formula_ids": ["shanghan:小青龙汤", "shanghan:麻黄杏仁甘草石膏汤", "jinkui:射干麻黄汤", "jinkui:葶苈大枣泻肺汤"],
        "bencao_ids": ["bencao:麻黄", "bencao:半夏", "bencao:干姜", "bencao:细辛", "bencao:石膏"],
        "acupuncture_condition_ids": ["cond:ch6:s272", "cond:ch6:s275", "cond:ch6:s293"],
        "acupuncture_point_ids": ["acupoint:lu05:尺泽", "acupoint:lu07:列缺", "acupoint:bl13:肺俞", "acupoint:ren17:膻中"],
        "clinical_reasoning": "依《内经》“五脏六腑皆令人咳”与《金匮》痰饮咳嗽分寒饮、热郁、肺实壅塞三层：外寒内饮用小青龙（辛散温化加五味酸收防散）；肺热壅喘用麻杏石甘；肺水实喘不得卧用葶苈泻肺。",
        "differentials": "清稀白沫痰、不渴、脉弦或紧用小青龙汤；无恶寒、汗出、痰粘黄、口渴喘急用麻杏石甘汤；咳而上气喉中水鸡声用射干麻黄汤；胸胁支饮面肿不得平卧用葶苈大枣泻肺汤。",
        "version_conflicts": "《金匮》麻黄与石膏配比在麻杏石甘汤（1:2）、越婢汤（约1:1.3）、大青龙汤（1:鸡子大）各有微调，不可混为一谈。",
        "safety_note": "细辛、麻黄对高血压及心动过速患者高风险；急性呼吸困难发绀须立刻送医。",
    },
    {
        "id": "syndrome:shuizhong-shuiqi",
        "title": "水肿、水饮与十枣蓄饮（风水/石水/十枣/防己黄耆群）",
        "keywords": ["水肿", "浮肿", "脚肿", "积水", "悬饮", "支饮", "肺积水", "十枣汤", "风水", "黄耆"],
        "neijing_concept_ids": ["concept:nj:fengshui-shuinie-ni", "concept:nj:kaiguimen-shuiyurexue-cire"],
        "neijing_chapter_ids": ["nj:suwen:61", "nj:suwen:14"],
        "formula_ids": ["jinkui:防己黄耆汤", "jinkui:越婢汤", "shanghan:十枣汤", "jinkui:木防己汤"],
        "bencao_ids": ["bencao:黄耆", "bencao:防己", "bencao:大戟", "bencao:甘遂", "bencao:芫花"],
        "acupuncture_condition_ids": ["cond:ch6:s275", "cond:ch6:s278"],
        "acupuncture_point_ids": ["acupoint:sp09:阴陵泉", "acupoint:ren09:水分", "acupoint:st36:足三里", "acupoint:bl23:肾俞"],
        "clinical_reasoning": "遵循《内经》“开鬼门、洁净府、去宛陈莝”及《金匮》“腰以上肿当发汗、腰以下肿当利小便”；分别风水表实、表虚、阳虚及胸胁实质悬饮。",
        "differentials": "脉浮汗出恶风身重（气虚表虚水肿）用防己黄耆汤；恶风一身悉肿脉浮不渴（风水挟热）用越婢加术汤；咳唾引痛心下痞硬脉沉弦（胸肋悬饮实邪）用十枣汤；心下痞坚喘满面黧黑用木防己汤。",
        "version_conflicts": "十枣汤药材（甘遂、大戟、芫花）为剧毒峻下逐水药，古代且用“十枚肥大枣”护胃调和、平旦一服，现代切忌随意自煎加量；防己需严辨汉防己（粉防己）与木防己/广防己（马兜铃酸肾毒！）。",
        "safety_note": "极高危警示：广防己含马兜铃酸可致不可逆肾衰！甘遂大戟芫花为烈性毒药且反甘草（十枣无甘草），绝对禁止无监护个人试服！",
    },
    {
        "id": "syndrome:shixue-xuezheng",
        "title": "吐血衄血便血（泻心/柏叶/黄土汤 + 《血证论》互参）",
        "keywords": ["吐血", "鼻衄", "便血", "下血", "远血", "近血", "先便后血", "先血后便", "血证", "泻心汤"],
        "neijing_concept_ids": ["concept:nj:jing-qi-shen-xue", "concept:nj:pibu-luose-wuzangfengzhen"],
        "neijing_chapter_ids": ["nj:suwen:37", "nj:suwen:10"],
        "formula_ids": ["jinkui:泻心汤", "jinkui:黄土汤", "jinkui:柏叶汤", "jinkui:赤豆当归散"],
        "bencao_ids": ["bencao:大黄", "bencao:黄连", "bencao:干姜", "bencao:ch3-艾叶", "bencao:阿胶"],
        "acupuncture_condition_ids": ["cond:ch6:s282", "cond:ch6:s287"],
        "acupuncture_point_ids": ["acupoint:sp10:血海", "acupoint:bl17:膈俞", "acupoint:lu06:孔最", "acupoint:du20:百会"],
        "clinical_reasoning": "以《金匮·惊悸吐衄下血胸满瘀血病脉证治》辨阳亢迫血与阳虚不摄两途，深合唐容川《血证论》“止血、消瘀、宁血、补虚”四纲与“水火气血升降”。",
        "differentials": "心气不足吐血衄血（实属心胃伏火迫血妄行）用泻心汤（三黄汤）；吐血不止中寒不能摄血用柏叶汤；下血先便后血（远血、脾阳不统）用黄土汤（灶心黄土+附子白术阿胶黄芩）；先血后便（近血、湿热瘀肛）用赤小豆当归散。",
        "version_conflicts": "《金匮》“心气不足”各家历来多解为心胃阳热有余而真阴不足或热邪乘心，唐容川《血证论》对此有专篇折衷申明。",
        "safety_note": "高危警示：大口呕血、黑柏油便大量失血伴头晕休克为致命急症，立即就医止血输血！",
    },
    {
        "id": "syndrome:huangdan-shidu",
        "title": "黄疸湿热瘀热与谷酒女劳（茵陈蒿/栀子柏皮/硝石矾石群）",
        "keywords": ["黄疸", "发黄", "谷疸", "酒疸", "女劳疸", "身目黄", "茵陈", "肝胆", "胆结石"],
        "neijing_concept_ids": ["concept:nj:taiyin-yangming-biaoli", "concept:nj:wu-xing-sheng-ke"],
        "neijing_chapter_ids": ["nj:suwen:09", "nj:suwen:19"],
        "formula_ids": ["shanghan:茵陈蒿汤", "shanghan:栀子蘗皮汤", "jinkui:茵陈五苓散", "jinkui:硝石矾石散"],
        "bencao_ids": ["bencao:茵陈", "bencao:栀子", "bencao:大黄", "bencao:檗木"],
        "acupuncture_condition_ids": ["cond:ch6:s279"],
        "acupuncture_point_ids": ["acupoint:gb34:阳陵泉", "acupoint:bl18:肝俞", "acupoint:bl19:胆俞", "acupoint:lv03:太冲"],
        "clinical_reasoning": "《金匮》明“黄家所得，从湿得之”，兼看小便色白（虚）还是不利赤浊（湿热瘀），外散与清利小便并举，忌见黄即只用苦寒清肝。",
        "differentials": "但头汗出身无汗、小便不利、腹微满、阳明湿热瘀黄用茵陈蒿汤；湿热俱重无里实大便硬用栀子柏皮汤；湿重于热用茵陈五苓散；额上黑微汗出手足心热薄暮发（女劳疸挟瘀热）用硝石矾石散。",
        "version_conflicts": "硝石矾石散中芒硝/火硝（硝酸钾/硫酸钠）历代本草辨析极多，单用或配大麦粥汁有严格分量边界。",
        "safety_note": "剧烈黄疸伴高热寒战腹痛或意识障碍（重症胆管炎/肝衰征兆）须立即急诊医院排查胆道梗阻。",
    },
    {
        "id": "syndrome:xufan-shimian",
        "title": "虚烦失眠懊憹与脏躁百合（酸枣仁/甘麦大枣/百合地黄）",
        "keywords": ["失眠", "虚烦", "睡不着", "不得眠", "心悸", "百合", "脏躁", "酸枣仁", "多梦"],
        "neijing_concept_ids": ["concept:nj:shier-guan-shenming", "concept:nj:zhi-shen-daoyin-yanzhou"],
        "neijing_chapter_ids": ["nj:suwen:46", "nj:suwen:08"],
        "formula_ids": ["jinkui:酸枣仁汤", "jinkui:甘麦大枣汤", "jinkui:百合地黄汤"],
        "bencao_ids": ["bencao:酸枣", "bencao:知母", "bencao:茯苓", "bencao:芎穷", "bencao:百合"],
        "acupuncture_condition_ids": ["cond:ch6:s273", "cond:ch6:s296"],
        "acupuncture_point_ids": ["acupoint:ht07:神门", "acupoint:pc06:内关", "acupoint:sp06:三阴交", "acupoint:du20:百会"],
        "clinical_reasoning": "合《内经》“胃不和则卧不安”“得神者昌”与《金匮》血虚肝郁不眠、胸膈余热懊憹、肺心阴虚百合百脉一宗，分脏腑虚实温凉治神。",
        "differentials": "虚劳虚烦不得眠（肝血虚热不藏魂）用酸枣仁汤；欲眠不得眠、默默欲饮食复不能食、小便赤（阴虚内热）用百合地黄汤；妇人悲伤欲哭象如神灵所作数欠伸用甘麦大枣汤；胃中热郁心中懊憹用栀子豉汤。",
        "version_conflicts": "酸枣仁煎法《金匮》注明“先煮酸枣仁”以取其脂液有效成分，后世多误诸药同煎短煮。",
        "safety_note": "若伴胸痛气短夜间阵发性端坐呼吸，须先鉴别心衰夜喘而非普通失眠。",
    },
    {
        "id": "syndrome:xiaoke-pidan",
        "title": "消渴饮水与下消（白虎加人参/肾气丸 + 《石室秘录》）",
        "keywords": ["消渴", "糖尿病", "口渴", "饮一斗", "小便一斗", "上消", "中消", "下消", "肾气丸"],
        "neijing_concept_ids": ["concept:nj:qibing-xueku-xiaoke", "concept:nj:wugu-weiyang-yinshi-jiankang"],
        "neijing_chapter_ids": ["nj:suwen:47", "nj:suwen:03"],
        "formula_ids": ["shanghan:白虎加人参汤", "jinkui:肾气丸", "jinkui:栝蒌瞿麦丸"],
        "bencao_ids": ["bencao:干地黄", "bencao:署豫", "bencao:山茱萸", "bencao:石膏", "bencao:瓜篓根"],
        "acupuncture_condition_ids": ["cond:ch6:s284"],
        "acupuncture_point_ids": ["acupoint:bl23:肾俞", "acupoint:sp06:三阴交", "acupoint:ki03:太溪", "acupoint:st36:足三里"],
        "clinical_reasoning": "源自《素问》“脾瘅、消瘅”高粱厚味内热伤阴，接续《金匮·消渴篇》男子消渴小便反多、饮一斗小便一斗之肾阳蒸腾失约，并以《石室秘录》大补真阴壮水制火参究。",
        "differentials": "上中消肺胃燥热大渴欲饮冷水用白虎加人参汤；下消小便反多饮一斗小便一斗（阳气不能化水蒸津上承）用八味肾气丸；上燥下寒小便不利有水气用栝蒌瞿麦丸。",
        "version_conflicts": "《金匮》肾气丸原作“干地黄、桂枝、附子”，宋代改用肉桂熟地为后世八味地黄丸，人纪特别标出桂枝与肉桂入阴出阳之差异。",
        "safety_note": "现代临床糖尿病酮症酸中毒（深大呼吸、烂苹果味、意识模糊）属危重急症，应立即西医抢救不可延误。",
    },
    {
        "id": "syndrome:toutong-dianding",
        "title": "六经头痛、巅顶冷痛吐涎沫（吴茱萸/葛根/针灸经络分部）",
        "keywords": ["头痛", "偏头痛", "巅顶痛", "头疼", "前额痛", "后头痛", "干呕", "吐涎沫", "吴茱萸"],
        "neijing_concept_ids": ["concept:nj:wufeng-qijue-zhuanbian", "concept:nj:liujing-xueqi-shierpibu"],
        "neijing_chapter_ids": ["nj:suwen:42", "nj:suwen:31"],
        "formula_ids": ["shanghan:吴茱萸汤", "shanghan:葛根汤", "shanghan:小柴胡汤"],
        "bencao_ids": ["bencao:吴茱萸", "bencao:人参", "bencao:干姜", "bencao:芎穷", "bencao:细辛"],
        "acupuncture_condition_ids": ["cond:ch6:头部与脑瘤治症"],
        "acupuncture_point_ids": ["acupoint:du20:百会", "acupoint:gb20:风池", "acupoint:li04:合谷", "acupoint:lv03:太冲"],
        "clinical_reasoning": "结合《内经》六经循头部位辨证（前额阳明合谷/解溪、两侧少阳外关/率谷、后项太阳列缺/后溪、巅顶厥阴百会/太冲涌泉）与《伤寒》阳明食谷欲呕、厥阴干呕吐涎沫头痛之寒痰浊阴上逆。",
        "differentials": "胃寒食谷欲呕或厥阴寒极干呕吐涎沫头巅顶痛用吴茱萸汤；外感项背强痛用葛根汤/桂枝汤；少阳偏头胀痛口苦往来寒热用小柴胡汤。",
        "version_conflicts": "百会“四神聪”与远道配穴下针先后及吴茱萸汤“汤洗七遍”去苦辛烈性炮制极重要。",
        "safety_note": "极高危警示：突发剧烈“霹雳样”头痛伴呕吐、视物重影、意识改变或偏瘫（脑出血/卒中先兆）严禁延误或随意猛刺，立刻送急诊！",
    },
    {
        "id": "syndrome:fengshi-lijie",
        "title": "风湿历节关节痹痛（桂枝芍药知母/乌头汤/甘草附子）",
        "keywords": ["风湿", "历节", "关节痛", "膝痛", "膝盖冷", "身烦疼", "痛风", "肿如脱", "痹症"],
        "neijing_concept_ids": ["concept:nj:ke-tong-bi-wei-bingji", "concept:nj:wufang-yifa-fashi"],
        "neijing_chapter_ids": ["nj:suwen:43", "nj:suwen:44"],
        "formula_ids": ["jinkui:桂枝芍药知母汤", "jinkui:乌头汤", "jinkui:甘草附子汤", "jinkui:防己黄耆汤"],
        "bencao_ids": ["bencao:乌头", "bencao:附子", "bencao:知母", "bencao:牡桂", "bencao:防己"],
        "acupuncture_condition_ids": ["cond:ch6:s264"],
        "acupuncture_point_ids": ["acupoint:st36:足三里", "acupoint:gb34:阳陵泉", "acupoint:sp09:阴陵泉", "acupoint:bl40:委中"],
        "clinical_reasoning": "上承《素问·痹论》“风寒湿三气杂至合而为痹”，接《金匮·中风历节病》寒湿阻遏关节或郁而化热伤阴，以微汗渐解（切忌大汗只出风不出湿）与温通督阳。",
        "differentials": "诸肢节疼痛、身体尪羸、脚肿如脱、头眩短气（寒湿化热伤阴兼脾虚）用桂枝芍药知母汤；病历节不可屈伸疼痛（纯粹剧烈寒湿阴凝）用乌头汤；骨节掣痛不得屈伸近之则痛剧用甘草附子汤。",
        "version_conflicts": "《金匮》乌头汤用“蜜二升煎乌头一升减半去滓再入它药”，白蜜之解乌头毒与缓急止痛在原书中不可或缺，不可省蜜换糖！",
        "safety_note": "高危警示：川乌/草乌（乌头汤主药）属剧毒中药，煎不透必致口舌麻木心律失常窒息，严禁私自抓药煎服！",
    },
]


def _auto_find_cluster_library_refs(
    cluster: dict[str, Any],
    catalog_books: list[dict[str, Any]],
    loaded_books: dict[str, list[dict[str, Any]]],
    formula_names: list[str],
) -> list[dict[str, Any]]:
    """Find verbatim highest-relevance library quotes for a syndrome cluster across non-renji & renji books."""
    priority_books = [
        "ni-hantang-articles-cases-pdf",
        "ni-hantang-formulas-pdf",
        "tang-rongchuan-xuezhenglun-pdf",
        "shanghan-juyi-book-txt",
        "chen-shiduo-shishimilu-txt",
        "otsuka-shanghan-docx",
    ]
    book_meta = {b["book_id"]: b for b in catalog_books}
    terms = [_norm_simp(k) for k in cluster["keywords"] if len(k) >= 2]
    terms += [_norm_simp(n) for n in formula_names if len(n) >= 2]
    terms = list(dict.fromkeys(terms))

    refs: list[dict[str, Any]] = []
    for bid in priority_books:
        rows = loaded_books.get(bid, [])
        if not rows:
            continue
        best_row = None
        best_score = 0
        best_term = ""
        for r in rows:
            stext = r.get("search_text") or ""
            if not stext or len(r.get("body_text", "")) < 40:
                continue
            sc = 0
            top_term = ""
            for idx, t in enumerate(terms):
                if t in stext:
                    weight = 5 if t in formula_names else 2
                    sc += weight
                    if not top_term or weight > 2:
                        top_term = t
            if sc > best_score:
                best_score = sc
                best_row = r
                best_term = top_term
        if best_row and best_score >= 4:
            body = best_row["body_text"]
            stext = best_row["search_text"]
            pos = stext.find(best_term) if best_term else 0
            start = max(0, pos - 40)
            end = min(len(body), pos + 130)
            quote = re.sub(r"\s+", " ", body[start:end]).strip()
            bm = book_meta[bid]
            refs.append(
                {
                    "book_id": bid,
                    "book_title": bm["short_title"],
                    "shelf": bm["shelf"],
                    "tradition_layer": bm["tradition_layer"],
                    "page_no": best_row["page_no"],
                    "unit_label": best_row["unit_label"],
                    "section_title": best_row.get("section_title", ""),
                    "quote": quote,
                    "text_sha256": best_row["text_sha256"],
                    "score": best_score,
                }
            )
    refs.sort(key=lambda x: -x["score"])
    return refs[:5]


def main() -> None:
    LIB_DATA_DIR.mkdir(parents=True, exist_ok=True)
    REL_DATA_DIR.mkdir(parents=True, exist_ok=True)

    src_cat = json.loads((DATA_DIR / "source_catalog.json").read_text(encoding="utf-8"))
    src_by_id = {s["source_id"]: s for s in src_cat.get("sources", [])}

    # Verify ID sets upfront
    formula_by_id: dict[str, dict[str, Any]] = {}
    for fn_name in ("formulas.json", "jinkui_formulas.json"):
        raw_f = json.loads((DATA_DIR / fn_name).read_text(encoding="utf-8"))
        for f in (raw_f if isinstance(raw_f, list) else raw_f.get("formulas", [])):
            formula_by_id[f["id"]] = f
    raw_bencao = json.loads((DATA_DIR / "bencao" / "entries.json").read_text(encoding="utf-8"))
    bencao_ids = {h["id"] for h in (raw_bencao if isinstance(raw_bencao, list) else raw_bencao.get("items", []))}
    acu_cond_ids = {c["id"] for c in json.loads((DATA_DIR / "acupuncture" / "conditions.json").read_text(encoding="utf-8")).get("items", [])}
    acu_pt_ids = {p["id"] for p in json.loads((DATA_DIR / "acupuncture" / "acupoints.json").read_text(encoding="utf-8")).get("items", [])}
    nj_conc_ids = {c["id"] for c in json.loads((DATA_DIR / "neijing" / "concepts.json").read_text(encoding="utf-8")).get("items", [])}
    nj_ch_ids = {c["id"] for c in json.loads((DATA_DIR / "neijing" / "chapters.json").read_text(encoding="utf-8")).get("chapters", [])}

    # 1. Build Book Catalog
    catalog_books: list[dict[str, Any]] = []
    loaded_books: dict[str, list[dict[str, Any]]] = {}
    for entry in BOOK_REGISTRY:
        bid = entry["book_id"]
        rows = _load_book_rows(bid)
        loaded_books[bid] = rows
        src = src_by_id.get(bid, {})
        rel_path = src.get("relative_path", "")
        text_populated = sum(1 for r in rows if r.get("body_text"))
        is_scan_only = text_populated == 0
        chapters = _extract_chapters_from_jsonl(bid, rows) if not is_scan_only else []

        catalog_books.append(
            {
                **entry,
                "source_id": bid,
                "shelf_label": SHELF_META[entry["shelf"]]["label"],
                "file_format": Path(rel_path).suffix.lstrip(".").lower() or "pdf",
                "relative_path": rel_path,
                "sha256": src.get("sha256", ""),
                "total_units": len(rows),
                "text_units": text_populated,
                "unit_type": rows[0]["unit_type"] if rows else "pdf_page",
                "has_image_viewer": rel_path.lower().endswith(".pdf"),
                "search_index_status": "scan_browse_only" if is_scan_only else "indexed",
                "chapters": chapters,
            }
        )

    catalog_payload = {
        "schema_version": "5.0",
        "shelves": SHELF_META,
        "stats": {
            "total_books": len(catalog_books),
            "indexed_books": sum(1 for b in catalog_books if b["search_index_status"] == "indexed"),
            "scan_only_books": sum(1 for b in catalog_books if b["search_index_status"] == "scan_browse_only"),
            "total_units": sum(b["total_units"] for b in catalog_books),
            "total_text_units": sum(b["text_units"] for b in catalog_books),
        },
        "books": catalog_books,
    }
    (LIB_DATA_DIR / "catalog.json").write_text(json.dumps(catalog_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    # 2. Build Cross-Book Entity Links
    entities = _collect_entities()
    cross_links = _build_cross_links(catalog_books, entities)
    cross_payload = {
        "schema_version": "5.0",
        "stats": {
            "linked_pages": len(cross_links["page_links"]),
            "linked_entities": len(cross_links["entity_refs"]),
        },
        **cross_links,
    }
    (LIB_DATA_DIR / "cross_links.json").write_text(json.dumps(cross_payload, ensure_ascii=False) + "\n", encoding="utf-8")

    # 3. Build Stage 5A Syndrome Clusters & Unified Network
    clusters: list[dict[str, Any]] = []
    network_edges: list[dict[str, Any]] = []
    for raw_c in CLUSTER_SPECS:
        # Assert every referenced ID truly resolves in the compiled datasets!
        fids = [fid for fid in raw_c["formula_ids"] if fid in formula_by_id]
        bids = [bid for bid in raw_c["bencao_ids"] if bid in bencao_ids]
        acids = [cid for cid in raw_c["acupuncture_condition_ids"] if cid in acu_cond_ids]
        apids = [pid for pid in raw_c["acupuncture_point_ids"] if pid in acu_pt_ids]
        ncids = [nid for nid in raw_c["neijing_concept_ids"] if nid in nj_conc_ids]
        nchids = [chid for chid in raw_c["neijing_chapter_ids"] if chid in nj_ch_ids]

        assert len(fids) == len(raw_c["formula_ids"]), f"Broken formula ID in {raw_c['id']}: {set(raw_c['formula_ids']) - set(fids)}"
        assert len(bids) == len(raw_c["bencao_ids"]), f"Broken bencao ID in {raw_c['id']}: {set(raw_c['bencao_ids']) - set(bids)}"
        assert len(acids) == len(raw_c["acupuncture_condition_ids"]), f"Broken acu cond in {raw_c['id']}"
        assert len(apids) == len(raw_c["acupuncture_point_ids"]), f"Broken acu point in {raw_c['id']}: {set(raw_c['acupuncture_point_ids']) - set(apids)}"
        assert len(ncids) == len(raw_c["neijing_concept_ids"]), f"Broken nj concept in {raw_c['id']}"
        assert len(nchids) == len(raw_c["neijing_chapter_ids"]), f"Broken nj chapter in {raw_c['id']}: {set(raw_c['neijing_chapter_ids']) - set(nchids)}"

        fnames = [formula_by_id[fid]["name"] for fid in fids]
        lib_refs = _auto_find_cluster_library_refs(raw_c, catalog_books, loaded_books, fnames)
        clusters.append({**raw_c, "library_refs": lib_refs})

        for module, ids in (
            ("neijing_concept", ncids),
            ("neijing_chapter", nchids),
            ("formula", fids),
            ("bencao", bids),
            ("acupuncture_condition", acids),
            ("acupuncture_point", apids),
        ):
            for tid in ids:
                network_edges.append({"syndrome_id": raw_c["id"], "target_module": module, "target_id": tid})

    (REL_DATA_DIR / "syndrome_clusters.json").write_text(
        json.dumps({"schema_version": "5.0", "count": len(clusters), "items": clusters}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (REL_DATA_DIR / "unified_network.json").write_text(
        json.dumps({"schema_version": "5.0", "edge_count": len(network_edges), "edges": network_edges}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Library catalog built: {len(catalog_books)} books, {len(cross_links['page_links'])} linked pages, {len(cross_links['entity_refs'])} linked entities.")
    print(f"Stage 5A syndrome network built: {len(clusters)} syndromes, {len(network_edges)} verified cross-module edges.")


if __name__ == "__main__":
    main()
