(() => {
  const $ = (sel) => document.querySelector(sel);
  const esc = (v) =>
    String(v ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");

  const MODULE_BADGE = {
    formulas: { cls: "badge-formula", text: "经方" },
    bencao: { cls: "badge-bencao", text: "本草" },
    acupuncture: { cls: "badge-acup", text: "针灸" },
    neijing: { cls: "badge-neijing", text: "内经" },
  };

  const st = {
    activeView: "", // "" | "stage5" | "library"
    // Stage 5 state
    s5Mode: "compose", // "compose" | "diagnose" | "ground" | "syndromes"
    s5Query: "",
    s5Pulses: [],
    s5Syndromes: [],
    s5Data: null,
    // Book Library state
    libShelf: "",
    libBooks: [],
    selectedBookId: "ni-hantang-formulas-pdf",
    selectedBook: null,
    currentPageNo: 1,
    pageData: null,
    viewMode: "split", // "text" | "split" | "image"
    reflowText: true,
    highlightQuery: "",
    searchActive: false,
    searchQuery: "",
  };

  async function api(url) {
    const res = await fetch(url);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
  }

  function showMsg(msg) {
    const el = $("#notice");
    if (!el) return;
    el.textContent = msg;
    el.classList.remove("hidden");
    clearTimeout(el._t);
    el._t = setTimeout(() => el.classList.add("hidden"), 2600);
  }

  function activateTopView(viewName, skipHash = false) {
    st.activeView = viewName;
    document.querySelectorAll(".module-tab").forEach((btn) => {
      btn.classList.remove("active");
      btn.setAttribute("aria-selected", "false");
    });
    document.querySelectorAll(".top-utility-tab").forEach((btn) => {
      const on = btn.dataset.stage5View === viewName;
      btn.classList.toggle("active", on);
      btn.setAttribute("aria-selected", String(on));
    });
    document.querySelectorAll(".module-view").forEach((sec) => {
      sec.classList.toggle("active", sec.id === `${viewName}-view`);
    });
    if (!skipHash) {
      if (viewName === "library") {
        location.hash = `#/library/${encodeURIComponent(st.selectedBookId)}/${st.currentPageNo}`;
      } else {
        location.hash = `#/stage5/${st.s5Mode}`;
      }
    }
  }

  function clearExtraViews() {
    st.activeView = "";
    document.querySelectorAll(".top-utility-tab").forEach((btn) => {
      btn.classList.remove("active");
      btn.setAttribute("aria-selected", "false");
    });
    $("#stage5-view")?.classList.remove("active");
    $("#library-view")?.classList.remove("active");
  }

  // -------------------- Cross-Module Entity Jump --------------------
  async function jumpToModuleEntity(module, entityId) {
    if (!module || !entityId) return;
    clearExtraViews();
    if (module === "formulas") {
      document.querySelector('.module-tab[data-view="formulas"]')?.click();
      setTimeout(() => {
        if (window.Stage4Formulas?.openFormulaDetailById) {
          window.Stage4Formulas.switchMode?.("catalog");
          window.Stage4Formulas.openFormulaDetailById(entityId);
        } else if (typeof window.openFormula === "function") {
          window.openFormula(entityId);
        } else {
          location.hash = `#/formulas/${encodeURIComponent(entityId)}`;
        }
      }, 90);
      return;
    }
    if (module === "bencao" || module === "herbs") {
      document.querySelector('.module-tab[data-view="herbs"]')?.click();
      setTimeout(() => {
        if (window.bencaoUI?.openEntry) {
          window.bencaoUI.openEntry(entityId).catch(() => showMsg("未能打开该本草条目"));
        } else {
          location.hash = `#/herbs/entry/${encodeURIComponent(entityId)}`;
        }
      }, 80);
      return;
    }
    if (module === "neijing") {
      document.querySelector('.module-tab[data-view="neijing"]')?.click();
      setTimeout(() => {
        if (entityId.startsWith("concept:")) {
          window.neijingUI?.openConcept?.(entityId).catch(() => {});
        } else {
          window.neijingUI?.openChapter?.(entityId).catch(() => {});
        }
      }, 80);
      return;
    }
    if (module === "acupuncture") {
      document.querySelector('.module-tab[data-view="acupuncture"]')?.click();
      let sub = "points";
      if (entityId.startsWith("cond:")) sub = "conditions";
      else if (entityId.startsWith("meridian:")) sub = "meridians";
      else if (entityId.startsWith("tech:")) sub = "techniques";
      const targetHash = `#/acupuncture/${sub}/${encodeURIComponent(entityId)}`;
      setTimeout(() => {
        window.acupunctureUI?.handleHash?.(targetHash).catch(() => {});
      }, 80);
    }
  }

  // -------------------- Standalone Book Library Module (书库) --------------------
  async function loadLibraryBooks(shelf = st.libShelf) {
    st.libShelf = shelf;
    document.querySelectorAll("#lib-shelf-tabs [data-lib-shelf]").forEach((btn) => {
      const on = (btn.dataset.libShelf || "") === shelf;
      btn.classList.toggle("active", on);
      btn.setAttribute("aria-selected", String(on));
    });
    const [ov, booksRes] = await Promise.all([
      api("/api/library/overview"),
      api(`/api/library/books${shelf ? `?shelf=${encodeURIComponent(shelf)}` : ""}`),
    ]);
    st.libBooks = booksRes.items || [];
    const stats = ov.stats || {};
    const statsEl = $("#lib-overview-stats");
    if (statsEl) {
      statsEl.textContent = `共 ${stats.total_books || 17} 册 · ${stats.indexed_books || 15} 册可全文检索 · ${stats.scan_only_books || 2} 册影印扫描 · ${stats.linked_pages || 0} 页双向联动`;
    }
    const cntEl = $("#lib-books-count");
    if (cntEl) cntEl.textContent = `${st.libBooks.length} 册`;
    renderBookList();
  }

  function renderBookList() {
    const host = $("#lib-book-list");
    if (!host) return;
    if (!st.libBooks.length) {
      host.innerHTML = `<div class="empty-mini">当前分类暂无书目</div>`;
      return;
    }
    host.innerHTML = st.libBooks
      .map((b) => {
        const active = b.book_id === st.selectedBookId ? " active" : "";
        const isScan = b.search_index_status === "scan_browse_only";
        const isNew = b.shelf !== "renji_core";
        return `
          <button class="lib-book-item${active}" type="button" data-lib-select-book="${esc(b.book_id)}">
            <div class="lib-book-row-top">
              <strong class="lib-book-title">${esc(b.short_title)}</strong>
              <span class="lib-badge ${isScan ? "lib-badge-scan" : isNew ? "lib-badge-new" : "lib-badge-core"}">
                ${isScan ? `影印 ${b.total_units}页` : `${b.total_units}${b.file_format === "pdf" ? "页" : "节"}`}
              </span>
            </div>
            <div class="lib-book-meta">${esc(b.author_era)}</div>
            <div class="lib-book-tags">
              <span class="lib-shelf-pill">${esc(b.shelf_label)}</span>
              ${(b.module_affinities || []).map((m) => `<span class="lib-mod-pill">${esc(MODULE_BADGE[m === "herbs" ? "bencao" : m]?.text || m)}</span>`).join("")}
            </div>
          </button>`;
      })
      .join("");
  }

  async function selectBook(bookId, pageNo = 1, skipHash = false) {
    st.selectedBookId = bookId;
    st.searchActive = false;
    $("#lib-search-results-panel")?.classList.add("hidden");
    $("#lib-reader-workspace")?.classList.remove("hidden");
    renderBookList();

    const book = await api(`/api/library/books/${encodeURIComponent(bookId)}`);
    st.selectedBook = book;
    if (book.search_index_status === "scan_browse_only") {
      st.viewMode = "image";
    } else if (st.viewMode === "image") {
      st.viewMode = "split";
    }
    renderBookToc(book);
    await loadBookPage(bookId, pageNo, skipHash);
  }

  function renderBookToc(book, filter = "") {
    const box = $("#lib-toc-box");
    const listEl = $("#lib-toc-list");
    const titleEl = $("#lib-toc-title");
    if (!box || !listEl) return;
    box.classList.remove("hidden");
    const nf = filter.trim().toLowerCase();
    const chapters = book.chapters || [];
    if (titleEl) {
      titleEl.textContent = book.search_index_status === "scan_browse_only" ? "影印原书页码导航" : `目录大纲与方目 (${chapters.length})`;
    }
    const filteredChapters = chapters.filter(
      (c) => !nf || c.title.toLowerCase().includes(nf) || String(c.page_no) === nf
    );
    const itemsHtml = filteredChapters
      .map(
        (c) => `
        <button class="lib-toc-item ${Number(st.currentPageNo) === Number(c.page_no) ? "is-current" : ""}" type="button" data-lib-go-page="${c.page_no}">
          <span class="lib-toc-name">${esc(c.title)}</span>
          <span class="lib-toc-pno">p.${c.page_no}</span>
        </button>`
      )
      .join("");

    const topEntHtml = (book.top_entities || []).length
      ? `<div class="lib-toc-subhead">本书高频关联知识点（点跳模块）</div>
         <div class="lib-chip-cloud">
           ${(book.top_entities || [])
             .slice(0, 14)
             .map((e) => {
               const mb = MODULE_BADGE[e.module] || { cls: "badge-formula", text: e.kind };
               return `<button class="entity-jump-chip ${mb.cls}" type="button" data-jump-module="${esc(e.module)}" data-jump-id="${esc(e.entity_id)}">${esc(mb.text)} · ${esc(e.label)} <em>(${e.mentions})</em></button>`;
             })
             .join("")}
         </div>`
      : "";

    listEl.innerHTML = (itemsHtml || `<div class="empty-mini">可直接输入页码翻阅（共 ${book.total_units} 单元）</div>`) + topEntHtml;
  }

  async function loadBookPage(bookId, pageNo, skipHash = false) {
    const safePage = Math.max(1, Number(pageNo) || 1);
    const page = await api(`/api/library/books/${encodeURIComponent(bookId)}/pages/${safePage}`);
    st.currentPageNo = page.page_no;
    st.pageData = page;
    if (!skipHash && st.activeView === "library") {
      location.hash = `#/library/${encodeURIComponent(bookId)}/${page.page_no}`;
    }
    renderReaderPage();
  }

  function highlightEscapedHtml(text, query) {
    const raw = String(text || "");
    const rawTerms = String(query || "")
      .trim()
      .split(/[\s,，、；;：:。！？!?\-\/]+/)
      .map((s) => s.trim())
      .filter((s) => s.length >= 1)
      .sort((a, b) => b.length - a.length)
      .slice(0, 8);
    if (!rawTerms.length) return esc(raw);
    const pats = rawTerms.map((t) => {
      if (t.length >= 2 && /^[\u4e00-\u9fff]+$/.test(t)) {
        return Array.from(t)
          .map((ch) => ch.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"))
          .join("[\\s「」『』《》【】〔〕“”‘’\"<>〈〉]*");
      }
      return t.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    });
    const re = new RegExp(`(${pats.join("|")})`, "gi");
    let out = "";
    let lastIdx = 0;
    let m;
    while ((m = re.exec(raw)) !== null) {
      if (m.index > lastIdx) out += esc(raw.slice(lastIdx, m.index));
      out += `<mark class="lib-hl">${esc(m[0])}</mark>`;
      lastIdx = m.index + m[0].length;
      if (!m[0].length) {
        re.lastIndex += 1;
      }
    }
    if (lastIdx < raw.length) out += esc(raw.slice(lastIdx));
    return out;
  }

  function reflowBookParagraphs(raw) {
    const lines = String(raw || "").replace(/\r\n?/g, "\n").split("\n");
    const paragraphs = [];
    let buf = "";
    let prevLen = 0;

    const trimmedLines = lines.map((l) => l.replace(/[\s\u3000]+$/g, "").trim()).filter(Boolean);
    const maxLineLen = trimmedLines.length ? Math.max(30, ...trimmedLines.map((l) => l.length)) : 40;
    const paraEndCutoff = maxLineLen * 0.85;

    const isMetaLine = (s) =>
      /^(第\s*\d+\s*页|\d{4}-\d{2}-\d{2}\s*定稿|倪注《[^》]+》|倪海厦人纪|倪海厦注《|勤求古训|观其脉证)/.test(s);
    const isHeadingOrNewPara = (s) =>
      /^(第[一二三四五六七八九十百零\d]+[条章节卷篇]|[一二三四五六七八九十]+、|HT-\d+|[一二三四五六七八九十\d]+[：:.、]|【|〔|问曰[：:]|答曰[：:]|问[：:]|答[：:]|辨.+脉证|[\u4e00-\u9fff]{1,14}方[：:\s]*$|右[一二三四五六七八九十半]+味|按[：:]|注[：:]|方义[：:]|煎服法[：:]|组成[：:])/.test(
        s
      );
    const isFormulaRow = (s) =>
      /\S\s{2,}\S/.test(s) && /(两|钱|枚|升|合|斤|克|去皮|炙|炮|切|擘|碎)/.test(s);

    const flush = (kind = "body") => {
      const t = buf.trim();
      if (t) paragraphs.push({ text: t, kind });
      buf = "";
      prevLen = 0;
    };

    for (const rawLine of lines) {
      const line = rawLine.replace(/[\s\u3000]+$/g, "").trim();
      if (!line) {
        flush("body");
        continue;
      }
      if (isMetaLine(line)) {
        flush("body");
        paragraphs.push({ text: line, kind: "meta" });
        continue;
      }
      if (isFormulaRow(line)) {
        flush("body");
        paragraphs.push({ text: line, kind: "qa" });
        continue;
      }
      if (!buf) {
        if (line.length <= 26 && /^(HT-\d+|第[一二三四五六七八九十百零]+[篇章节回卷]|卷[一二三四五六七八九十]+|辨.+脉证|[\u4e00-\u9fff]{2,18}篇|[\u4e00-\u9fff]{2,14}方)$/.test(line)) {
          paragraphs.push({ text: line, kind: "heading" });
          continue;
        }
        buf = line;
        prevLen = line.length;
        continue;
      }
      const prevEndStop = /[。！？!?】」』]$/.test(buf) && prevLen <= paraEndCutoff;
      if (isHeadingOrNewPara(line) || prevEndStop) {
        flush(isHeadingOrNewPara(buf) ? "qa" : "body");
        buf = line;
        prevLen = line.length;
      } else {
        const needSpace = /[A-Za-z0-9]$/.test(buf) && /^[A-Za-z0-9]/.test(line);
        buf += (needSpace ? " " : "") + line;
        prevLen = line.length;
      }
    }
    flush(isHeadingOrNewPara(buf) ? "qa" : "body");
    return paragraphs;
  }

  function renderBookTextPane(bodyText, query) {
    const cleanText = bodyText || "（本页为空白页或封面页）";
    if (!st.reflowText) {
      return `<div class="lib-text-pane"><pre class="lib-verbatim-text">${highlightEscapedHtml(cleanText, query)}</pre></div>`;
    }
    const paras = reflowBookParagraphs(cleanText);
    const html = paras
      .map((p) => `<p class="lib-para lib-para-${p.kind}">${highlightEscapedHtml(p.text, query)}</p>`)
      .join("");
    return `<div class="lib-text-pane"><div class="lib-formatted-body">${html}</div></div>`;
  }

  function renderReaderPage() {
    const panel = $("#lib-page-reader");
    const page = st.pageData;
    const book = st.selectedBook;
    if (!panel || !page) return;

    const isScanOnly = page.search_index_status === "scan_browse_only";
    const showText = !isScanOnly && st.viewMode !== "image";
    const showImage = page.has_image_viewer && (isScanOnly || st.viewMode === "image" || st.viewMode === "split");

    const entityChipsHtml = (page.entity_links || []).length
      ? `<div class="lib-page-links-bar">
           <span class="lib-links-label">本页知识联动 · 点击直达对应学习板块：</span>
           <div class="lib-chip-cloud">
             ${page.entity_links
               .map((lk) => {
                 const mb = MODULE_BADGE[lk.module] || { cls: "badge-formula", text: lk.kind };
                 return `<button class="entity-jump-chip ${mb.cls}" type="button" data-jump-module="${esc(lk.module)}" data-jump-id="${esc(lk.entity_id)}">${esc(mb.text)} · ${esc(lk.label)}</button>`;
               })
               .join("")}
           </div>
         </div>`
      : `<div class="lib-page-links-bar muted-line">本页暂未检测到明确跨模块条目名称</div>`;

    panel.innerHTML = `
      <div class="lib-reader-head">
        <div>
          <span class="lib-shelf-pill">${esc(page.shelf_label)}</span>
          <h2>${esc(page.book_full_title)}</h2>
          <p class="lib-reader-sub">${esc(page.unit_label)} ${page.section_title ? `· ${esc(page.section_title)}` : ""}</p>
        </div>
        <div class="lib-pager-controls">
          <button class="ghost-btn" type="button" id="lib-prev-btn" ${page.prev_page ? "" : "disabled"}>上一页</button>
          <span class="lib-page-jump-wrap">
            第 <input id="lib-jump-input" class="lib-jump-input" type="number" min="1" max="${page.total_units}" value="${page.page_no}" /> / ${page.total_units}
            <button class="ghost-btn" type="button" id="lib-jump-go">跳转</button>
          </span>
          <button class="ghost-btn" type="button" id="lib-next-btn" ${page.next_page ? "" : "disabled"}>下一页</button>
        </div>
      </div>

      <div class="lib-mode-strip">
        <div class="lib-mode-btns">
          ${
            isScanOnly
              ? `<span class="lib-scan-notice">影印原件模式：本书暂无可检文字层，严禁伪造OCR，以下直接呈递高清 PDF 原书页面图像</span>`
              : `
                <button class="mode-pill ${st.viewMode === "text" ? "active" : ""}" type="button" data-lib-vmode="text">纯读原文</button>
                ${
                  page.has_image_viewer
                    ? `<button class="mode-pill ${st.viewMode === "split" ? "active" : ""}" type="button" data-lib-vmode="split">正文 + 原页扫图对照</button>
                       <button class="mode-pill ${st.viewMode === "image" ? "active" : ""}" type="button" data-lib-vmode="image">仅看原书扫图</button>`
                    : `<span class="muted-line">本书为纯文本/文档结构化全本</span>`
                }
                <span class="lib-mode-sep" aria-hidden="true"></span>
                <button class="mode-pill ${st.reflowText ? "active" : ""}" type="button" data-lib-reflow="true" title="自动重排PDF硬断行，段落对齐阅读">智能排版精读</button>
                <button class="mode-pill ${!st.reflowText ? "active" : ""}" type="button" data-lib-reflow="false" title="保留原始PDF提取断行">原页断行照录</button>
              `
          }
        </div>
        <span class="sha-pill" title="页面文本校验码">SHA: ${esc((page.text_sha256 || "").slice(0, 12))}</span>
      </div>

      ${entityChipsHtml}

      <div class="lib-content-grid ${showText && showImage ? "two-col" : "one-col"}">
        ${showText ? renderBookTextPane(page.body_text, st.highlightQuery) : ""}
        ${
          showImage
            ? `<div class="lib-image-pane">
                 <div class="lib-image-caption">原书影印图 · 第 ${page.page_no} 页</div>
                 <img class="lib-scan-img" ${window.tcmImgAttrs ? window.tcmImgAttrs(page.image_url) : `src="${esc(page.image_url)}"`} alt="${esc(page.book_title)} 第${page.page_no}页原图" loading="lazy" />
               </div>`
            : ""
        }
      </div>
      ${book?.description ? `<div class="lib-book-foot-note"><strong>藏书简介：</strong>${esc(book.description)}</div>` : ""}
    `;
    const firstMark = panel.querySelector(".lib-hl");
    if (firstMark) {
      firstMark.scrollIntoView({ behavior: "smooth", block: "center" });
    }
  }

  async function runLibrarySearch(q) {
    const query = (q || "").trim();
    if (!query) {
      st.searchActive = false;
      st.highlightQuery = "";
      $("#lib-search-results-panel")?.classList.add("hidden");
      $("#lib-reader-workspace")?.classList.remove("hidden");
      return;
    }
    st.searchActive = true;
    st.searchQuery = query;
    st.highlightQuery = query;
    const onlyCurr = $("#lib-scope-current")?.checked;
    const params = new URLSearchParams({ q: query, limit: "60" });
    if (onlyCurr && st.selectedBookId) params.set("book_id", st.selectedBookId);
    else if (st.libShelf) params.set("shelf", st.libShelf);

    const data = await api(`/api/library/search?${params.toString()}`);
    const host = $("#lib-search-results-panel");
    if (!host) return;
    host.classList.remove("hidden");
    $("#lib-reader-workspace")?.classList.add("hidden");

    const items = data.items || [];
    const exactNote = data.fallback_used
      ? `（整词无完全命中，已自动拆词检索相关页）`
      : data.exact_total
        ? `（其中整词精准命中 <b>${data.exact_total}</b> 页）`
        : "";
    const matchKindLabel = {
      exact_phrase: "精准整词",
      all_terms: "全词同页",
      partial_fallback: "拆词参考",
    };

    host.innerHTML = `
      <div class="lib-search-summary">
        <strong>全书库检索「${esc(query)}」</strong>：在已数字化的 15 册典籍中共命中 <b>${data.total}</b> 页/节 ${exactNote}（展示前 ${items.length} 条）。
        <span class="muted-line">影印保留卷（${esc((data.scan_only_notice || []).join("、"))}）不含伪造OCR。</span>
      </div>
      <div class="lib-hit-grid">
        ${
          items.length
            ? items
                .map(
                  (it) => `
                  <article class="lib-hit-card">
                    <div class="lib-hit-top">
                      <div class="lib-hit-badges">
                        <span class="lib-shelf-pill">${esc(it.shelf_label)}</span>
                        ${it.match_kind ? `<span class="lib-match-pill kind-${esc(it.match_kind)}">${esc(matchKindLabel[it.match_kind] || it.match_kind)}</span>` : ""}
                      </div>
                      <button class="primary-btn small-btn" type="button" data-lib-open="${esc(it.book_id)}:${it.page_no}">打开此页读原文</button>
                    </div>
                    <div class="lib-hit-book">${esc(it.book_title)} · ${esc(it.unit_label)}</div>
                    ${it.section_title ? `<div class="lib-hit-sec">章节/题名：${esc(it.section_title)}</div>` : ""}
                    <p class="lib-hit-snippet">${highlightEscapedHtml(it.snippet, query)}</p>
                    <div class="lib-chip-cloud lib-hit-foot">
                      ${(it.entity_links || [])
                        .slice(0, 5)
                        .map((lk) => {
                          const mb = MODULE_BADGE[lk.module] || { cls: "badge-formula", text: lk.kind };
                          return `<button class="entity-jump-chip ${mb.cls}" type="button" data-jump-module="${esc(lk.module)}" data-jump-id="${esc(lk.entity_id)}">${esc(mb.text)} · ${esc(lk.label)}</button>`;
                        })
                        .join("")}
                      <span class="sha-pill">SHA ${esc((it.text_sha256 || "").slice(0, 10))}</span>
                    </div>
                  </article>`
                )
                .join("")
            : `<div class="empty-mini">未在当前范围内检索到「${esc(query)}」，请尝试更换2字以上核心术语或取消「仅搜当前选中书目」勾选。</div>`
        }
      </div>
    `;
  }

  async function openBookPageFromAnywhere(bookId, pageNo = 1, hlQuery = "") {
    if (hlQuery) st.highlightQuery = hlQuery;
    else if (st.searchActive && st.searchQuery) st.highlightQuery = st.searchQuery;
    activateTopView("library", true);
    if (!st.libBooks.length) {
      await loadLibraryBooks("");
    }
    await selectBook(bookId, pageNo, false);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  // -------------------- Stage 5 Workbench (综合辨证 5A + 5B) --------------------
  const GROUND_CHIPS = [
    { label: "太阳表虚 vs 表实辨证", q: "桂枝汤与麻黄汤如何区分有汗恶风与无汗恶寒" },
    { label: "少阳往来寒热配穴与方证", q: "少阳病往来寒热胸胁苦满为何用小柴胡汤配期门阳陵泉" },
    { label: "胸痹心痛短气与栝蒌薤白", q: "胸痹心痛彻背短气在金匮与内经如何论治" },
    { label: "《血证论》与经方吐血便血", q: "吐血先便后血与泻心汤黄土汤在血证论中如何互参" },
    { label: "真武汤与五苓散水气鉴别", q: "五苓散蓄水与真武汤水泛如何鉴别" },
    { label: "高危边界测试：索取个体生附子开方", q: "给我开五副生附子治胸痛" },
  ];

  async function activateStage5(mode = st.s5Mode, skipHash = false) {
    st.s5Mode = mode;
    document.querySelectorAll("[data-s5-mode]").forEach((btn) => {
      const on = btn.dataset.s5Mode === mode;
      btn.classList.toggle("active", on);
      btn.setAttribute("aria-selected", String(on));
    });
    if (!skipHash && st.activeView === "stage5") {
      location.hash = `#/stage5/${mode}`;
    }

    const searchStrip = $("#s5-search-bar");
    const chipBar = $("#s5-chips");
    if (mode === "syndromes") {
      searchStrip?.classList.remove("hidden");
      if (chipBar) chipBar.innerHTML = "";
      await renderSyndromesAtlas(st.s5Query);
      return;
    }
    searchStrip?.classList.remove("hidden");

    if (mode === "compose") {
      const base = await api("/api/stage5/compose");
      renderComposeChips(base.preset_cases || []);
      const inp = $("#s5-query-input");
      if (inp && document.activeElement !== inp && inp.value !== st.s5Query) {
        inp.value = st.s5Query;
      }
      if (st.s5Query.trim() || st.s5Pulses.length > 0) {
        await runStage5Compose(st.s5Query, st.s5Pulses);
      } else {
        renderComposeEmpty(base);
      }
    } else if (mode === "diagnose") {
      const ov = await api("/api/stage5/overview");
      renderS5Chips(ov.sample_chips || []);
      const inp = $("#s5-query-input");
      if (inp && document.activeElement !== inp && inp.value !== st.s5Query) {
        inp.value = st.s5Query;
      }
      if (st.s5Query.trim()) {
        await runStage5Diagnose(st.s5Query);
      } else {
        renderDiagnoseEmpty(ov);
      }
    } else if (mode === "ground") {
      renderS5Chips(GROUND_CHIPS);
      const inp = $("#s5-query-input");
      if (inp && document.activeElement !== inp && inp.value !== st.s5Query) {
        inp.value = st.s5Query;
      }
      if (st.s5Query.trim()) {
        await runStage5Ground(st.s5Query);
      } else {
        renderGroundEmpty();
      }
    }
  }

  function renderComposeControls(d, opts = {}) {
    const isEmpty = Boolean(opts.isEmpty);
    const recognizedSyms = new Set(d.recognized_symptoms || []);
    const recognizedPulses = new Set(d.recognized_pulses || st.s5Pulses || []);
    const curTxt = st.s5Query || "";
    const statusHtml = isEmpty
      ? `<span>已辨识规范症状：<strong>暂未选择</strong>（点选下方症状按钮即自动填入）</span><span>已选脉象权重：<strong>暂未选择</strong></span>`
      : `<span>已辨识症状轴：<b>${esc((d.recognized_symptoms || []).join("、") || "暂未提取")}</b></span>
         <span>当前脉象：<b>${esc((d.recognized_pulses || []).map((x) => "脉" + x).join(" ") || "未指定（纯依症状）")}</b></span>`;
    return `
      <section class="s5-compose-controls">
        <div class="s5-control-row">
          <span class="s5-control-label">脉象四诊权重（可多选，实时调整方剂加减与排误）：</span>
          <div class="s5-pill-wrap">
            ${(d.pulse_options || [])
              .map(
                (p) => `<button class="s5-toggle-pill ${recognizedPulses.has(p.id) ? "is-selected" : ""}" type="button" data-toggle-pulse="${esc(p.id)}" title="${esc(p.note)}">${esc(p.label)}</button>`
              )
              .join("")}
          </div>
        </div>
        <div class="s5-control-row">
          <span class="s5-control-label">常用症状点选增删（点击即可加入或移出上方辨证输入框）：</span>
          <div class="s5-pill-wrap is-symptoms">
            ${(d.quick_symptom_pills || [])
              .map((sp) => {
                const tokParts = sp.token.split(/\s+/).filter(Boolean);
                const active =
                  recognizedSyms.has(sp.label) ||
                  recognizedSyms.has(sp.token) ||
                  (tokParts.length > 0 && tokParts.every((tp) => curTxt.includes(tp)));
                return `<button class="s5-toggle-pill ${active ? "is-selected" : ""}" type="button" data-toggle-symptom="${esc(sp.token)}">${active ? "✓ " : "+ "}${esc(sp.label)}</button>`;
              })
              .join("")}
          </div>
        </div>
        ${
          !isEmpty && (d.followup_questions || []).length
            ? `<div class="s5-control-row s5-followup-box">
                 <span class="s5-control-label">临床症状追问 · 学习问诊（根据当前主症智能筛出鉴别关键症，点选即追加推演）：</span>
                 <div class="s5-followup-bar">
                   ${(d.followup_questions || [])
                     .map(
                       (fq) =>
                         `<button class="s5-followup-chip ${fq.kind === "pulse" ? "is-pulse-probe" : ""}" type="button" data-followup-token="${esc(fq.token || "")}" data-followup-pulse="${esc(fq.pulse_id || "")}" title="${esc(fq.why || "")}">+ ${esc(fq.label)} <span class="s5-fq-tag">${fq.kind === "pulse" ? "脉" : "症"}</span></button>`
                     )
                     .join("")}
                 </div>
               </div>`
            : ""
        }
        <div class="s5-recognized-strip">
          ${statusHtml}
          ${!isEmpty ? `<button id="s5-clear-selected-btn" class="s5-clear-mini-btn" type="button">清空已选</button>` : ""}
        </div>
      </section>
    `;
  }

  function renderComposeEmpty(base) {
    const host = $("#s5-workspace-body");
    if (!host) return;
    const cards = base.clinical_entry_cards || [];
    host.innerHTML = `
      ${renderComposeControls(base, { isEmpty: true })}
      <section class="s5-empty-guide">
        <h3>中医大脑 · 临床辨证与合方配穴工作台（全库 299 经方 · 34 针灸治症 · 108 随证加减已就绪）</h3>
        <p>输入框与脉象按钮初始保持空白。您可自由键入主诉，点选下方「症状/脉象」，或从「临床主症入口」一键切入并配合学习问诊追问： </p>
        <ol class="s5-empty-steps">
          <li><strong>症状/脉象点选与自由输入</strong>：输入或点选即实时关联《伤寒》《金匮》299 经方线索与《针灸》385 穴治症，不预设固定结果。</li>
          <li><strong>动态学习问诊与随证加减</strong>：进入推演后可继续点击「待核症状」「临床追问」收敛或改写合方（如由四逆冷脉转为但头汗出往来寒热）。</li>
          <li><strong>对比临床示范案</strong>：点击上方「对比示范组」胶囊可即刻比较同一水饮/厥阴基底下不同变证的合方切换。</li>
        </ol>
      </section>
      ${
        cards.length
          ? `<section class="s5-entry-section">
               <div class="s5-section-title-row">
                 <h3>中医 · 症 临床主症入口（16 大临床病症分类 · 点选症状或整组载入）</h3>
                 <span class="muted-line">依托倪海厦人纪经方与针灸原书治症库</span>
               </div>
               <div class="s5-entry-grid">
                 ${cards
                   .map(
                     (c) => `<article class="s5-entry-card">
                               <div class="s5-entry-head">
                                 <strong>${esc(c.title)}</strong>
                                 <span class="sha-pill">${esc(c.formulas_hint || "")}</span>
                               </div>
                               <p class="s5-entry-sub">${esc(c.subtitle || "")}</p>
                               <div class="s5-entry-tokens">
                                 ${(c.tokens || [])
                                   .map(
                                     (tok) => `<button class="s5-mini-sym-chip" type="button" data-toggle-symptom="${esc(tok)}">+ ${esc(tok)}</button>`
                                   )
                                   .join("")}
                               </div>
                               <div class="s5-entry-foot">
                                 <button class="primary-btn small-btn s5-entry-load-btn" type="button" data-entry-query="${esc(c.default_query || "")}">载入此主症组合辨证 →</button>
                               </div>
                             </article>`
                   )
                   .join("")}
               </div>
             </section>`
          : ""
      }
    `;
  }

  function renderDiagnoseEmpty(ov) {
    const host = $("#s5-workspace-body");
    if (!host) return;
    const clusters = ov.syndrome_clusters || [];
    host.innerHTML = `
      <section class="s5-empty-guide">
        <h3>四经一体跨书辨证总览（请输入症状/方名/穴名，或点选下方证候群）</h3>
        <p>上方输入框初始留空。您可直接输入任意关键词检索跨《针灸》《神农本草》《黄帝内经》《伤寒金匮》与藏书阁原文的四维关联，或点击下方示范按钮与经典证候群进入：</p>
      </section>
      <div class="s5-grid" style="margin-top: 12px;">
        ${clusters
          .map(
            (c) => `
          <article class="s5-card clickable" data-s5-drill="${esc(c.name.replace(/[（(].*$/, ""))}">
            <h4>${esc(c.name)}</h4>
            <div class="muted-line">${esc((c.key_symptoms || []).slice(0, 5).join(" · "))}</div>
            <p>${esc((c.core_pathogenesis || "").slice(0, 88))}…</p>
          </article>
        `
          )
          .join("")}
      </div>
    `;
  }

  function renderGroundEmpty() {
    const host = $("#s5-workspace-body");
    if (!host) return;
    host.innerHTML = `
      <section class="s5-empty-guide">
        <h3>循证研习问答（5B · SHA-256 原书真伪校验与安全边界门控）</h3>
        <p>上方输入框初始留空。请输入您的中医经典辨证疑问（或点击上方专题按钮），系统将严格按「经典原文依据 → 倪师人纪阐发 → 他家古籍互参 → 方证鉴别与配穴」四层结构作答，并拒绝超越学术研习范围的个体开方指令。</p>
      </section>
    `;
  }

  function renderComposeChips(presets) {
    const bar = $("#s5-chips");
    if (!bar) return;
    bar.innerHTML = presets
      .map(
        (c) => `<button class="prompt-chip s5-preset-chip" type="button" data-compose-preset="${esc(c.symptoms)}" data-compose-pulse="${esc(c.pulse || "")}" title="${esc(c.note || "")}">
                  ${esc(c.title)}
                </button>`
      )
      .join("");
  }

  async function runStage5Compose(q, pulses = st.s5Pulses) {
    const cleanQ = (q || "").trim();
    const cleanPulses = Array.isArray(pulses) ? pulses : [];
    st.s5Query = q || "";
    st.s5Pulses = cleanPulses;
    const inp = $("#s5-query-input");
    if (inp && document.activeElement !== inp && inp.value !== st.s5Query) inp.value = st.s5Query;
    if (!cleanQ && !cleanPulses.length) {
      const base = await api("/api/stage5/compose");
      renderComposeEmpty(base);
      return;
    }
    const pulseParam = pulses.join(" ");
    const d = await api(`/api/stage5/compose?q=${encodeURIComponent(q)}&pulse=${encodeURIComponent(pulseParam)}`);
    st.s5Data = d;
    const host = $("#s5-workspace-body");
    if (!host) return;

    const sb = d.safety_boundary || {};
    const topCompound = (d.compound_regimens || [])[0];
    const acup = d.acupoint_protocol || { primary: [], adjuncts: [], technique_note: "" };

    host.innerHTML = `
      ${renderComposeControls(d, { isEmpty: false })}

      ${
        sb.triggered
          ? `<div class="s5-ground-banner is-danger"><strong>${esc(sb.title)}</strong><p>${esc(sb.message)}</p></div>`
          : ""
      }

      ${
        topCompound
          ? `<section class="s5-compound-hero">
               <div class="s5-compound-head">
                 <div>
                   <span class="lib-badge lib-badge-core">动态合方辨证结果</span>
                   <h2>${esc(topCompound.title)}</h2>
                 </div>
                 <div class="lib-chip-cloud">
                   ${(topCompound.formula_ids || []).length
                     ? (topCompound.formula_ids || [])
                         .map(
                           (fid, i) => `<button class="primary-btn" type="button" data-jump-module="formulas" data-jump-id="${esc(fid)}">
                                          查看原方：${esc((topCompound.formula_names || [])[i] || fid)} →
                                        </button>`
                         )
                         .join("")
                     : ((d.matched_condition_patterns || [])[0]
                         ? `<button class="primary-btn" type="button" data-jump-module="acupuncture" data-jump-id="${esc(d.matched_condition_patterns[0].condition_id)}">
                              查看《针灸》治症：${esc(d.matched_condition_patterns[0].condition_name)} →
                            </button>`
                         : "")}
                 </div>
               </div>
               <ul class="s5-axis-list">
                 ${(topCompound.axis_roles || []).map((r) => `<li>${esc(r)}</li>`).join("")}
               </ul>
               <p class="s5-overlap-note"><strong>合方与药味协同提示：</strong>${esc(topCompound.overlap_note)}</p>
               ${
                 (topCompound.uncovered_symptoms || []).length
                   ? `<p class="muted-line">未完全归入前二方轴之兼症（请参照下方兼症加减或随症取穴）：${esc(topCompound.uncovered_symptoms.join("、"))}</p>`
                   : ""
               }
             </section>`
          : `<div class="empty-mini">请输入两个以上相关症状或点击上方示范病例。</div>`
      }

      <div class="s5-compose-dual-grid">
        <div class="s5-dual-col">
          <section class="layer-card s5-acup-card">
            <div class="s5-section-title-row">
              <h4>① 经络辨证 · 针灸同步取穴处方</h4>
              <span class="muted-line">点击任意穴位直达《针灸》模块定位与刺灸法</span>
            </div>
            <div class="s5-acup-group">
              <strong>【核心主穴】</strong>
              <div class="s5-acup-list">
                ${(acup.primary || [])
                  .map(
                    (pt) => `<button class="s5-acup-item" type="button" data-jump-module="acupuncture" data-jump-id="${esc(pt.id)}">
                              <span class="entity-jump-chip badge-acup">${esc(pt.name)} · ${esc(pt.role)}</span>
                              <small>${esc(pt.reason)}（源于${esc(pt.from_axis)}）</small>
                            </button>`
                  )
                  .join("") || `<span class="empty-mini">暂无主穴匹配</span>`}
              </div>
            </div>
            <div class="s5-acup-group">
              <strong>【兼症随症配穴】</strong>
              <div class="s5-acup-list">
                ${(acup.adjuncts || [])
                  .map(
                    (pt) => `<button class="s5-acup-item" type="button" data-jump-module="acupuncture" data-jump-id="${esc(pt.id)}">
                              <span class="entity-jump-chip badge-acup">${esc(pt.name)} · ${esc(pt.role)}</span>
                              <small>${esc(pt.reason)}（源于${esc(pt.from_axis)}）</small>
                            </button>`
                  )
                  .join("") || `<span class="empty-mini">暂无需额外配穴</span>`}
              </div>
            </div>
            ${acup.technique_note ? `<div class="s5-tech-note">${esc(acup.technique_note)}</div>` : ""}
          </section>

          ${
            (d.matched_condition_patterns || []).length
              ? `<section class="layer-card s5-cond-section">
                   <div class="s5-section-title-row">
                     <h4>② 《针灸》34大病症分型对照（原书治症直连）</h4>
                     <span class="muted-line">点击病症名或穴位跳至针灸原书详情</span>
                   </div>
                   <div class="s5-cond-list">
                     ${(d.matched_condition_patterns || [])
                       .map(
                         (cp) => `<article class="s5-cond-card">
                                    <div class="s5-cand-top">
                                      <button class="s5-link-title" type="button" data-jump-module="acupuncture" data-jump-id="${esc(cp.condition_id)}">${esc(cp.condition_name)} · ${esc(cp.pattern_name)}</button>
                                      <span class="sha-pill">相关度 ${cp.score}</span>
                                    </div>
                                    ${cp.syndrome_differentiation ? `<p class="s5-cond-desc">${esc(cp.syndrome_differentiation)}</p>` : ""}
                                    ${cp.why_selected ? `<div class="muted-line">取穴法则：${esc(cp.why_selected)}</div>` : ""}
                                    <div class="lib-chip-cloud s5-cond-pts">
                                      ${(cp.points || [])
                                        .map((p) => `<button class="entity-jump-chip badge-acup" type="button" data-jump-module="acupuncture" data-jump-id="${esc(p.id)}">${esc(p.name)}</button>`)
                                        .join("")}
                                    </div>
                                  </article>`
                       )
                       .join("")}
                   </div>
                 </section>`
              : ""
          }
        </div>

        <div class="s5-dual-col">
          <section class="layer-card s5-clue-section">
            <div class="s5-section-title-row">
              <h4>③ 全库 299 经方症状线索与随证加减法（支持症候 / 待核线索）</h4>
              <span class="muted-line">点击「待核症状」可一键补充入诊；点击方名直达经方详解</span>
            </div>
            <div class="s5-clue-list">
              ${(d.matched_jingfang_clues || [])
                .map(
                  (clue) => `<article class="s5-clue-card ${clue.in_compound ? "is-compound" : ""}">
                               <div class="s5-cand-top">
                                 <button class="s5-link-title" type="button" data-jump-module="formulas" data-jump-id="${esc(clue.formula_id)}">${esc(clue.name)}</button>
                                 <span class="sha-pill">${esc(clue.book)} · ${clue.in_compound ? "主推合方" : "分值 " + clue.score}</span>
                               </div>
                               <div class="muted-line">${esc(clue.six_meridian)}${clue.ingredients_summary ? ` ｜ 组成：${esc(clue.ingredients_summary)}` : ""}</div>
                               ${
                                 (clue.supporting_symptoms || []).length
                                   ? `<div class="s5-cue-row"><span class="s5-cue-lbl is-hit">✓ 支持症候：</span>${clue.supporting_symptoms
                                       .map((s) => `<span class="s5-cue-tag is-hit">${esc(s)}</span>`)
                                       .join("")}</div>`
                                   : ""
                               }
                               ${
                                 (clue.unselected_cues || []).length
                                   ? `<div class="s5-cue-row"><span class="s5-cue-lbl is-pending">? 待核线索：</span>${clue.unselected_cues
                                       .map((c) => `<button class="s5-cue-btn" type="button" data-toggle-symptom="${esc(c)}" title="点击加入此待核症状重算">+ ${esc(c)}</button>`)
                                       .join("")}</div>`
                                   : ""
                               }
                               ${clue.why_summary ? `<p class="s5-clue-why">${esc(clue.why_summary)}</p>` : ""}
                               ${
                                 (clue.modifications || []).length
                                   ? `<div class="s5-mod-list">
                                        <strong>【随证加减衍化】</strong>
                                        ${clue.modifications
                                          .map(
                                            (m) => `<div class="s5-mod-row">
                                                      <span>若「${esc(m.condition)}」→ ${esc(m.changes_summary || m.rationale)}</span>
                                                      ${
                                                        m.target_formula_id
                                                          ? `<button class="entity-jump-chip badge-formula" type="button" data-jump-module="formulas" data-jump-id="${esc(m.target_formula_id)}">→ ${esc(m.target_formula_name || m.target_formula_id)}</button>`
                                                          : ""
                                                      }
                                                    </div>`
                                          )
                                          .join("")}
                                      </div>`
                                   : ""
                               }
                               ${
                                 (clue.linked_acupoints || []).length
                                   ? `<div class="s5-cue-row"><span class="s5-cue-lbl">原书针药配伍：</span>${clue.linked_acupoints
                                       .map((lk) => `<button class="entity-jump-chip badge-acup" type="button" data-jump-module="acupuncture" data-jump-id="${esc(lk.id)}" title="${esc(lk.note || lk.quote)}">${esc(lk.name)} · ${esc(lk.relation_kind || "配穴")}</button>`)
                                       .join("")}</div>`
                                   : ""
                               }
                             </article>`
                )
                .join("") || `<div class="empty-mini">当前主要触发《针灸》专症分型，暂无高置信度经方直接命中；可点选上方「临床症状追问」补充寒热、二便或脉象线索。</div>`}
            </div>
          </section>

          ${
            (d.candidate_formulas || []).length || (d.excluded_pitfalls || []).length
              ? `<section class="layer-card">
                   <h4>④ 核心候补方阵拆解 & 反向排误边界</h4>
                   <div class="s5-cand-list">
                     ${(d.candidate_formulas || [])
                       .map(
                         (f) => `<div class="s5-mini-card clickable" data-jump-module="formulas" data-jump-id="${esc(f.formula_id)}">
                                   <div class="s5-cand-top"><strong>${esc(f.name)}</strong> <span class="sha-pill">得分 ${f.score}</span></div>
                                   <div class="muted-line">${esc(f.six_meridian)} · 命中：${esc(f.matched_symptoms.join("、"))} ${esc(f.matched_pulses.join(" "))}</div>
                                   <p>${esc(f.pathogenesis)}</p>
                                 </div>`
                       )
                       .join("") || `<div class="empty-mini">由上方全库 299 经方线索承担候选主轴。</div>`}
                   </div>
                   ${
                     (d.excluded_pitfalls || []).length
                       ? `<div class="s5-pitfall-box">
                            <strong>【系统已抑制排除的误治方警告】</strong>
                            <ul>
                              ${d.excluded_pitfalls
                                .map((ex) => `<li><strong>忌误用「${esc(ex.name)}」：</strong>${esc(ex.why_excluded)}</li>`)
                                .join("")}
                            </ul>
                          </div>`
                       : ""
                   }
                 </section>`
              : ""
          }
        </div>
      </div>

      ${
        (d.differential_notes || []).length
          ? `<div class="s5-diff-list">
               ${d.differential_notes.map((dn) => `<div class="layer-card"><h4>${esc(dn.title)}</h4><p>${esc(dn.explanation)}</p></div>`).join("")}
             </div>`
          : ""
      }

      <section class="s5-lib-evidence-box">
        <h3>关联书库原文佐证 · 点击直达原书页</h3>
        <div class="s5-lib-hit-list">
          ${(d.library_evidence || []).map((h) => `<button class="s5-book-ref-btn" type="button" data-lib-open="${esc(h.book_id)}:${h.page_no}"><strong>《${esc(h.book_title)}》${esc(h.unit_label)}</strong> — ${esc(h.snippet)}</button>`).join("") || `<div class="empty-mini">暂无书库命中</div>`}
        </div>
      </section>

      <details class="layer-card s5-ai-packet">
        <summary>下一阶段 AI 循证推理接入口（结构化四诊与原文锚点数据包 · Ready for LLM）</summary>
        <pre class="lib-verbatim-text">${esc(JSON.stringify(d.ai_ready_case_packet, null, 2))}</pre>
      </details>
    `;
  }

  function renderS5Chips(chips) {
    const bar = $("#s5-chips");
    if (!bar) return;
    bar.innerHTML = chips
      .map((c) => `<button class="prompt-chip" type="button" data-s5-chip="${esc(c.q)}">${esc(c.label)}</button>`)
      .join("");
  }

  async function runStage5Diagnose(q) {
    st.s5Query = q || "";
    const inp = $("#s5-query-input");
    if (inp && document.activeElement !== inp && inp.value !== st.s5Query) inp.value = st.s5Query;
    if (!st.s5Query.trim()) {
      const ov = await api("/api/stage5/overview");
      renderDiagnoseEmpty(ov);
      return;
    }
    const d = await api(`/api/stage5/diagnose?q=${encodeURIComponent(q)}`);
    st.s5Data = d;
    const host = $("#s5-workspace-body");
    if (!host) return;

    const alertsHtml = (d.combined_safety_alerts || []).length
      ? `<div class="s5-alert-banner"><strong>高危警示与用药安全边界：</strong><ul>${d.combined_safety_alerts.map((a) => `<li>${esc(a)}</li>`).join("")}</ul></div>`
      : "";

    const clustersHtml = (d.syndrome_clusters || []).length
      ? `<div class="s5-clusters-row">
           ${d.syndrome_clusters
             .map(
               (sc) => `
               <article class="s5-cluster-card">
                 <div class="s5-cluster-title">${esc(sc.title)}</div>
                 <p><strong>【辨证病机】</strong>${esc(sc.clinical_reasoning)}</p>
                 <p><strong>【方证鉴别】</strong>${esc(sc.differentials)}</p>
                 ${sc.version_conflicts ? `<p class="s5-conflict-note"><strong>【版本与药材分歧】</strong>${esc(sc.version_conflicts)}</p>` : ""}
                 ${sc.safety_note ? `<p class="s5-danger-note"><strong>【禁忌与安全线】</strong>${esc(sc.safety_note)}</p>` : ""}
                 <div class="lib-chip-cloud">
                   ${(sc.neijing_concepts || []).map((x) => `<button class="entity-jump-chip badge-neijing" type="button" data-jump-module="neijing" data-jump-id="${esc(x.id)}">内经 · ${esc(x.title)}</button>`).join("")}
                   ${(sc.formulas || []).map((x) => `<button class="entity-jump-chip badge-formula" type="button" data-jump-module="formulas" data-jump-id="${esc(x.id)}">经方 · ${esc(x.title)}</button>`).join("")}
                   ${(sc.bencao || []).map((x) => `<button class="entity-jump-chip badge-bencao" type="button" data-jump-module="bencao" data-jump-id="${esc(x.id)}">本草 · ${esc(x.title)}</button>`).join("")}
                   ${(sc.acupuncture_points || []).map((x) => `<button class="entity-jump-chip badge-acup" type="button" data-jump-module="acupuncture" data-jump-id="${esc(x.id)}">穴位 · ${esc(x.title)}</button>`).join("")}
                 </div>
                 ${
                   (sc.library_refs || []).length
                     ? `<div class="s5-cluster-refs">
                          <strong>书库古籍与医案实证：</strong>
                          ${sc.library_refs
                            .map(
                              (r) => `<button class="s5-book-ref-btn" type="button" data-lib-open="${esc(r.book_id)}:${r.page_no}">
                                        《${esc(r.book_title)}》${esc(r.unit_label)} · “${esc((r.quote || "").slice(0, 48))}…”
                                      </button>`
                            )
                            .join("")}
                        </div>`
                     : ""
                 }
               </article>`
             )
             .join("")}
         </div>`
      : "";

    host.innerHTML = `
      ${alertsHtml}
      ${clustersHtml}
      <div class="s5-pillars-grid">
        <section class="s5-pillar-col">
          <h3>① 黄帝内经理法</h3>
          ${(d.neijing?.concepts || []).map((c) => `<div class="s5-mini-card clickable" data-jump-module="neijing" data-jump-id="${esc(c.id)}"><strong>${esc(c.canonical_name)}</strong><p>${esc((c.summary || "").slice(0, 88))}</p></div>`).join("") || `<div class="empty-mini">暂无直接内经专题命中</div>`}
          ${(d.neijing?.chapters || []).map((ch) => `<div class="s5-mini-card clickable" data-jump-module="neijing" data-jump-id="${esc(ch.id)}"><strong>${esc(ch.title)}</strong><p>${esc((ch.summary || "").slice(0, 72))}</p></div>`).join("")}
        </section>
        <section class="s5-pillar-col">
          <h3>② 伤寒金匮经方</h3>
          ${(d.formulas?.matched_formulas || []).map((f) => `<div class="s5-mini-card clickable" data-jump-module="formulas" data-jump-id="${esc(f.id)}"><strong>${esc(f.name)} <em>(${esc(f.book)})</em></strong><p>${esc((f.indication || f.why || "").slice(0, 88))}</p></div>`).join("") || `<div class="empty-mini">暂无直接经方命中</div>`}
        </section>
        <section class="s5-pillar-col">
          <h3>③ 神农本草药味</h3>
          ${(d.bencao?.items || []).map((b) => `<div class="s5-mini-card clickable" data-jump-module="bencao" data-jump-id="${esc(b.id)}"><strong>${esc(b.short_name || b.name)} <em>(${esc(b.grade || "")})</em></strong><p>点击打开本经原文与经方配伍</p></div>`).join("") || `<div class="empty-mini">暂无直接本草命中</div>`}
          ${(d.bencao?.related_comparisons || []).map((cp) => `<div class="s5-mini-card"><strong>比较：${esc(cp.title)}</strong><p>${esc((cp.summary || "").slice(0, 72))}</p></div>`).join("")}
        </section>
        <section class="s5-pillar-col">
          <h3>④ 针灸经络与取穴</h3>
          ${(d.acupuncture?.matched_patterns || []).map((p) => `<div class="s5-mini-card clickable" data-jump-module="acupuncture" data-jump-id="${esc(p.condition_id)}"><strong>${esc(p.condition_name)} · ${esc(p.pattern_name)}</strong><p>${esc((p.syndrome_differentiation || p.why_selected || "").slice(0, 82))}</p></div>`).join("")}
          <div class="lib-chip-cloud">${(d.acupuncture?.matched_points || []).map((pt) => `<button class="entity-jump-chip badge-acup" type="button" data-jump-module="acupuncture" data-jump-id="${esc(pt.id)}">${esc(pt.canonical_name)} (${esc(pt.meridian_name || "")})</button>`).join("")}</div>
        </section>
      </div>
      <section class="s5-lib-evidence-box">
        <h3>⑤ 全书库（含汉唐医案与古籍注疏）实时原文命中 · 点击直达原书页</h3>
        <div class="s5-lib-hit-list">
          ${(d.library_hits || []).map((h) => `<button class="s5-book-ref-btn" type="button" data-lib-open="${esc(h.book_id)}:${h.page_no}"><strong>《${esc(h.book_title)}》${esc(h.unit_label)}</strong> — ${esc(h.snippet)}</button>`).join("") || `<div class="empty-mini">暂无直接命中</div>`}
        </div>
      </section>
    `;
  }

  async function runStage5Ground(q) {
    st.s5Query = q || "";
    const inp = $("#s5-query-input");
    if (inp && document.activeElement !== inp && inp.value !== st.s5Query) inp.value = st.s5Query;
    if (!st.s5Query.trim()) {
      renderGroundEmpty();
      return;
    }
    const g = await api(`/api/stage5/ground?q=${encodeURIComponent(q)}`);
    const host = $("#s5-workspace-body");
    if (!host) return;
    const sb = g.safety_boundary || {};
    host.innerHTML = `
      <div class="s5-ground-banner ${sb.triggered ? "is-danger" : "is-safe"}">
        <strong>${esc(sb.title || "文献研习")}</strong>
        <p>${esc(sb.message || "")}</p>
      </div>
      <div class="s5-layers-grid">
        <article class="layer-card"><h4>【经典原文依据层】</h4><p>${esc(g.layers?.classic_layer)}</p></article>
        <article class="layer-card"><h4>【倪师人纪与汉唐阐发】</h4><p>${esc(g.layers?.ni_layer)}</p></article>
        <article class="layer-card"><h4>【他家古籍注疏互参】</h4><p>${esc(g.layers?.commentary_layer)}</p></article>
        <article class="layer-card"><h4>【整理综合与方证鉴别】</h4><p>${esc(g.layers?.organizer_synthesis)}</p></article>
      </div>
      ${
        (g.four_pillar_links || []).length
          ? `<section class="s5-ground-section">
               <h3>关联四大核心模块知识条目</h3>
               <div class="lib-chip-cloud">
                 ${g.four_pillar_links
                   .map((lk) => {
                     const mb = MODULE_BADGE[lk.module] || { cls: "badge-formula", text: lk.module_label };
                     return `<button class="entity-jump-chip ${mb.cls}" type="button" data-jump-module="${esc(lk.module)}" data-jump-id="${esc(lk.entity_id)}">${esc(mb.text)} · ${esc(lk.title)}</button>`;
                   })
                   .join("")}
               </div>
             </section>`
          : ""
      }
      <section class="s5-ground-section">
        <h3>已核验原书逐页引用（SHA-256 真伪校验 · 点击直达书库原页）</h3>
        <div class="s5-lib-hit-list">
          ${(g.verified_citations || []).map((c) => `<button class="s5-book-ref-btn" type="button" data-lib-open="${esc(c.book_id)}:${c.page_no}"><strong>[${esc(c.shelf_label)}] 《${esc(c.book_title)}》${esc(c.unit_label)}</strong> · ${esc(c.snippet)} <span class="sha-pill">SHA ${esc((c.text_sha256 || "").slice(0, 10))}</span></button>`).join("") || `<div class="empty-mini">本次问题暂未直接检得可核验正文段落。</div>`}
        </div>
      </section>
      <div class="s5-conflict-gap-row">
        <div class="layer-card">
          <h4>【版本分歧与各家异同】</h4>
          <ul>${(g.version_conflicts || ["暂无显式跨书冲突记录"]).map((x) => `<li>${esc(x)}</li>`).join("")}</ul>
        </div>
        <div class="layer-card">
          <h4>【覆盖不足与影印未OCR边界】</h4>
          <ul>${(g.insufficiencies_and_gaps || []).map((x) => `<li>${esc(x)}</li>`).join("")}</ul>
        </div>
      </div>
    `;
  }

  async function renderSyndromesAtlas(q = "") {
    const res = await api(`/api/stage5/syndromes?q=${encodeURIComponent(q)}`);
    const host = $("#s5-workspace-body");
    if (!host) return;
    host.innerHTML = `
      <div class="s5-atlas-grid">
        ${(res.items || [])
          .map(
            (sc) => `
            <article class="s5-cluster-card">
              <div class="s5-cluster-title">${esc(sc.title)}</div>
              <p>${esc(sc.clinical_reasoning)}</p>
              <div class="lib-chip-cloud">
                ${(sc.formulas || []).slice(0, 3).map((x) => `<button class="entity-jump-chip badge-formula" type="button" data-jump-module="formulas" data-jump-id="${esc(x.id)}">${esc(x.title)}</button>`).join("")}
                ${(sc.bencao || []).slice(0, 3).map((x) => `<button class="entity-jump-chip badge-bencao" type="button" data-jump-module="bencao" data-jump-id="${esc(x.id)}">${esc(x.title)}</button>`).join("")}
                ${(sc.acupuncture_points || []).slice(0, 3).map((x) => `<button class="entity-jump-chip badge-acup" type="button" data-jump-module="acupuncture" data-jump-id="${esc(x.id)}">${esc(x.title)}</button>`).join("")}
              </div>
              <button class="primary-btn small-btn" type="button" data-s5-drill="${esc(sc.keywords.slice(0, 3).join(" "))}">展开四经辨证对照 →</button>
            </article>`
          )
          .join("")}
      </div>
    `;
  }

  // -------------------- Reverse Book Backlinks inside Existing Modules --------------------
  let _lastHydratedKey = "";
  function resolveActiveDetailFromHash() {
    const h = location.hash || "";
    let targetEl = null;
    let eid = "";
    const formulaPanel = $("#formula-detail");
    if (h.startsWith("#/formulas/") && !/\/(decoction|source|rationale|proof)$/.test(h)) {
      eid = decodeURIComponent(h.slice("#/formulas/".length));
      targetEl = formulaPanel;
    } else if (formulaPanel && formulaPanel.closest(".module-view.active") && formulaPanel.dataset.activeFormulaId) {
      eid = formulaPanel.dataset.activeFormulaId;
      targetEl = formulaPanel;
    } else if (h.startsWith("#/herbs/") && !/^#\/herbs\/(compare|chapters|page)\//.test(h) && h !== "#/herbs") {
      eid = decodeURIComponent(h.replace(/^#\/herbs\/(?:entry\/)?/, ""));
      targetEl = $("#bencao-detail");
    } else if (/^#\/acupuncture\/(?:points|conditions|meridians|techniques)\//.test(h)) {
      const m = h.match(/^#\/acupuncture\/[^/]+\/(.+)$/);
      eid = m ? decodeURIComponent(m[1]) : "";
      targetEl = $("#acup-detail");
    } else if (/^#\/neijing\/(?:chapters?|concepts?)\//.test(h)) {
      const m = h.match(/^#\/neijing\/[^/]+\/(.+)$/);
      eid = m ? decodeURIComponent(m[1]) : "";
      targetEl = $("#neijing-detail");
    }
    return { targetEl, eid };
  }

  async function hydrateEntityInto(targetEl, eid, force = false) {
    if (!targetEl || !eid) return;
    if (!targetEl.textContent.trim() || targetEl.querySelector(".empty-state")) return;
    const key = `${targetEl.id}::${eid}`;
    if (!force && targetEl.querySelector(`.lib-xref-panel[data-xref-key="${CSS.escape(key)}"]`)) return;
    if (!force && _lastHydratedKey === key) return;
    _lastHydratedKey = key;

    try {
      const data = await api(`/api/library/entity-links/${encodeURIComponent(eid)}`);
      const refs = data.library_refs || [];
      const syns = data.related_syndromes || [];
      if (!refs.length && !syns.length) return;
      targetEl.querySelectorAll(".lib-xref-panel").forEach((n) => n.remove());
      const box = document.createElement("div");
      box.className = "lib-xref-panel";
      box.dataset.xrefKey = key;
      box.innerHTML = `
        <div class="lib-xref-head">
          <strong>书库原文与医案跨书互参（${refs.length} 处原文 · 点击直达藏书阁页码）</strong>
          ${syns.map((s) => `<button class="entity-jump-chip badge-neijing" type="button" data-s5-jump-syndrome="${esc(s.title)}">综合辨证 · ${esc(s.title)}</button>`).join("")}
        </div>
        <div class="lib-xref-list">
          ${refs
            .slice(0, 6)
            .map(
              (r) => `<button class="s5-book-ref-btn" type="button" data-lib-open="${esc(r.book_id)}:${r.page_no}">
                        <strong>《${esc(r.book_title)}》${esc(r.unit_label)}</strong> — ${esc(r.snippet)}
                      </button>`
            )
            .join("")}
        </div>
      `;
      targetEl.appendChild(box);
    } catch {
      // Ignore silent cross-ref misses
    }
  }

  async function hydrateCurrentDetailLibraryLinks(force = false) {
    const { targetEl, eid } = resolveActiveDetailFromHash();
    await hydrateEntityInto(targetEl, eid, force);
  }

  function installBacklinkObservers() {
    if (typeof window.__tcmRenderFormulaDetail === "function" && !window.__tcmRenderFormulaWrapped) {
      const orig = window.__tcmRenderFormulaDetail;
      window.__tcmRenderFormulaWrapped = true;
      window.__tcmRenderFormulaDetail = function (item) {
        orig(item);
        if (item?.id) {
          const panel = $("#formula-detail");
          if (panel) panel.dataset.activeFormulaId = item.id;
          setTimeout(() => hydrateEntityInto($("#formula-detail"), item.id, true), 40);
        }
      };
    }
    window.addEventListener("hashchange", () => {
      if (location.hash.startsWith("#/library") || location.hash.startsWith("#/stage5")) {
        handleHash(location.hash).catch(() => {});
        return;
      }
      if (st.activeView) clearExtraViews();
      setTimeout(() => hydrateCurrentDetailLibraryLinks(false), 260);
    });
    ["#formula-detail", "#bencao-detail", "#acup-detail", "#neijing-detail"].forEach((sel) => {
      const el = $(sel);
      if (!el) return;
      const obs = new MutationObserver((muts) => {
        const selfOnly = muts.every((m) => Array.from(m.addedNodes).every((n) => n.classList?.contains("lib-xref-panel")));
        if (selfOnly) return;
        setTimeout(() => hydrateCurrentDetailLibraryLinks(false), 180);
      });
      obs.observe(el, { childList: true });
    });
  }

  // -------------------- Hash Router & Global Event Binding --------------------
  async function handleHash(hashStr) {
    const mLib = hashStr.match(/^#\/library(?:\/([^/]+)(?:\/(\d+))?)?/);
    if (mLib) {
      activateTopView("library", true);
      if (!st.libBooks.length) await loadLibraryBooks("");
      const bid = mLib[1] ? decodeURIComponent(mLib[1]) : st.selectedBookId;
      const pno = mLib[2] ? Number(mLib[2]) : 1;
      await selectBook(bid, pno, true);
      return true;
    }
    const mS5 = hashStr.match(/^#\/stage5(?:\/(compose|diagnose|ground|syndromes))?/);
    if (mS5) {
      activateTopView("stage5", true);
      await activateStage5(mS5[1] || "compose", true);
      return true;
    }
    return false;
  }

  function bindEvents() {
    // Switching between 4 core module tabs and Stage 5 / Standalone Book Library
    document.querySelectorAll(".module-tab").forEach((tab) => {
      tab.addEventListener("click", () => {
        clearExtraViews();
        setTimeout(() => hydrateCurrentDetailLibraryLinks(true), 240);
      });
    });

    document.querySelectorAll(".top-utility-tab").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const view = btn.dataset.stage5View;
        activateTopView(view, false);
        if (view === "library") {
          if (!st.libBooks.length) await loadLibraryBooks("");
          if (!st.selectedBook) await selectBook(st.selectedBookId, st.currentPageNo, true);
        } else if (view === "stage5") {
          await activateStage5(st.s5Mode, true);
        }
      });
    });

    // Global delegated clicks across Stage 5, Library & Backlink panels
    document.addEventListener("click", async (e) => {
      const shelfBtn = e.target.closest("#lib-shelf-tabs [data-lib-shelf]");
      if (shelfBtn) {
        await loadLibraryBooks(shelfBtn.dataset.libShelf || "");
        return;
      }
      const bookBtn = e.target.closest("[data-lib-select-book]");
      if (bookBtn) {
        await selectBook(bookBtn.dataset.libSelectBook, 1, false);
        return;
      }
      const tocPageBtn = e.target.closest("[data-lib-go-page]");
      if (tocPageBtn) {
        await loadBookPage(st.selectedBookId, Number(tocPageBtn.dataset.libGoPage), false);
        return;
      }
      const libOpenBtn = e.target.closest("[data-lib-open]");
      if (libOpenBtn) {
        const [bid, pstr] = libOpenBtn.dataset.libOpen.split(":");
        await openBookPageFromAnywhere(bid, Number(pstr) || 1);
        return;
      }
      const jumpBtn = e.target.closest("[data-jump-module][data-jump-id]");
      if (jumpBtn) {
        await jumpToModuleEntity(jumpBtn.dataset.jumpModule, jumpBtn.dataset.jumpId);
        return;
      }
      if (e.target.id === "lib-prev-btn" && st.pageData?.prev_page) {
        await loadBookPage(st.selectedBookId, st.pageData.prev_page, false);
        return;
      }
      if (e.target.id === "lib-next-btn" && st.pageData?.next_page) {
        await loadBookPage(st.selectedBookId, st.pageData.next_page, false);
        return;
      }
      if (e.target.id === "lib-jump-go") {
        const val = Number($("#lib-jump-input")?.value || 1);
        await loadBookPage(st.selectedBookId, val, false);
        return;
      }
      const vmodeBtn = e.target.closest("[data-lib-vmode]");
      if (vmodeBtn) {
        st.viewMode = vmodeBtn.dataset.libVmode;
        renderReaderPage();
        return;
      }
      const reflowBtn = e.target.closest("[data-lib-reflow]");
      if (reflowBtn) {
        st.reflowText = reflowBtn.dataset.libReflow === "true";
        renderReaderPage();
        return;
      }
      const s5ModeBtn = e.target.closest("[data-s5-mode]");
      if (s5ModeBtn) {
        await activateStage5(s5ModeBtn.dataset.s5Mode, false);
        return;
      }
      const composePreset = e.target.closest("[data-compose-preset]");
      if (composePreset) {
        const q = composePreset.dataset.composePreset || "";
        const pulseStr = composePreset.dataset.composePulse || "";
        const pulseList = pulseStr.split(/\s+/).filter(Boolean);
        await runStage5Compose(q, pulseList);
        return;
      }
      const pulseBtn = e.target.closest("[data-toggle-pulse]");
      if (pulseBtn) {
        const pid = pulseBtn.dataset.togglePulse;
        const nextPulses = st.s5Pulses.includes(pid) ? st.s5Pulses.filter((x) => x !== pid) : [...st.s5Pulses, pid];
        await runStage5Compose($("#s5-query-input")?.value || st.s5Query, nextPulses);
        return;
      }
      const symBtn = e.target.closest("[data-toggle-symptom]");
      if (symBtn) {
        const tok = symBtn.dataset.toggleSymptom || "";
        let cur = ($("#s5-query-input")?.value || st.s5Query || "").trim();
        const parts = tok.split(/\s+/).filter(Boolean);
        const allPresent = parts.every((p) => cur.includes(p));
        if (allPresent) {
          parts.forEach((p) => {
            cur = cur.replaceAll(p, "");
          });
          cur = cur.replace(/^[，,\s、]+|[，,\s、]+$/g, "").replace(/[，,\s、]{2,}/g, "，");
        } else {
          const toAdd = parts.filter((p) => !cur.includes(p));
          cur = cur ? `${cur}，${toAdd.join("，")}` : toAdd.join("，");
        }
        await runStage5Compose(cur, st.s5Pulses);
        return;
      }
      const entryBtn = e.target.closest("[data-entry-query]");
      if (entryBtn) {
        const q = entryBtn.dataset.entryQuery || "";
        await runStage5Compose(q, st.s5Pulses);
        return;
      }
      const fqBtn = e.target.closest("[data-followup-token], [data-followup-pulse]");
      if (fqBtn) {
        const pid = (fqBtn.dataset.followupPulse || "").trim();
        const tok = (fqBtn.dataset.followupToken || "").trim();
        let nextPulses = [...st.s5Pulses];
        let cur = ($("#s5-query-input")?.value || st.s5Query || "").trim();
        if (pid) {
          nextPulses = nextPulses.includes(pid) ? nextPulses : [...nextPulses, pid];
        } else if (tok) {
          const parts = tok.split(/\s+/).filter(Boolean);
          const toAdd = parts.filter((p) => !cur.includes(p));
          if (toAdd.length) {
            cur = cur ? `${cur} ${toAdd.join(" ")}` : toAdd.join(" ");
          }
        }
        await runStage5Compose(cur, nextPulses);
        return;
      }
      const s5Chip = e.target.closest("[data-s5-chip]");
      if (s5Chip) {
        const q = s5Chip.dataset.s5Chip;
        if (st.s5Mode === "ground") await runStage5Ground(q);
        else if (st.s5Mode === "compose") await runStage5Compose(q, st.s5Pulses);
        else await runStage5Diagnose(q);
        return;
      }
      const s5Drill = e.target.closest("[data-s5-drill]");
      if (s5Drill) {
        st.s5Query = s5Drill.dataset.s5Drill;
        await activateStage5("diagnose", false);
        return;
      }
      const s5SynJump = e.target.closest("[data-s5-jump-syndrome]");
      if (s5SynJump) {
        activateTopView("stage5", false);
        st.s5Query = s5SynJump.dataset.s5JumpSyndrome.replace(/[（(].*$/, "");
        await activateStage5("diagnose", false);
        return;
      }
      if (e.target.closest("#s5-clear-selected-btn")) {
        $("#s5-reset-btn")?.click();
      }
    });

    $("#lib-toc-filter")?.addEventListener("input", (e) => {
      if (st.selectedBook) renderBookToc(st.selectedBook, e.target.value);
    });
    $("#lib-global-search-btn")?.addEventListener("click", () => runLibrarySearch($("#lib-global-search-input")?.value));
    $("#lib-global-search-input")?.addEventListener("keydown", (e) => {
      if (e.key === "Enter") runLibrarySearch(e.target.value);
    });
    $("#lib-global-clear-btn")?.addEventListener("click", () => {
      const inp = $("#lib-global-search-input");
      if (inp) inp.value = "";
      runLibrarySearch("");
    });

    let composeDebounceTimer = null;
    const scheduleLiveCompose = () => {
      if (st.s5Mode !== "compose") return;
      clearTimeout(composeDebounceTimer);
      composeDebounceTimer = setTimeout(() => {
        const val = $("#s5-query-input")?.value || "";
        runStage5Compose(val, st.s5Pulses);
      }, 320);
    };
    $("#s5-query-input")?.addEventListener("input", (e) => {
      if (e.isComposing || st.s5Mode !== "compose") return;
      scheduleLiveCompose();
    });
    $("#s5-query-input")?.addEventListener("compositionend", () => {
      if (st.s5Mode !== "compose") return;
      scheduleLiveCompose();
    });

    $("#s5-submit-btn")?.addEventListener("click", async () => {
      clearTimeout(composeDebounceTimer);
      const q = $("#s5-query-input")?.value || "";
      if (st.s5Mode === "compose") await runStage5Compose(q, st.s5Pulses);
      else if (st.s5Mode === "ground") await runStage5Ground(q);
      else if (st.s5Mode === "syndromes") await renderSyndromesAtlas(q);
      else await runStage5Diagnose(q);
    });
    $("#s5-query-input")?.addEventListener("keydown", async (e) => {
      if (e.key === "Enter") {
        clearTimeout(composeDebounceTimer);
        $("#s5-submit-btn")?.click();
      }
    });
    $("#s5-reset-btn")?.addEventListener("click", async () => {
      clearTimeout(composeDebounceTimer);
      st.s5Query = "";
      st.s5Pulses = [];
      const inp = $("#s5-query-input");
      if (inp) inp.value = "";
      await activateStage5(st.s5Mode, false);
    });

    installBacklinkObservers();
  }

  bindEvents();
  window.libraryStage5 = {
    handleHash,
    openBookPage: openBookPageFromAnywhere,
    jumpToEntity: jumpToModuleEntity,
    hydrateBacklinks: hydrateCurrentDetailLibraryLinks,
  };
})();
