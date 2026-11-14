"""Deterministic Traditional/Simplified-aware search index across 15 digitized books & 4 modules."""
from __future__ import annotations

from functools import lru_cache
import json
from pathlib import Path
import re
from typing import Any

from retrieval.t2s_table import T2S_TRANS


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
LIB_SOURCES_DIR = ROOT / "sources" / "library"


_CJK_VARIANT_TRANS = str.maketrans({
    "\u3127": "一",
    "\uf9e7": "里",
    "裏": "里",
    "臓": "脏",
    "悪": "恶",
    "渇": "渴",
    "発": "发",
    "圧": "压",
    "気": "气",
    "薬": "药",
    "醫": "医",
    "證": "证",
    "脈": "脉",
    "癥": "症",
    "臍": "脐",
    "處": "处",
    "麥": "麦",
    "齋": "斋",
    "乾": "干",
    "髮": "发",
    "髪": "发",
    "朮": "术",
    "後": "后",
    "於": "于",
})


def norm_simp(text: str) -> str:
    simp = (text or "").translate(T2S_TRANS).translate(_CJK_VARIANT_TRANS)
    return re.sub(r"\s+", " ", simp).strip().lower()


_QUOTE_WS_RE = re.compile(r"[\s「」『』《》【】〔〕“”‘’\"<>〈〉]+")


def compact_cjk(text: str) -> str:
    """Strip whitespace and classic quotation brackets so line wraps & quotes do not break CJK phrase lookup."""
    return _QUOTE_WS_RE.sub("", norm_simp(text))


def _split_primary_terms(q: str) -> list[str]:
    cleaned = norm_simp(q)
    raw = [t.strip() for t in re.split(r"[\s,，、；;：:。！？!?\-\/]+", cleaned) if t.strip()]
    tokens: list[str] = []
    seen: set[str] = set()
    for part in raw:
        if part not in seen:
            seen.add(part)
            tokens.append(part)
    return tokens[:14]


def tokenize_query(q: str) -> list[str]:
    """Tokenize queries for structured entity/syndrome matching (includes 2-char subtokens for prose questions)."""
    tokens = _split_primary_terms(q)
    seen = set(tokens)
    for part in list(tokens):
        if len(part) >= 5 and re.fullmatch(r"[\u4e00-\u9fff]+", part):
            for i in range(0, len(part) - 1, 2):
                bg = part[i : i + 2]
                if bg not in seen:
                    seen.add(bg)
                    tokens.append(bg)
    return tokens[:14]


def _fallback_subtokens(primary: list[str]) -> list[str]:
    """Generate auxiliary 2-char subtokens ONLY when strict phrase/AND search yields zero hits."""
    subs: list[str] = []
    seen: set[str] = set()
    for part in primary:
        if part not in seen:
            seen.add(part)
            subs.append(part)
        if len(part) >= 4 and re.fullmatch(r"[\u4e00-\u9fff]+", part):
            for i in range(0, len(part) - 1, 2):
                bg = part[i : i + 2]
                if bg not in seen:
                    seen.add(bg)
                    subs.append(bg)
    return subs[:14]


@lru_cache(maxsize=1)
def _catalog_books() -> dict[str, dict[str, Any]]:
    cat = json.loads((DATA_DIR / "library" / "catalog.json").read_text(encoding="utf-8"))
    return {b["book_id"]: b for b in cat.get("books", [])}


