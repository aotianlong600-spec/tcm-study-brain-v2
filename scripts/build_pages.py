"""Build the self-contained GitHub Pages / PWA static edition in dist/."""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import re
import shutil
from urllib.request import urlopen
from zipfile import ZIP_DEFLATED, ZipFile


ROOT = Path(__file__).resolve().parents[1]
WEB_DIR = ROOT / "web"
PAGES_SRC = ROOT / "scripts" / "pages"
CACHE_DIR = ROOT / ".pages-cache"
DIST = ROOT / "dist"

RUNTIME_ASSETS = {
    "pyodide/pyodide.mjs": (
        "https://cdn.jsdelivr.net/pyodide/v0.29.3/full/pyodide.mjs",
        "23213d27e9dacbda6f25f955fb38dabfc40ada082c04ee253047ea5dddcaa3b5",
    ),
    "pyodide/pyodide.asm.js": (
        "https://cdn.jsdelivr.net/pyodide/v0.29.3/full/pyodide.asm.js",
        "1263f02b5b26099b96112378156f242dd98b39a8201ba7765e5fe3d455c5ce91",
    ),
    "pyodide/pyodide.asm.wasm": (
        "https://cdn.jsdelivr.net/pyodide/v0.29.3/full/pyodide.asm.wasm",
        "e2f4ee75b325e35eb31bfb8c613d4dd5098f5502c156a97847686875b5025480",
    ),
    "pyodide/python_stdlib.zip": (
        "https://cdn.jsdelivr.net/pyodide/v0.29.3/full/python_stdlib.zip",
        "4298b6ee445cb724c3973437da47789752b9e6ff4e26619026b283ec801fc46b",
    ),
    "pyodide/pyodide-lock.json": (
        "https://cdn.jsdelivr.net/pyodide/v0.29.3/full/pyodide-lock.json",
        "3256ffc76388de0e37f4b34d42ab484268d1afc675179ff97b2a5bb14f84ccac",
    ),
    "pyodide/LICENSE": (
        "https://raw.githubusercontent.com/pyodide/pyodide/0.29.3/LICENSE",
        "1f256ecad192880510e84ad60474eab7589218784b9a50bc7ceee34c2b91f1d5",
    ),
    "pdfjs/pdf.min.mjs": (
        "https://cdn.jsdelivr.net/npm/pdfjs-dist@4.8.69/build/pdf.min.mjs",
        "85d678eca696a50ed3e372afb4e4831d9cd16c3d56b9b14011b0d982f8e6bcc2",
    ),
    "pdfjs/pdf.worker.min.mjs": (
        "https://cdn.jsdelivr.net/npm/pdfjs-dist@4.8.69/build/pdf.worker.min.mjs",
        "8806d6a3b155fca69eb4b590629f760794fe3e21e82df102a39762d60eed53e1",
    ),
    "pdfjs/LICENSE": (
        "https://cdn.jsdelivr.net/npm/pdfjs-dist@4.8.69/LICENSE",
        "0d542e0c8804e39aa7f37eb00da5a762149dc682d7829451287e11b938e94594",
    ),
}


def download_verified(rel_path: str, url: str, expected_sha256: str) -> bytes:
    cached = CACHE_DIR / rel_path
    if cached.is_file():
        data = cached.read_bytes()
        if sha256(data).hexdigest() == expected_sha256:
            return data
    print(f"Downloading {url} ...")
    with urlopen(url, timeout=90) as resp:
        data = resp.read()
    digest = sha256(data).hexdigest()
    if digest != expected_sha256:
        raise ValueError(f"Checksum mismatch for {rel_path}: got {digest}, expected {expected_sha256}")
    cached.parent.mkdir(parents=True, exist_ok=True)
    cached.write_bytes(data)
    return data


