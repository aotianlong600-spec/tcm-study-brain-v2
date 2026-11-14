"""FastAPI entry point for the local formula module."""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from . import (
    acupuncture_catalog,
    acupuncture_diagnose,
    bencao_catalog,
    catalog,
    formula_diagnose,
    formula_extras,
    hantang_catalog,
    library_catalog,
    neijing_catalog,
    stage5_service,
    syndrome_composer,
)
from ai import grounded_study


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web"

app = FastAPI(title="中医学习大脑 · 针灸 / 本草 / 内经 / 经方 / 辨证与书库")


@app.get("/api/health")
def health():
    return {"status": "ok", "module": "formula"}


@app.get("/api/overview")
def overview():
    payload = catalog.overview()
    payload["formula_summary"] = formula_extras.stage4_summary()
    if isinstance(payload.get("modules"), dict):
        payload["modules"]["six_channels"] = "complete"
        payload["modules"]["diagnosis"] = "ready"
        payload["modules"]["jinkui"] = "complete"
    return payload


@app.get("/api/formulas")
def formulas(
    q: str = "",
    type: str = "",
    meridian: str = "",
    book: str = "",
    status: str = "",
    review: str = "",
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=24, ge=1, le=60),
):
    return catalog.list_formulas(q, type, meridian, book, status, review, page, page_size)


@app.get("/api/formulas/diagnose")
def formulas_diagnose(
    q: str = Query(default=""),
    book: str = Query(default=""),
    six_meridian: str = Query(default=""),
    chapter_id: str = Query(default=""),
):
    return formula_diagnose.diagnose_formulas(
        q=q,
        book=book,
        six_meridian=six_meridian,
        chapter_id=chapter_id,
    )


@app.get("/api/formulas/{formula_id:path}")
def formula(formula_id: str):
    item = catalog.get_formula(formula_id)
    if not item:
        raise HTTPException(status_code=404, detail="未找到方剂")
    return formula_extras.enrich_formula_payload(item)


@app.get("/api/herbs")
def herbs(
    q: str = "",
    category: str = "",
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=24, ge=1, le=60),
):
    return catalog.list_herbs(q, category, page, page_size)


@app.get("/api/herbs/{herb_id:path}")
def herb(herb_id: str):
    item = catalog.get_herb(herb_id)
    if not item:
        raise HTTPException(status_code=404, detail="未找到中药")
    return item


@app.get("/api/six-channels")
def six_channels():
    return catalog.list_six_channels()


@app.get("/api/six-channels/{channel_id:path}")
def six_channel(channel_id: str):
    item = catalog.get_six_channel(channel_id)
    if not item:
        raise HTTPException(status_code=404, detail="未找到六经条目")
    return formula_extras.enrich_six_channel_payload(item)


@app.get("/api/acupuncture/overview")
def acupuncture_overview():
    return acupuncture_catalog.overview()


@app.get("/api/acupuncture/chapters")
def acupuncture_chapters():
    return acupuncture_catalog.list_chapters()


@app.get("/api/acupuncture/chapters/{chapter_id:path}")
def acupuncture_chapter(chapter_id: str):
    item = acupuncture_catalog.get_chapter(chapter_id)
    if not item:
        raise HTTPException(status_code=404, detail="未找到针灸章节")
    return item


@app.get("/api/acupuncture/indexes")
def acupuncture_indexes(
    q: str = Query(default=""),
    kind: str = Query(default=""),
):
    return acupuncture_catalog.list_book_indexes(q=q, kind=kind)


@app.get("/api/acupuncture/meridians")
def acupuncture_meridians(
    q: str = Query(default=""),
    review_status: str = Query(default=""),
    risk_level: str = Query(default=""),
):
    return acupuncture_catalog.list_meridians(q=q, review_status=review_status, risk_level=risk_level)


