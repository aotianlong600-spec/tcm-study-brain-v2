"""FastAPI entry point for the local formula module."""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from . import catalog


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web"

app = FastAPI(title="中医学习大脑 · 本地方剂")


@app.get("/api/health")
def health():
    return {"status": "ok", "module": "formula"}


@app.get("/api/overview")
def overview():
    return catalog.overview()


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


@app.get("/api/formulas/{formula_id:path}")
def formula(formula_id: str):
    item = catalog.get_formula(formula_id)
    if not item:
        raise HTTPException(status_code=404, detail="未找到方剂")
    return item


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
    return item


app.mount("/", StaticFiles(directory=WEB, html=True), name="web")