def create_pwa_icons(out_dir: Path) -> None:
    from PIL import Image, ImageDraw, ImageFont

    out_dir.mkdir(parents=True, exist_ok=True)
    specs = [("icon-192.png", 192), ("icon-512.png", 512), ("apple-touch-icon.png", 180)]
    font_candidates = [
        "C:/Windows/Fonts/msyhbd.ttc",
        "C:/Windows/Fonts/simsun.ttc",
        "/usr/share/fonts/opentype/noto/NotoSerifCJK-Bold.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
    ]
    font_path = next((p for p in font_candidates if Path(p).is_file()), None)

    for fname, size in specs:
        img = Image.new("RGBA", (size, size), (22, 72, 54, 255))
        draw = ImageDraw.Draw(img)
        pad = max(8, size // 14)
        draw.rounded_rectangle(
            [pad, pad, size - pad, size - pad],
            radius=size // 6,
            fill=(22, 72, 54, 255),
            outline=(232, 221, 198, 255),
            width=max(2, size // 36),
        )
        txt = "医" if font_path and not font_path.endswith("DejaVuSerif-Bold.ttf") else "TCM"
        if font_path:
            fsize = int(size * (0.54 if txt == "医" else 0.3))
            font = ImageFont.truetype(font_path, fsize)
        else:
            font = ImageFont.load_default()
        bbox = draw.textbbox((0, 0), txt, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        draw.text(
            ((size - tw) / 2 - bbox[0], (size - th) / 2 - bbox[1]),
            txt,
            font=font,
            fill=(249, 245, 236, 255),
        )
        img.save(out_dir / fname, format="PNG")


def _should_bundle_data_file(rel: str) -> bool:
    if rel.startswith("data/library/page_images/"):
        return False
    if "/review_batches/" in rel:
        return False
    if rel.endswith(("_report.json", "audit_report.json", "evidence_report.json")):
        return False
    return rel.endswith((".json", ".jsonl"))


def build_bundle_zip(target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(target, "w", ZIP_DEFLATED, compresslevel=6) as zf:
        for pkg in ("app", "ai", "retrieval"):
            for p in sorted((ROOT / pkg).rglob("*.py")):
                if "__pycache__" in p.parts:
                    continue
                zf.write(p, p.relative_to(ROOT).as_posix())
        zf.write(ROOT / "etl/__init__.py", "etl/__init__.py")
        zf.write(ROOT / "etl/herb_alias.py", "etl/herb_alias.py")

        for p in sorted((ROOT / "data").rglob("*")):
            if not p.is_file():
                continue
            rel = p.relative_to(ROOT).as_posix()
            if _should_bundle_data_file(rel):
                zf.write(p, rel)

        needed_sources = [
            ROOT / "sources/acupuncture/pages.jsonl",
            ROOT / "sources/bencao/pages.jsonl",
            ROOT / "sources/neijing/pages.jsonl",
        ] + sorted((ROOT / "sources/library").glob("*.jsonl"))
        for p in needed_sources:
            if p.is_file():
                zf.write(p, p.relative_to(ROOT).as_posix())

        books_readme = ROOT / "books/README.md"
        if books_readme.is_file():
            zf.write(books_readme, "books/README.md")


def build_dist(*, skip_pdfs: bool = False) -> Path:
    if DIST.exists():
        shutil.rmtree(DIST)
    DIST.mkdir(parents=True, exist_ok=True)

    # 1. Runtime assets (Pyodide + PDF.js)
    for rel, (url, digest) in RUNTIME_ASSETS.items():
        data = download_verified(rel, url, digest)
        out_file = DIST / "runtime" / rel
        out_file.parent.mkdir(parents=True, exist_ok=True)
        out_file.write_bytes(data)

    # 2. Knowledge & Python runtime bundle.zip
    bundle_path = DIST / "runtime" / "bundle.zip"
    build_bundle_zip(bundle_path)
    bundle_ver = sha256(bundle_path.read_bytes()).hexdigest()[:14]

    # 3. Copy PDFs for lazy PDF.js page-scan rendering
    if not skip_pdfs:
        pdf_src = ROOT / "books" / "ni-haixia-medicine"
        pdf_dst = DIST / "books" / "ni-haixia-medicine"
        pdf_dst.mkdir(parents=True, exist_ok=True)
        for p in sorted(pdf_src.glob("*.pdf")):
            shutil.copy2(p, pdf_dst / p.name)

    # 4. Copy web static assets
    for p in sorted(WEB_DIR.iterdir()):
        if not p.is_file() or p.name == "index.html":
            continue
        shutil.copy2(p, DIST / p.name)

    # 5. Copy worker & runtime bridge with pinned build id
    worker_src = (PAGES_SRC / "pages_worker.js").read_text(encoding="utf-8")
    (DIST / "pages_worker.js").write_text(worker_src.replace("__BUILD_ID__", bundle_ver), encoding="utf-8")

    rt_src = (PAGES_SRC / "pages_runtime.js").read_text(encoding="utf-8")
    (DIST / "pages_runtime.js").write_text(rt_src.replace("__BUILD_ID__", bundle_ver), encoding="utf-8")

    # 6. Icons & Web App Manifest
    create_pwa_icons(DIST / "icons")
    manifest = {
        "id": "./",
        "name": "中医学习大脑 · 构建版",
        "short_name": "中医大脑",
        "lang": "zh-CN",
        "start_url": "./",
        "scope": "./",
        "display": "standalone",
        "background_color": "#f6f2e8",
        "theme_color": "#164836",
        "icons": [
            {"src": "icons/icon-192.png", "sizes": "192x192", "type": "image/png"},
            {"src": "icons/icon-512.png", "sizes": "512x512", "type": "image/png"},
        ],
    }
    (DIST / "manifest.webmanifest").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    # 7. Transform web/index.html -> dist/index.html with relative paths & static bridge
    html = (WEB_DIR / "index.html").read_text(encoding="utf-8")
    html = html.replace("<html lang=\"zh-CN\">", '<html lang="zh-CN" data-static-web="true">')
    html = re.sub(r'href="/favicon\.svg"', 'href="./favicon.svg"', html)
    html = re.sub(r'href="/style\.css(?:\?[^"]*)?"', f'href="./style.css?v={bundle_ver}"', html)
    html = html.replace(
        "</head>",
        '  <link rel="manifest" href="manifest.webmanifest">\n'
        '    <link rel="apple-touch-icon" sizes="180x180" href="icons/apple-touch-icon.png">\n'
        '    <meta name="apple-mobile-web-app-capable" content="yes">\n'
        '    <meta name="apple-mobile-web-app-title" content="中医大脑">\n'
        '    <meta name="apple-mobile-web-app-status-bar-style" content="default">\n'
        "  </head>",
    )
    html = html.replace(
        "原文仅供学习，不替代诊疗",
        "构建版（持续优化中）· 原文仅供学习，不替代诊疗",
    )
    for js_name in ("acupuncture.js", "bencao.js", "neijing.js", "app.js", "formulas_stage4.js", "library_stage5.js"):
        html = html.replace(f'src="/{js_name}"', f'src="./{js_name}?v={bundle_ver}"')
    html = html.replace(
        f'<script src="./acupuncture.js?v={bundle_ver}"></script>',
        f'<script src="./pages_runtime.js?v={bundle_ver}"></script>\n    <script src="./acupuncture.js?v={bundle_ver}"></script>',
    )
    (DIST / "index.html").write_text(html, encoding="utf-8")
    (DIST / ".nojekyll").write_text("", encoding="utf-8")

    # 8. Service Worker (precache shell files, lazy runtime & pdfs)
    precache = [
        "index.html",
        f"style.css?v={bundle_ver}",
        "favicon.svg",
        f"pages_runtime.js?v={bundle_ver}",
        f"pages_worker.js?v={bundle_ver}",
        f"acupuncture.js?v={bundle_ver}",
        f"bencao.js?v={bundle_ver}",
        f"neijing.js?v={bundle_ver}",
        f"app.js?v={bundle_ver}",
        f"formulas_stage4.js?v={bundle_ver}",
        f"library_stage5.js?v={bundle_ver}",
        "manifest.webmanifest",
        "icons/icon-192.png",
        "icons/icon-512.png",
        "icons/apple-touch-icon.png",
    ]
    sw_src = (PAGES_SRC / "sw-template.js").read_text(encoding="utf-8")
    (DIST / "sw.js").write_text(
        sw_src.replace("__PWA_CONFIG__", json.dumps({"version": bundle_ver, "precache": precache}, ensure_ascii=False)),
        encoding="utf-8",
    )
    print(
        f"Built static PWA/Pages app in {DIST} (version={bundle_ver}, "
        f"bundle_zip={bundle_path.stat().st_size / 1024 / 1024:.2f} MB)"
    )
    return DIST


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Build static GitHub Pages / PWA distribution.")
    parser.add_argument("--skip-pdfs", action="store_true", help="Skip copying PDF files into dist/books.")
    args = parser.parse_args()
    build_dist(skip_pdfs=args.skip_pdfs)