@app.get("/api/acupuncture/meridians/{meridian_id:path}")
def acupuncture_meridian(meridian_id: str):
    item = acupuncture_catalog.get_meridian(meridian_id)
    if not item:
        raise HTTPException(status_code=404, detail="未找到经络条目")
    return item


@app.get("/api/acupuncture/points")
def acupuncture_points(
    q: str = Query(default=""),
    meridian_id: str = Query(default=""),
    review_status: str = Query(default=""),
    risk_level: str = Query(default=""),
):
    return acupuncture_catalog.list_points(
        q=q,
        meridian_id=meridian_id,
        review_status=review_status,
        risk_level=risk_level,
    )


@app.get("/api/acupuncture/points/{point_id:path}")
def acupuncture_point(point_id: str):
    item = acupuncture_catalog.get_point(point_id)
    if not item:
        raise HTTPException(status_code=404, detail="未找到穴位条目")
    return item


@app.get("/api/acupuncture/techniques")
def acupuncture_techniques(
    q: str = Query(default=""),
    category: str = Query(default=""),
    review_status: str = Query(default=""),
    risk_level: str = Query(default=""),
):
    return acupuncture_catalog.list_techniques(
        q=q,
        category=category,
        review_status=review_status,
        risk_level=risk_level,
    )


@app.get("/api/acupuncture/techniques/{technique_id:path}")
def acupuncture_technique(technique_id: str):
    item = acupuncture_catalog.get_technique(technique_id)
    if not item:
        raise HTTPException(status_code=404, detail="未找到针灸技法条目")
    return item


@app.get("/api/acupuncture/conditions")
def acupuncture_conditions(
    q: str = Query(default=""),
    review_status: str = Query(default=""),
    risk_level: str = Query(default=""),
):
    return acupuncture_catalog.list_conditions(q=q, review_status=review_status, risk_level=risk_level)


@app.get("/api/acupuncture/conditions/{condition_id:path}")
def acupuncture_condition(condition_id: str):
    item = acupuncture_catalog.get_condition(condition_id)
    if not item:
        raise HTTPException(status_code=404, detail="未找到针灸治症条目")
    return item


@app.get("/api/acupuncture/diagnose")
def acupuncture_diagnose_endpoint(
    q: str = Query(default=""),
    risk_level: str = Query(default=""),
    meridian_id: str = Query(default=""),
):
    return acupuncture_diagnose.diagnose_symptoms(
        q=q,
        risk_level=risk_level,
        meridian_id=meridian_id,
    )


@app.get("/api/acupuncture/source-pages/{pdf_page}/image")
def acupuncture_source_page_image(pdf_page: int):
    img = acupuncture_catalog.render_page_image(pdf_page)
    if not img:
        raise HTTPException(status_code=404, detail="未找到针灸原书页面图像")
    return FileResponse(img, media_type="image/png")


@app.get("/api/acupuncture/source-pages/{pdf_page}")
def acupuncture_source_page(pdf_page: int):
    item = acupuncture_catalog.get_source_page(pdf_page)
    if not item:
        raise HTTPException(status_code=404, detail="未找到针灸原书页面")
    return item


@app.get("/api/neijing/overview")
def neijing_overview():
    return neijing_catalog.overview()


@app.get("/api/neijing/chapters")
def neijing_chapters(
    q: str = Query(default=""),
    volume: str = Query(default=""),
    review_status: str = Query(default=""),
    risk_level: str = Query(default=""),
):
    return neijing_catalog.list_chapters(
        q=q,
        volume=volume,
        review_status=review_status,
        risk_level=risk_level,
    )


@app.get("/api/neijing/chapters/{chapter_id:path}")
def neijing_chapter(chapter_id: str):
    item = neijing_catalog.get_chapter(chapter_id)
    if not item:
        raise HTTPException(status_code=404, detail="未找到内经篇目")
    return item


@app.get("/api/neijing/concepts")
def neijing_concepts(
    q: str = Query(default=""),
    submodule: str = Query(default=""),
    review_status: str = Query(default=""),
    risk_level: str = Query(default=""),
):
    return neijing_catalog.list_concepts(
        q=q,
        submodule=submodule,
        review_status=review_status,
        risk_level=risk_level,
    )