@lru_cache(maxsize=1)
def _cross_links() -> dict[str, Any]:
    return json.loads((DATA_DIR / "library" / "cross_links.json").read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def _indexed_pages() -> list[dict[str, Any]]:
    books = _catalog_books()
    rows: list[dict[str, Any]] = []
    for bid, meta in books.items():
        if meta.get("search_index_status") != "indexed":
            continue
        jsonl_path = LIB_SOURCES_DIR / f"{bid}.jsonl"
        if not jsonl_path.exists():
            continue
        for raw_ln in jsonl_path.read_text(encoding="utf-8").splitlines():
            if not raw_ln.strip():
                continue
            r = json.loads(raw_ln)
            body = r.get("body_text") or ""
            if not body:
                continue
            st = norm_simp(r.get("search_text") or body)
            sec = norm_simp(r.get("section_title") or "")
            r["_stext_lower"] = st
            r["_stext_compact"] = _QUOTE_WS_RE.sub("", st)
            r["_sec_lower"] = sec
            r["_sec_compact"] = _QUOTE_WS_RE.sub("", sec)
            r["_title"] = meta["short_title"]
            r["_full_title"] = meta["title"]
            r["_shelf"] = meta["shelf"]
            r["_shelf_label"] = meta["shelf_label"]
            r["_tradition_layer"] = meta["tradition_layer"]
            rows.append(r)
    return rows


def _locate_in_body(body: str, tok: str) -> int:
    """Locate simplified/variant token in raw Traditional/wrapped body text by character span."""
    if not tok:
        return -1
    # Map body char index cleanly via translated/simplified characters (strict 1:1 index alignment)
    simp_chars = body.translate(T2S_TRANS).translate(_CJK_VARIANT_TRANS).lower()
    pos = simp_chars.find(tok)
    if pos >= 0:
        return pos
    # Fallback allowing arbitrary whitespace/newlines and quotation brackets inside CJK token
    compact_tok = _QUOTE_WS_RE.sub("", tok)
    if len(compact_tok) >= 2:
        pat = r"[\s「」『』《》【】〔〕“”‘’\"<>〈〉]*".join(re.escape(ch) for ch in compact_tok)
        m = re.search(pat, simp_chars)
        if m:
            return m.start()
    return -1


def _make_snippet(body: str, stext_lower: str, matched_tokens: list[str]) -> str:
    pos = -1
    for tok in sorted(matched_tokens, key=len, reverse=True):
        pos = _locate_in_body(body, tok)
        if pos >= 0:
            break
    if pos < 0:
        pos = 0
    start = max(0, pos - 36)
    end = min(len(body), pos + 148)
    snip = re.sub(r"\s+", " ", body[start:end]).strip()
    snip = re.sub(r"(?<=[\u4e00-\u9fff，。；：、！？「」『』（）])\s+(?=[\u4e00-\u9fff「」『』（）])", "", snip)
    if start > 0:
        snip = "…" + snip
    if end < len(body):
        snip = snip + "…"
    return snip


def search_library_pages(
    q: str = "",
    shelf: str = "",
    book_id: str = "",
    limit: int = 36,
) -> dict[str, Any]:
    """Full-text ranked search across digitized books (exact/AND first; partial sub-token fallback only on zero hits)."""
    cleaned = norm_simp(q)
    cleaned_cmp = compact_cjk(q)
    tokens = _split_primary_terms(q)
    books = _catalog_books()
    cross = _cross_links()
    page_links_map = cross.get("page_links", {})

    if not cleaned:
        return {
            "query": q,
            "tokens": [],
            "total": 0,
            "exact_total": 0,
            "fallback_used": False,
            "scan_only_notice": [
                b["short_title"] for b in books.values() if b["search_index_status"] == "scan_browse_only"
            ],
            "items": [],
        }

    primary_cmp = [compact_cjk(t) for t in tokens if compact_cjk(t)]
    scored: list[tuple[int, int, str, dict[str, Any]]] = []
    shelf_bonus = {"hantang_clinical": 4, "renji_core": 3, "classical_companions": 2}
    exact_count = 0

    candidates = [
        row for row in _indexed_pages()
        if (not shelf or row["_shelf"] == shelf) and (not book_id or row["book_id"] == book_id)
    ]

    for row in candidates:
        st_cmp = row["_stext_compact"]
        sec_cmp = row["_sec_compact"]
        combined_cmp = sec_cmp + "\n" + st_cmp
        if not primary_cmp or not all(p in combined_cmp for p in primary_cmp):
            continue

        hits: list[str] = []
        sc = 0
        for p_raw, p_c in zip(tokens, primary_cmp):
            in_sec = p_c in sec_cmp
            freq = min(combined_cmp.count(p_c), 8)
            hits.append(p_raw)
            sc += 18 * max(1, min(len(p_c), 8)) + freq * 4
            if in_sec:
                sc += 28
        is_exact = bool(cleaned_cmp and (cleaned_cmp in combined_cmp))
        if is_exact:
            exact_count += 1
            sc += 120 if len(cleaned_cmp) >= 3 else 40
            if cleaned_cmp in sec_cmp:
                sc += 50
            match_kind = "exact_phrase"
        else:
            match_kind = "all_terms"
        sc += shelf_bonus.get(row["_shelf"], 0)
        pk = f"{row['book_id']}:{row['page_no']}"
        scored.append(
            (
                sc,
                len(hits),
                row["book_id"],
                {
                    "book_id": row["book_id"],
                    "book_title": row["_title"],
                    "book_full_title": row["_full_title"],
                    "shelf": row["_shelf"],
                    "shelf_label": row["_shelf_label"],
                    "tradition_layer": row["_tradition_layer"],
                    "page_no": row["page_no"],
                    "unit_label": row["unit_label"],
                    "section_title": row.get("section_title", ""),
                    "snippet": _make_snippet(row["body_text"], row["_stext_lower"], [cleaned_cmp] if is_exact else hits),
                    "matched_tokens": hits[:6],
                    "match_kind": match_kind,
                    "text_sha256": row["text_sha256"],
                    "entity_links": page_links_map.get(pk, [])[:8],
                    "score": sc,
                },
            )
        )

    fallback_used = False
    if not scored:
        sub_tokens = _fallback_subtokens(primary_cmp)
        if sub_tokens:
            fallback_used = True
            for row in candidates:
                st_cmp = row["_stext_compact"]
                sec_cmp = row["_sec_compact"]
                combined_cmp = sec_cmp + "\n" + st_cmp
                hits = [tok for tok in sub_tokens if tok in combined_cmp]
                if not hits:
                    continue
                sc = sum(8 * len(t) + (12 if t in sec_cmp else 0) for t in hits) + shelf_bonus.get(row["_shelf"], 0)
                pk = f"{row['book_id']}:{row['page_no']}"
                scored.append(
                    (
                        sc,
                        len(hits),
                        row["book_id"],
                        {
                            "book_id": row["book_id"],
                            "book_title": row["_title"],
                            "book_full_title": row["_full_title"],
                            "shelf": row["_shelf"],
                            "shelf_label": row["_shelf_label"],
                            "tradition_layer": row["_tradition_layer"],
                            "page_no": row["page_no"],
                            "unit_label": row["unit_label"],
                            "section_title": row.get("section_title", ""),
                            "snippet": _make_snippet(row["body_text"], row["_stext_lower"], hits),
                            "matched_tokens": hits[:6],
                            "match_kind": "partial_fallback",
                            "text_sha256": row["text_sha256"],
                            "entity_links": page_links_map.get(pk, [])[:8],
                            "score": sc,
                        },
                    )
                )

    scored.sort(key=lambda x: (-x[0], -x[1], x[2], x[3]["page_no"]))
    per_cap = limit if (book_id or len(scored) <= limit) else 12
    items: list[dict[str, Any]] = []
    per_book: dict[str, int] = {}
    for _, _, bid, item in scored:
        if per_book.get(bid, 0) >= per_cap:
            continue
        per_book[bid] = per_book.get(bid, 0) + 1
        items.append(item)
        if len(items) >= limit:
            break

    return {
        "query": q,
        "tokens": tokens,
        "total": len(scored),
        "exact_total": exact_count,
        "fallback_used": fallback_used,
        "scan_only_notice": [
            b["short_title"] for b in books.values() if b["search_index_status"] == "scan_browse_only"
        ],
        "items": items,
    }


def _flatten_str(val: Any) -> str:
    if val is None:
        return ""
    if isinstance(val, str):
        return val
    if isinstance(val, dict):
        return " ".join(_flatten_str(v) for v in val.values())
    if isinstance(val, (list, tuple)):
        return " ".join(_flatten_str(v) for v in val)
    return str(val)


@lru_cache(maxsize=1)
def _structured_entities() -> list[dict[str, Any]]:
    entities: list[dict[str, Any]] = []

    for fn in ("formulas.json", "jinkui_formulas.json"):
        raw = json.loads((DATA_DIR / fn).read_text(encoding="utf-8"))
        for f in raw:
            blob = " ".join(
                [
                    f.get("name", ""),
                    f.get("book", ""),
                    f.get("six_meridian", ""),
                    f.get("indication", ""),
                    _flatten_str(f.get("ingredients", [])),
                ]
            )
            entities.append(
                {
                    "entity_id": f["id"],
                    "module": "formulas",
                    "module_label": "经方",
                    "title": f["name"],
                    "subtitle": f"{f.get('book', '')} · {f.get('six_meridian') or f.get('chapter') or ''}",
                    "summary": (f.get("indication") or "")[:120],
                    "_blob": norm_simp(blob),
                }
            )

    for h in json.loads((DATA_DIR / "bencao" / "entries.json").read_text(encoding="utf-8")):
        blob = " ".join(
            [
                h.get("name", ""),
                h.get("short_name", ""),
                _flatten_str(h.get("classic_indications", "")),
                _flatten_str(h.get("classic_properties", "")),
                _flatten_str(h.get("ni_summary", "")),
            ]
        )
        entities.append(
            {
                "entity_id": h["id"],
                "module": "bencao",
                "module_label": "神农本草",
                "title": h.get("short_name") or h["name"],
                "subtitle": f"{h.get('grade', '')} · {_flatten_str(h.get('classic_properties', ''))[:24]}",
                "summary": (_flatten_str(h.get("ni_summary")) or _flatten_str(h.get("classic_indications")))[:120],
                "_blob": norm_simp(blob),
            }
        )

    for p in json.loads((DATA_DIR / "acupuncture" / "acupoints.json").read_text(encoding="utf-8")).get("items", []):
        blob = " ".join([p.get("canonical_name", ""), _flatten_str(p.get("indications", [])), _flatten_str(p.get("summary", ""))])
        entities.append(
            {
                "entity_id": p["id"],
                "module": "acupuncture",
                "module_label": "针灸穴位",
                "title": p["canonical_name"],
                "subtitle": p.get("meridian_name") or "穴位",
                "summary": (_flatten_str(p.get("summary")) or _flatten_str(p.get("indications", [])[:3]))[:120],
                "_blob": norm_simp(blob),
            }
        )

    for c in json.loads((DATA_DIR / "neijing" / "concepts.json").read_text(encoding="utf-8")).get("items", []):
        blob = " ".join([c.get("canonical_name", ""), c.get("summary", ""), c.get("clinical_relevance", "")])
        entities.append(
            {
                "entity_id": c["id"],
                "module": "neijing",
                "module_label": "黄帝内经",
                "title": c["canonical_name"],
                "subtitle": c.get("submodule", "内经专题"),
                "summary": (c.get("summary") or "")[:120],
                "_blob": norm_simp(blob),
            }
        )

    return entities


def search_all_knowledge(q: str = "", limit: int = 24) -> list[dict[str, Any]]:
    """Search structured knowledge records across all 4 modules simultaneously."""
    cleaned = norm_simp(q)
    tokens = tokenize_query(q)
    if not tokens:
        return []
    scored: list[tuple[int, dict[str, Any]]] = []
    for ent in _structured_entities():
        blob = ent["_blob"]
        title_l = norm_simp(ent["title"])
        sc = 0
        for tok in tokens:
            if tok in title_l:
                sc += 25
            elif tok in blob:
                sc += 5
        if cleaned in title_l:
            sc += 40
        if sc > 0:
            scored.append((sc, {k: v for k, v in ent.items() if k != "_blob"}))
    scored.sort(key=lambda x: (-x[0], x[1]["module"], x[1]["entity_id"]))
    return [item for _, item in scored[:limit]]
