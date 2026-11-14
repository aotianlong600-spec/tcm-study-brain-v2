"""Stage 5 Book Library catalog, page reader, PDF image renderer & bidirectional entity links."""
from __future__ import annotations

from functools import lru_cache
import json
from pathlib import Path
from typing import Any

from retrieval.index import compact_cjk, norm_simp, search_library_pages


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
LIB_SOURCES_DIR = ROOT / "sources" / "library"
IMAGE_CACHE_DIR = DATA_DIR / "library" / "page_images"


@lru_cache(maxsize=1)
def _catalog() -> dict[str, Any]:
    return json.loads((DATA_DIR / "library" / "catalog.json").read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def _books_by_id() -> dict[str, dict[str, Any]]:
    return {b["book_id"]: b for b in _catalog().get("books", [])}


@lru_cache(maxsize=1)
def _cross_links() -> dict[str, Any]:
    return json.loads((DATA_DIR / "library" / "cross_links.json").read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def _syndrome_clusters() -> list[dict[str, Any]]:
    return json.loads((DATA_DIR / "relations" / "syndrome_clusters.json").read_text(encoding="utf-8")).get("items", [])


@lru_cache(maxsize=20)
def _book_pages(book_id: str) -> list[dict[str, Any]]:
    path = LIB_SOURCES_DIR / f"{book_id}.jsonl"
    if not path.exists():
        return []
    return [json.loads(ln) for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]


def overview() -> dict[str, Any]:
    cat = _catalog()
    books = cat.get("books", [])
    shelves = []
    for key, meta in sorted(cat.get("shelves", {}).items(), key=lambda x: x[1]["order"]):
        s_books = [b for b in books if b["shelf"] == key]
        shelves.append({"key": key, **meta, "book_count": len(s_books)})
    cross = _cross_links()
    return {
        "stats": {
            **cat.get("stats", {}),
            "linked_pages": len(cross.get("page_links", {})),
            "linked_entities": len(cross.get("entity_refs", {})),
        },
        "shelves": shelves,
    }


def list_books(shelf: str = "", q: str = "") -> dict[str, Any]:
    books = _catalog().get("books", [])
    nq = norm_simp(q)
    out = []
    for b in books:
        if shelf and b["shelf"] != shelf:
            continue
        if nq:
            blob = norm_simp(" ".join([b["title"], b["short_title"], b["author_era"], b["description"]]))
            if nq not in blob:
                continue
        out.append(
            {
                "book_id": b["book_id"],
                "title": b["title"],
                "short_title": b["short_title"],
                "author_era": b["author_era"],
                "shelf": b["shelf"],
                "shelf_label": b["shelf_label"],
                "file_format": b["file_format"],
                "total_units": b["total_units"],
                "text_units": b["text_units"],
                "has_image_viewer": b["has_image_viewer"],
                "search_index_status": b["search_index_status"],
                "tradition_layer": b["tradition_layer"],
                "module_affinities": b["module_affinities"],
                "chapter_count": len(b.get("chapters", [])),
                "description": b["description"],
            }
        )
    return {"total": len(out), "items": out}


def get_book(book_id: str) -> dict[str, Any] | None:
    meta = _books_by_id().get(book_id)
    if not meta:
        return None
    pages = _book_pages(book_id)
    page_links = _cross_links().get("page_links", {})
    linked_count = sum(1 for p in pages if f"{book_id}:{p['page_no']}" in page_links)

    # Top mentioned entities across this book
    entity_counts: dict[str, dict[str, Any]] = {}
    for p in pages:
        for lk in page_links.get(f"{book_id}:{p['page_no']}", []):
            eid = lk["entity_id"]
            if eid not in entity_counts:
                entity_counts[eid] = {**lk, "mentions": 0, "first_page": p["page_no"]}
            entity_counts[eid]["mentions"] += 1
    top_entities = sorted(entity_counts.values(), key=lambda x: (-x["mentions"], x["first_page"]))[:24]

    return {
        **meta,
        "linked_page_count": linked_count,
        "top_entities": top_entities,
        "preview_pages": [
            {
                "page_no": p["page_no"],
                "unit_label": p["unit_label"],
                "section_title": p.get("section_title", ""),
                "ocr_status": p.get("ocr_status", ""),
                "link_count": len(page_links.get(f"{book_id}:{p['page_no']}", [])),
                "preview": (p.get("body_text") or "")[:90],
            }
            for p in pages[:60]
        ],
    }


def list_book_pages(book_id: str, q: str = "", offset: int = 0, limit: int = 60) -> dict[str, Any] | None:
    meta = _books_by_id().get(book_id)
    if not meta:
        return None
    pages = _book_pages(book_id)
    page_links = _cross_links().get("page_links", {})
    if q.strip():
        nq = norm_simp(q)
        nq_cmp = compact_cjk(q)
        filtered = [
            p for p in pages
            if nq in norm_simp(p.get("search_text") or p.get("body_text") or "")
            or nq in norm_simp(p.get("section_title", ""))
            or (
                nq_cmp
                and (
                    nq_cmp in compact_cjk(p.get("search_text") or p.get("body_text") or "")
                    or nq_cmp in compact_cjk(p.get("section_title", ""))
                )
            )
        ]
    else:
        filtered = pages
    sliced = filtered[offset : offset + limit]
    return {
        "book_id": book_id,
        "book_title": meta["short_title"],
        "search_index_status": meta["search_index_status"],
        "total": len(filtered),
        "offset": offset,
        "items": [
            {
                "page_no": p["page_no"],
                "unit_label": p["unit_label"],
                "section_title": p.get("section_title", ""),
                "ocr_status": p.get("ocr_status", ""),
                "link_count": len(page_links.get(f"{book_id}:{p['page_no']}", [])),
                "preview": (p.get("body_text") or "")[:100] or meta["description"][:70],
            }
            for p in sliced
        ],
    }


def get_book_page(book_id: str, page_no: int) -> dict[str, Any] | None:
    meta = _books_by_id().get(book_id)
    if not meta:
        return None
    pages = _book_pages(book_id)
    if page_no < 1 or page_no > len(pages):
        return None
    row = pages[page_no - 1]
    pk = f"{book_id}:{page_no}"
    links = _cross_links().get("page_links", {}).get(pk, [])
    has_img = meta["has_image_viewer"]
    return {
        "book_id": book_id,
        "book_title": meta["short_title"],
        "book_full_title": meta["title"],
        "shelf": meta["shelf"],
        "shelf_label": meta["shelf_label"],
        "tradition_layer": meta["tradition_layer"],
        "search_index_status": meta["search_index_status"],
        "page_no": page_no,
        "total_units": len(pages),
        "prev_page": page_no - 1 if page_no > 1 else None,
        "next_page": page_no + 1 if page_no < len(pages) else None,
        "unit_type": row["unit_type"],
        "unit_label": row["unit_label"],
        "printed_page": row.get("printed_page"),
        "section_title": row.get("section_title", ""),
        "headings": row.get("headings", []),
        "body_text": row.get("body_text", ""),
        "text_sha256": row.get("text_sha256", ""),
        "extraction_method": row.get("extraction_method", ""),
        "ocr_status": row.get("ocr_status", ""),
        "has_image_viewer": has_img,
        "image_url": f"/api/library/books/{book_id}/pages/{page_no}/image" if has_img else None,
        "entity_links": links,
    }


def render_book_page_image(book_id: str, page_no: int) -> Path | None:
    meta = _books_by_id().get(book_id)
    if not meta or not meta.get("has_image_viewer"):
        return None
    if page_no < 1 or page_no > meta["total_units"]:
        return None
    out_dir = IMAGE_CACHE_DIR / book_id
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"page_{page_no:04d}.png"
    if out_path.exists():
        return out_path
    pdf_path = ROOT / meta["relative_path"]
    if not pdf_path.exists():
        return None
    try:
        import pypdfium2 as pdfium  # noqa: PLC0415
    except ImportError:
        return None
    doc = pdfium.PdfDocument(str(pdf_path))
    try:
        page = doc[page_no - 1]
        bitmap = page.render(scale=1.75)
        pil_img = bitmap.to_pil()
        pil_img.save(out_path, format="PNG")
    finally:
        doc.close()
    return out_path


def get_entity_links(entity_id: str) -> dict[str, Any]:
    """Return all book references AND Stage 5A syndrome clusters connected to any entity across all 4 modules."""
    refs = _cross_links().get("entity_refs", {}).get(entity_id, [])
    syndromes = []
    for sc in _syndrome_clusters():
        all_ids = (
            sc.get("formula_ids", [])
            + sc.get("bencao_ids", [])
            + sc.get("acupuncture_condition_ids", [])
            + sc.get("acupuncture_point_ids", [])
            + sc.get("neijing_concept_ids", [])
            + sc.get("neijing_chapter_ids", [])
        )
        if entity_id in all_ids:
            syndromes.append({"id": sc["id"], "title": sc["title"], "clinical_reasoning": sc["clinical_reasoning"]})
    return {
        "entity_id": entity_id,
        "library_ref_count": len(refs),
        "library_refs": refs,
        "related_syndromes": syndromes,
    }


def search(q: str = "", shelf: str = "", book_id: str = "", limit: int = 36) -> dict[str, Any]:
    return search_library_pages(q=q, shelf=shelf, book_id=book_id, limit=limit)