@app.get("/api/neijing/concepts/{concept_id:path}")
def neijing_concept(concept_id: str):
    item = neijing_catalog.get_concept(concept_id)
    if not item:
        raise HTTPException(status_code=404, detail="未找到内经专题")
    return item


@app.get("/api/neijing/diagnose")
def neijing_diagnose(
    q: str = Query(default=""),
    submodule: str = Query(default=""),
    risk_level: str = Query(default=""),
):
    return neijing_catalog.diagnose(q=q, submodule=submodule, risk_level=risk_level)


@app.get("/api/neijing/pages")
def neijing_pages_search(
    q: str = Query(default=""),
    volume: str = Query(default=""),
    page_role: str = Query(default=""),
    limit: int = Query(default=60, ge=1, le=120),
):
    return neijing_catalog.search_pages(q=q, volume=volume, page_role=page_role, limit=limit)


@app.get("/api/neijing/source-pages/{source_id}/{pdf_page}/image")
def neijing_source_page_image(source_id: str, pdf_page: int):
    img = neijing_catalog.render_page_image(source_id, pdf_page)
    if not img:
        raise HTTPException(status_code=404, detail="未找到内经原书页面图像")
    return FileResponse(img, media_type="image/png")


@app.get("/api/neijing/source-pages/{source_id}/{pdf_page}")
def neijing_source_page(source_id: str, pdf_page: int):
    item = neijing_catalog.get_source_page(source_id, pdf_page)
    if not item:
        raise HTTPException(status_code=404, detail="未找到内经原书页面")
    return item


@app.get("/api/neijing/page-by-id/{page_id:path}")
def neijing_source_page_by_id(page_id: str):
    item = neijing_catalog.get_source_page_by_id(page_id)
    if not item:
        raise HTTPException(status_code=404, detail="未找到内经原书页面")
    return item


@app.get("/api/jinkui-chapters")
def jinkui_chapters(
    q: str = Query(default=""),
    review_status: str = Query(default=""),
):
    return formula_extras.list_jinkui_chapters(q=q, review_status=review_status)


@app.get("/api/jinkui-chapters/{chapter_id:path}")
def jinkui_chapter_detail(chapter_id: str):
    item = formula_extras.get_jinkui_chapter(chapter_id)
    if not item:
        raise HTTPException(status_code=404, detail="未找到金匮要略篇目")
    return item


@app.get("/api/formula-modifications")
def formula_modifications(
    q: str = Query(default=""),
    base_formula_id: str = Query(default=""),
    target_formula_id: str = Query(default=""),
):
    return formula_extras.list_formula_modifications(
        q=q,
        base_formula_id=base_formula_id,
        target_formula_id=target_formula_id,
    )


@app.get("/api/formula-variants")
def formula_variants(
    q: str = Query(default=""),
    diff_only: bool = Query(default=False),
):
    return formula_extras.list_formula_variants(q=q, diff_only=diff_only)


@app.get("/api/formula-acupuncture-links")
def formula_acupuncture_links(
    q: str = Query(default=""),
    formula_id: str = Query(default=""),
    channel_id: str = Query(default=""),
    chapter_id: str = Query(default=""),
):
    return formula_extras.list_formula_acupuncture_links(
        q=q,
        formula_id=formula_id,
        channel_id=channel_id,
        chapter_id=chapter_id,
    )


@app.get("/api/bencao/overview")
def bencao_overview():
    return bencao_catalog.overview()


@app.get("/api/bencao/chapters")
def bencao_chapters():
    return bencao_catalog.list_chapters()


@app.get("/api/bencao/chapters/{chapter_id:path}")
def bencao_chapter_detail(chapter_id: str):
    item = bencao_catalog.get_chapter(chapter_id)
    if not item:
        raise HTTPException(status_code=404, detail="未找到本草经章节")
    return item


