# 构建与开发说明（Build & Architecture Guide）

> 本文档对应 **初版构建版（`v0.1.0-build`）**，记录仓库目录组织、本地运行、数据校验与 GitHub Pages 纯静态网页版构建机制。

## 1. 仓库目录结构

- `app/`：FastAPI 服务端入口（`app/main.py`）、纯 Python 静态请求分发器（`app/static_dispatch.py`）、合方配穴推理（`app/syndrome_composer.py`）与各模块查询目录（`app/*_catalog.py`、`app/acupuncture_diagnose.py`）。
- `retrieval/`：繁简归一与全库检索索引（`retrieval/index.py`、`retrieval/t2s_table.py`）。
- `web/`：原生 ES/DOM 单页前端（`index.html`、`style.css` 及各专题脚本 `acupuncture.js`、`bencao.js`、`neijing.js`、`formulas_stage4.js`、`library_stage5.js`、`app.js`）。
- `etl/`：文献导入、来源清册同步与各阶段一致性校验器（`etl/acupuncture/validate.py`、`etl/bencao/validate.py`、`etl/neijing/validate.py`、`etl/library/validate.py`）。
- `data/` & `sources/`：结构化知识图谱、校勘批次与页级文本快照。
- `books/`：随库保存的原书 PDF、文本与文档底本（清册见 `books/README.md` 与 `docs/SOURCE_REGISTRY.md`）。
- `scripts/`：静态网页构建器（`scripts/build_pages.py` 与 `scripts/pages/`）、剂量表导出及审查批次脚本。
- `tests/`：涵盖经方、本草、针灸、内经、藏书阁、合方配穴及 `static_dispatch` 等全栈 `unittest` 用例。

## 2. 网页构建版（GitHub Pages / PWA）工作机制

本地开发时由 `FastAPI` 提供 `/api/*` 与 `/api/.../page-image`；构建静态网页版时，`scripts/build_pages.py` 会生成可独立部署到 GitHub Pages 的 `dist/`：

1. **浏览器端 Python 引擎**：`scripts/pages/pages_runtime.js` 拦截前端发往 `/api/*` 的请求（兼容根路径 `/` 与 GitHub Pages 子路径 `/tcm-study-brain-v2/api/*`），转发给在 Web Worker 中运行的 Pyodide (`pages_worker.js`)。
2. **一致的路由分发**：`pages_worker.js` 解压并挂载 `dist/runtime/bundle.zip`，直接调用 `app/static_dispatch.py` 的 `dispatch_json()`，返回与本地 FastAPI 完全一致的 JSON 响应结构。
3. **无原生二进制依赖的繁简归一化**：`retrieval/t2s_table.py` 内置基于 Apache-2.0 OpenCC `TSCharacters.txt` 编译的纯 Python 繁简映射表，可在无 `zhconv` / C 扩展的 Pyodide 环境中直接运行。
4. **按需 PDF.js 原书扫描渲染**：前端通过 `window.tcmImgAttrs()` 为静态环境标记图片占位；当用户打开某条原文的原书对照面板时，`pages_runtime.js` 查询 `/api/__pdf-source` 定位对应的 PDF 与页码，再利用 `pdfjs-dist` 延迟渲染该页为 Canvas PNG。
5. **SHA-256 锁定运行时资源**：`scripts/build_pages.py` 下载 `Pyodide v0.29.3` 与 `pdfjs-dist@4.8.69` 时全部验证 SHA-256 摘要并缓存于 `.pages-cache/`。

## 3. GitHub Actions 自动部署

[.github/workflows/web-app.yml](../.github/workflows/web-app.yml) 在推送到 `main` 分支或手动触发时执行：

1. 安装 Python 3.11 及构建/测试依赖（`fastapi`、`uvicorn`、`pypdfium2`、`pillow`、`httpx`）。
2. 运行全量单元测试（`python -m unittest discover -s tests -q`）与 5 个模块数据校验器。
3. 执行 `python scripts/build_pages.py` 构建 `dist/` 并打包上传 GitHub Pages Artifact。
4. 通过 `actions/deploy-pages` 发布至 GitHub Pages。
