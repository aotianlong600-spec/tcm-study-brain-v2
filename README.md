# 中医学习大脑 · 本地知识库与网页版（v0.1.0-build）

> **构建版声明（持续构建与优化中）**
> 本项目当前为 **初版构建版（`v0.1.0-build`）**，各模块资料整理、板书校勘与辨证匹配逻辑仍在持续构建与迭代优化中。
> 系统内所有经方剂量、本草条文、针灸配穴与辨证线索仅用于**个人中医学习、文献考据与代码研究**，**不构成医疗建议，绝不能替代执业医师面对面四诊合参**。

[在线网页版（GitHub Pages）](https://aotianlong600-spec.github.io/tcm-study-brain-v2/) · [版本发布（Releases）](https://github.com/aotianlong600-spec/tcm-study-brain-v2/releases) · [构建与开发说明](docs/BUILD_GUIDE.md) · [资料范围与免责声明](docs/DATA_AND_DISCLAIMER.md) · [来源署名](ATTRIBUTION.md) · [MIT 许可证](LICENSE)

---

## 在线网页版与 PWA 支持

网页版与《天纪紫微》网页版同样托管于 GitHub Pages（`https://aotianlong600-spec.github.io/tcm-study-brain-v2/`），采用纯静态构建分发，**无需后端服务器即可在浏览器中完整运行**：

- 通过 Web Worker 在浏览器本地启动 [Pyodide](https://pyodide.org/) Python 运行时并挂载结构化索引包（首次打开会下载运行时与数据压缩包，建议在稳定网络环境下首次加载）。
- 支持安装为桌面 / iOS / Android PWA 网页应用；加载完成后可离线检索经方、本草、针灸、内经与辨证线索。
- 原书 PDF 扫描对照图在网页版采用 [PDF.js](https://mozilla.github.io/pdf.js/) 按查看页面**按需渲染**，不预先全量下载所有 PDF 页面图片。

---

## 当前已集成模块与实际范围（v0.1.0-build）

| 模块 | 覆盖数据与主要功能 | 诚实范围与已知局限 |
|---|---|---|
| **辨证论治 · 合方配穴** | 整合 `20` 个核心病证模块与 `346` 条经方-本草-经穴关联边；支持输入症状、主诉与辨证线索，给出合方组合、原方加减参考、配穴思路及原书出处 | 初版为本地规则与结构化知识网络匹配，尚待后续进一步丰富条文权重与多维辩证支持 |
| **伤寒金匮经方 · 六经** | 共 `299` 首经方（《伤寒论》`113` 首 + 《金匮要略》`186` 首），逐方校对 `299/299`；收录原书加减 `108` 条、衍化方 `42` 条、针灸联动 `27` 条，并汇总 [剂量核查索引](docs/formula-dosage-index.md) | 极少数条目底本存在异文或待核状态（如 `variant`、`manual`、`missing`、`unchecked` 等），已在界面明确标示来源状态 |
| **人纪针灸与症状取穴** | 依据《倪海厦人纪系列之针灸教程》（`216` PDF 页），收录 `15` 条经络、`387` 条穴位记录（其中 `385` 已核准、`2` 条待核）、`86` 项针灸技法、`34` 类常见病症及 `1,364` 条关联 | 保留原书待考与禁忌提示；部分跨章节对照仍在继续细化 |
| **神农本草经（全书复原）** | 依据《倪海厦注神农本草经》（`154` PDF 页，第 2–3 页原书空白），完整复原正经 `357` 味（上经 `142`、中经 `112`、下经 `103`）及第三章增补仲景常用药 `28` 味，合计 `385` 味；附总义 `13` 条、鉴别对照 `38` 组、原书全页图鉴 | 不混入第三方本草书填补未载条目；个别原书错印序号按底本如实注明 |
| **黄帝内经《素问》研读** | 依据《黄帝内经》视频同步文稿上下册（`306` PDF 页 / `301` 印制页），收录 `72` 篇独特《素问》篇号（目录 `74` 条、`283` 节）、`34` 个核心概念与 `303` 条关联，分阴阳五行、藏象、病因病机、诊法、辨证、养生六大专题 | 底本缺失《素问》第 `51`、`66–71`、`73`、`74` 共 `9` 篇（含运气七大论等），且**未收录《灵枢》**；当前已完成 `24` 篇核心篇章精校，其余 `50` 篇保留目录与页码锚定，不作 AI 补全 |
| **藏书阁原书检索对照** | 收录 `17` 册本地文献（清册见 [books/README.md](books/README.md) 与 [docs/SOURCE_REGISTRY.md](docs/SOURCE_REGISTRY.md)），其中 `15` 册可全文检索（`3,303` 个单元、`2,777` 个文本单元、`2,412` 个关联页），支持目录大纲与原书 PDF 扫描页对照 | 《明清名医全书大成·徐灵胎医学全书》《黄帝外经》共 `2` 册为纯扫描图像 PDF，无电子文本层，暂仅支持逐页翻阅 |

---

## 本地运行与构建

### 1. 本地启动 FastAPI 知识库服务

需要 **Python 3.11+**。在仓库根目录执行：

```powershell
pip install -r requirements.txt
.\run.ps1
```

或手动启动：

```powershell
python -m uvicorn app.main:app --host 127.0.0.1 --port 8765
```

启动后访问 `http://127.0.0.1:8765/`。本地服务使用 `pypdfium2` 实时渲染原书 PDF 扫描页图片。

### 2. 生成静态网页与 PWA 发布包（`dist/`）

```powershell
python scripts/build_pages.py
```

脚本会校验并缓存 Pyodide (`v0.29.3`) 与 `pdfjs-dist` (`4.8.69`) 运行时资产（已配置 SHA-256 校验），将后端检索与推理包打包为 `dist/runtime/bundle.zip`，复制原书 PDF 到 `dist/books/`，并生成适配 GitHub Pages 子路径与 PWA 离线缓存的 `dist/` 目录。

如需用任意静态 HTTP 服务器本地预览静态版：

```powershell
python -m http.server 8799 --directory dist
```

### 3. 运行单元测试与数据校验器

```powershell
python -m unittest discover -s tests -q
python -m etl.acupuncture.validate
python -m etl.bencao.validate
python -m etl.neijing.validate
python -m etl.library.validate
python scripts/validate_curated_batches.py
```

更完整的目录结构、静态打包原理与 GitHub Actions 发布配置请查看 [docs/BUILD_GUIDE.md](docs/BUILD_GUIDE.md)。

---

## 开源许可与文献归属声明

- **程序代码与检索/构建脚本**：仓库内自主编写的 Python / JavaScript / CSS 代码（`app/`、`ai/`、`etl/`、`retrieval/`、`web/`、`scripts/`、`tests/`）按 [MIT 许可证](LICENSE) 开源。
- **医书原文、课程讲记与原书扫描文档**：`books/`、`sources/` 与 `data/` 中引用的古籍文本、倪海厦先生人纪与汉唐讲解文稿及原书 PDF **不按 MIT 协议授权再分发或商业使用**，详见 [ATTRIBUTION.md](ATTRIBUTION.md) 与 [docs/DATA_AND_DISCLAIMER.md](docs/DATA_AND_DISCLAIMER.md)。
- **繁简体检索字符表**：`retrieval/t2s_table.py` 基于 Apache-2.0 协议的 [OpenCC `TSCharacters.txt`](https://github.com/BYVoid/OpenCC) 生成，避免运行时引入 GPL 传代限制，使代码可干净运行于 FastAPI 与 Pyodide 浏览器端。