@app.get("/api/bencao/entries")
def bencao_entries(
    q: str = "",
    grade: str = "",
    nature: str = "",
    flavor: str = "",
    toxicity: str = "",
    risk_level: str = "",
    review_status: str = "",
    has_formulas: bool = False,
    recovered_only: bool = False,
    meridian: str = "",
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=24, ge=1, le=80),
):
    return bencao_catalog.list_entries(
        q=q,
        grade=grade,
        nature=nature,
        flavor=flavor,
        toxicity=toxicity,
        risk_level=risk_level,
        review_status=review_status,
        has_formulas=has_formulas,
        recovered_only=recovered_only,
        meridian=meridian,
        page=page,
        page_size=page_size,
    )


@app.get("/api/bencao/comparisons")
def bencao_comparisons(q: str = "", category: str = ""):
    return bencao_catalog.list_comparisons(q=q, category=category)


@app.get("/api/bencao/comparisons/{comp_id:path}")
def bencao_comparison_detail(comp_id: str):
    item = bencao_catalog.get_comparison(comp_id)
    if not item:
        raise HTTPException(status_code=404, detail="未找到本草比较专题")
    return item


@app.get("/api/bencao/diagnose")
def bencao_diagnose(
    q: str = Query(default=""),
    grade: str = Query(default=""),
    risk_level: str = Query(default=""),
):
    return bencao_catalog.diagnose(q=q, grade=grade, risk_level=risk_level)


@app.get("/api/bencao/pages")
def bencao_pages_search(
    q: str = Query(default=""),
    page_role: str = Query(default=""),
    limit: int = Query(default=40, ge=1, le=160),
):
    return bencao_catalog.search_pages(q=q, page_role=page_role, limit=limit)


@app.get("/api/bencao/source-pages/{pdf_page}/image")
def bencao_source_page_image(pdf_page: int):
    img = bencao_catalog.render_page_image(pdf_page)
    if not img:
        raise HTTPException(status_code=404, detail="未找到本草经原书页面图像")
    return FileResponse(img, media_type="image/png")


@app.get("/api/bencao/source-pages/{pdf_page}")
def bencao_source_page(pdf_page: int):
    item = bencao_catalog.get_source_page(pdf_page)
    if not item:
        raise HTTPException(status_code=404, detail="未找到本草经原书页面")
    return item


@app.get("/api/bencao/entries/{entry_id:path}")
def bencao_entry_detail(entry_id: str):
    item = bencao_catalog.get_entry(entry_id)
    if not item:
        raise HTTPException(status_code=404, detail="未找到神农本草经条目")
    return item


@app.get("/api/library/overview")
def library_overview():
    return library_catalog.overview()


@app.get("/api/library/books")
def library_books(shelf: str = Query(default=""), q: str = Query(default="")):
    return library_catalog.list_books(shelf=shelf, q=q)


@app.get("/api/library/books/{book_id}/pages/{page_no}/image")
def library_book_page_image(book_id: str, page_no: int):
    img = library_catalog.render_book_page_image(book_id, page_no)
    if not img:
        raise HTTPException(status_code=404, detail="未找到书籍原页扫描图像")
    return FileResponse(img, media_type="image/png")


@app.get("/api/library/books/{book_id}/pages/{page_no}")
def library_book_page_detail(book_id: str, page_no: int):
    item = library_catalog.get_book_page(book_id, page_no)
    if not item:
        raise HTTPException(status_code=404, detail="未找到指定书页或章节")
    return item


@app.get("/api/library/books/{book_id}/pages")
def library_book_pages(
    book_id: str,
    q: str = Query(default=""),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=60, ge=1, le=200),
):
    item = library_catalog.list_book_pages(book_id, q=q, offset=offset, limit=limit)
    if not item:
        raise HTTPException(status_code=404, detail="未找到指定书籍")
    return item


@app.get("/api/library/locate")
def library_locate_context(
    book_id: str = Query(default=""),
    page_no: int = Query(default=0, ge=0),
    line: int = Query(default=0, ge=0),
    q: str = Query(default=""),
    book_hint: str = Query(default=""),
    before: int = Query(default=2, ge=0, le=6),
    after: int = Query(default=4, ge=0, le=8),
):
    item = library_catalog.locate_book_context(
        book_id=book_id,
        page_no=page_no,
        line=line,
        q=q,
        book_hint=book_hint,
        before=before,
        after=after,
    )
    if not item:
        raise HTTPException(status_code=404, detail="未能在书库中定位对应原书页码")
    return item


@app.get("/api/library/books/{book_id}/context")
def library_book_context(
    book_id: str,
    page_no: int = Query(default=1, ge=1),
    before: int = Query(default=2, ge=0, le=6),
    after: int = Query(default=4, ge=0, le=8),
):
    item = library_catalog.get_book_context(book_id, page_no=page_no, before=before, after=after)
    if not item:
        raise HTTPException(status_code=404, detail="未找到指定书籍或上下文页面")
    return item


@app.get("/api/library/books/{book_id}")
def library_book_detail(book_id: str):
    item = library_catalog.get_book(book_id)
    if not item:
        raise HTTPException(status_code=404, detail="未找到指定书籍")
    return item


@app.get("/api/library/search")
def library_search(
    q: str = Query(default=""),
    shelf: str = Query(default=""),
    book_id: str = Query(default=""),
    limit: int = Query(default=36, ge=1, le=100),
):
    return library_catalog.search(q=q, shelf=shelf, book_id=book_id, limit=limit)


@app.get("/api/library/entity-links/{entity_id:path}")
def library_entity_links(entity_id: str):
    return library_catalog.get_entity_links(entity_id)


@app.get("/api/stage5/overview")
def stage5_overview():
    return stage5_service.overview()


@app.get("/api/stage5/syndromes")
def stage5_syndromes(q: str = Query(default="")):
    return stage5_service.list_syndromes(q=q)


@app.get("/api/stage5/syndromes/{syndrome_id:path}")
def stage5_syndrome_detail(syndrome_id: str):
    item = stage5_service.get_syndrome(syndrome_id)
    if not item:
        raise HTTPException(status_code=404, detail="未找到跨书辨证证候群")
    return item


@app.get("/api/stage5/diagnose")
def stage5_diagnose(q: str = Query(default="")):
    return stage5_service.diagnose_unified(q=q)


@app.get("/api/stage5/compose")
def stage5_compose(q: str = Query(default=""), pulse: str = Query(default="")):
    return syndrome_composer.compose_differentiation(q=q, pulse=pulse)


@app.get("/api/stage5/ground")
def stage5_ground(
    q: str = Query(default=""),
    limit: int = Query(default=12, ge=1, le=24),
):
    return grounded_study.ground_study_query(q=q, limit_citations=limit)


# --- Hantang Formulas & Ni Haixia Clinical System ---
@app.get("/api/hantang/overview")
def hantang_overview():
    return hantang_catalog.overview()


@app.get("/api/hantang/formulas")
def hantang_formulas(
    category: str = Query(default=""),
    safety: str = Query(default=""),
    q: str = Query(default=""),
):
    return hantang_catalog.list_formulas(category=category, safety=safety, q=q)


@app.get("/api/hantang/formulas/{formula_id:path}")
def hantang_formula_detail(formula_id: str):
    item = hantang_catalog.get_formula(formula_id)
    if not item:
        raise HTTPException(status_code=404, detail="未找到汉唐方剂")
    return item


@app.get("/api/hantang/match")
def hantang_match(
    q: str = Query(default=""),
    limit: int = Query(default=4, ge=1, le=8),
):
    return hantang_catalog.match_clinical_context(q=q, limit=limit)


app.mount("/", StaticFiles(directory=WEB, html=True), name="web")
