const state = {
  view: "formulas",
  formulaQuery: "",
  formulaType: "",
  formulaMeridian: "",
  formulaPage: 1,
  formulaTotal: 0,
  formulaItems: [],
  selectedFormula: null,
  herbQuery: "",
  herbCategory: "",
  herbPage: 1,
  herbTotal: 0,
  herbItems: [],
  selectedHerb: null,
};

const $ = (selector) => document.querySelector(selector);

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

async function request(path) {
  const response = await fetch(path);
  if (!response.ok) throw new Error("本地数据读取失败");
  return response.json();
}

function showNotice(message) {
  const node = $("#notice");
  node.textContent = message;
  node.classList.remove("hidden");
  window.clearTimeout(showNotice.timer);
  showNotice.timer = window.setTimeout(() => node.classList.add("hidden"), 2800);
}

function setView(view) {
  state.view = view;
  document.querySelectorAll(".module-tab").forEach((button) => {
    const active = button.dataset.view === view;
    button.classList.toggle("active", active);
    button.setAttribute("aria-selected", active ? "true" : "false");
  });
  document.querySelectorAll(".module-view").forEach((node) => {
    node.classList.toggle("active", node.id === `${view}-view`);
  });
  if (view === "herbs" && !state.herbItems.length) loadHerbs(true);
}

function listItem({ id, name, type, six_meridian, ingredient_count, source_line, page }, selected, kind) {
  const selectedClass = selected ? " selected" : "";
  const meta = kind === "herb"
    ? `<span>本经 ${escapeHtml(page)} 页</span>`
    : `<span>${escapeHtml(type)}</span><span>${escapeHtml(six_meridian || "未分篇")}</span><span>${escapeHtml(ingredient_count)} 味</span><span>行 ${escapeHtml(source_line)}</span>`;
  return `<button class="entity-item${selectedClass}" data-kind="${kind}" data-id="${encodeURIComponent(id)}">
    <span class="entity-name"><strong>${escapeHtml(name)}</strong><em>${kind === "herb" ? "本经" : escapeHtml(type)}</em></span>
    <span class="entity-meta">${meta}</span>
  </button>`;
}

function renderFormulaList() {
  const selectedId = state.selectedFormula?.id;
  $("#formula-list").innerHTML = state.formulaItems.map((item) =>
    listItem(item, selectedId === item.id, "formula")
  ).join("") || `<div class="loading">没有匹配的方剂。</div>`;
  $("#formula-count").textContent = `${state.formulaTotal} 首`;
  $("#formula-more").classList.toggle("hidden", state.formulaItems.length >= state.formulaTotal);
}

function renderHerbList() {
  const selectedId = state.selectedHerb?.id;
  $("#herb-list").innerHTML = state.herbItems.map((item) =>
    listItem(item, selectedId === item.id, "herb")
  ).join("") || `<div class="loading">没有匹配的中药。</div>`;
  $("#herb-count").textContent = `${state.herbTotal} 味`;
  $("#herb-more").classList.toggle("hidden", state.herbItems.length >= state.herbTotal);
}

function ingredientHtml(item) {
  const name = item.herb_id
    ? `<button class="ingredient-link" data-herb-id="${encodeURIComponent(item.herb_id)}">${escapeHtml(item.name)}</button>`
    : escapeHtml(item.name);
  return `<div class="ingredient">
    <div class="ingredient-name">${name}</div>
    <div class="ingredient-dose">${escapeHtml(item.dose || "剂量见原文")}</div>
    <div class="ingredient-processing">${escapeHtml(item.processing || "未注炮制")}</div>
  </div>`;
}

function renderFormulaDetail(item) {
  const source = item.source || {};
  const mismatch = item.source_expected_count !== item.ingredients.length;
  const related = item.related_herbs?.length
    ? `<div class="tag-row">${item.related_herbs.map((herb) =>
        `<button class="tag" data-herb-id="${encodeURIComponent(herb.id)}">${escapeHtml(herb.name)}</button>`
      ).join("")}</div>`
    : "";
  const adjuncts = item.adjuncts?.length
    ? `<div class="section-block"><div class="section-title">煎服辅料</div><div class="composition-grid">${item.adjuncts.map((item) =>
        `<div class="ingredient"><div class="ingredient-name">${escapeHtml(item.name)}</div><div class="ingredient-dose">${escapeHtml(item.dose)}</div><div class="ingredient-processing">${escapeHtml(item.role)}</div></div>`
      ).join("")}</div></div>`
    : "";
  const variant = mismatch
    ? `<div class="warning-box">原文校注与当前整理组成有差异。${escapeHtml(source.note || "")}</div>
       <details><summary>查看原文组成（${item.source_ingredients.length} 味）</summary>
       <ul class="variant-list">${item.source_ingredients.map((row) =>
         `<li>${escapeHtml(row.name)} ${escapeHtml(row.dose || "剂量未注")} ${escapeHtml(row.processing || "")}</li>`
       ).join("")}</ul></details>`
    : source.note ? `<div class="warning-box">${escapeHtml(source.note)}</div>` : "";
  $("#formula-detail").innerHTML = `<div class="detail-inner">
    <div class="detail-kicker">伤寒论辑义 · 第 ${escapeHtml(source.line)} 行</div>
    <h2 class="detail-title">${escapeHtml(item.name)}</h2>
    <p class="detail-subtitle">${escapeHtml(item.indication || "条目原文见下方")}</p>
    <div class="tag-row"><span class="tag">${escapeHtml(item.type)}</span><span class="tag">${escapeHtml(item.six_meridian || "未分篇")}</span><span class="tag">${item.ingredients.length} 味</span></div>
    <div class="warning-box">古籍剂量按原文保留，仅供学习核对；含附子、乌头、巴豆等药味时，须由专业医师按炮制与安全规范处理。</div>
    <div class="section-block">
      <div class="section-title">组成 · 原文剂量</div>
      <div class="composition-grid">${item.ingredients.map(ingredientHtml).join("")}</div>
      ${variant}
    </div>
    ${adjuncts}
    <div class="section-block">
      <div class="section-title">煎服法</div>
      <div class="section-copy">${escapeHtml(item.decoction || "原文未提供煎服法")}</div>
    </div>
    <div class="section-block">
      <div class="section-title">相关药物</div>
      ${related || `<div class="section-copy">暂无已建立的本经条目链接。</div>`}
    </div>
    <div class="section-block">
      <div class="section-title">原文定位</div>
      <div class="source-box"><div class="source-locator">${escapeHtml(source.title)} · ${escapeHtml(source.path)} · 第 ${escapeHtml(source.line)} 行</div><p>${escapeHtml(source.excerpt)}</p></div>
    </div>
  </div>`;
}

function renderHerbDetail(item) {
  const sections = Object.entries(item.sections || {}).filter(([, value]) => String(value || "").trim());
  const formulas = item.formulas?.length
    ? item.formulas.map((formula) =>
        `<button class="herb-formula-link" data-formula-id="${encodeURIComponent(formula.id)}">${escapeHtml(formula.name)}</button>`
      ).join("")
    : `<span class="section-copy">暂无关联方剂。</span>`;
  $("#herb-detail").innerHTML = `<div class="detail-inner">
    <div class="detail-kicker">倪海厦注神农本草经 · 第 ${escapeHtml(item.page_start)} 页</div>
    <h2 class="detail-title">${escapeHtml(item.name)}</h2>
    <p class="detail-subtitle">${escapeHtml(item.names?.filter((name) => name !== item.name).join(" · ") || "本经条目")}</p>
    <div class="tag-row"><span class="tag">${escapeHtml(item.source || "本经")}</span><span class="tag">${formulas ? "有方剂关联" : "暂无方剂关联"}</span></div>
    ${sections.map(([label, value]) => `<div class="section-block"><div class="section-title">${escapeHtml(label)}</div><div class="section-copy">${escapeHtml(value)}</div></div>`).join("")}
    <div class="section-block herb-list-section"><div class="section-title">相关方剂</div><div class="herb-formulas">${formulas}</div></div>
  </div>`;
}

async function loadFormulas(reset = false) {
  if (reset) {
    state.formulaPage = 1;
    state.formulaItems = [];
    state.selectedFormula = null;
    $("#formula-detail").innerHTML = `<div class="empty-state"><span class="empty-mark">方</span><h2>正在读取方剂目录</h2><p>本地原文正在建立索引。</p></div>`;
  }
  const params = new URLSearchParams({
    q: state.formulaQuery,
    type: state.formulaType,
    meridian: state.formulaMeridian,
    page: String(state.formulaPage),
    page_size: "30",
  });
  const data = await request(`/api/formulas?${params}`);
  state.formulaTotal = data.total;
  state.formulaItems.push(...data.items);
  renderFormulaList();
  if (!state.selectedFormula && state.formulaItems.length) {
    const hashId = decodeURIComponent(location.hash.replace(/^#\/formulas\//, ""));
    const first = state.formulaItems.find((item) => item.id === hashId) || state.formulaItems[0];
    await selectFormula(first.id);
  }
}

async function loadHerbs(reset = false) {
  if (reset) {
    state.herbPage = 1;
    state.herbItems = [];
    state.selectedHerb = null;
  }
  const params = new URLSearchParams({
    q: state.herbQuery,
    category: state.herbCategory,
    page: String(state.herbPage),
    page_size: "30",
  });
  const data = await request(`/api/herbs?${params}`);
  state.herbTotal = data.total;
  state.herbItems.push(...data.items);
  renderHerbList();
  if (!state.selectedHerb && state.herbItems.length) {
    const hashId = decodeURIComponent(location.hash.replace(/^#\/herbs\//, ""));
    const first = state.herbItems.find((item) => item.id === hashId) || state.herbItems[0];
    await selectHerb(first.id);
  }
}

async function selectFormula(id) {
  state.selectedFormula = await request(`/api/formulas/${encodeURIComponent(id)}`);
  state.view = "formulas";
  location.hash = `#/formulas/${encodeURIComponent(id)}`;
  renderFormulaList();
  renderFormulaDetail(state.selectedFormula);
}

async function selectHerb(id) {
  state.selectedHerb = await request(`/api/herbs/${encodeURIComponent(id)}`);
  state.view = "herbs";
  setView("herbs");
  location.hash = `#/herbs/${encodeURIComponent(id)}`;
  renderHerbList();
  renderHerbDetail(state.selectedHerb);
}

function openHerb(id) {
  setView("herbs");
  selectHerb(id).catch(() => showNotice("该药味暂无本经条目"));
}

function openFormula(id) {
  setView("formulas");
  selectFormula(id).catch(() => showNotice("该方剂暂时无法读取"));
}

function debounce(fn, wait = 180) {
  let timer;
  return (...args) => {
    window.clearTimeout(timer);
    timer = window.setTimeout(() => fn(...args), wait);
  };
}

document.querySelectorAll(".module-tab").forEach((button) => {
  button.addEventListener("click", () => setView(button.dataset.view));
});

$("#formula-query").addEventListener("input", debounce((event) => {
  state.formulaQuery = event.target.value.trim();
  loadFormulas(true).catch(() => showNotice("方剂目录读取失败"));
}));
$("#formula-type").addEventListener("change", (event) => {
  state.formulaType = event.target.value;
  loadFormulas(true).catch(() => showNotice("方剂目录读取失败"));
});
$("#formula-meridian").addEventListener("change", (event) => {
  state.formulaMeridian = event.target.value;
  loadFormulas(true).catch(() => showNotice("方剂目录读取失败"));
});
$("#formula-clear").addEventListener("click", () => {
  state.formulaQuery = "";
  state.formulaType = "";
  state.formulaMeridian = "";
  $("#formula-query").value = "";
  $("#formula-type").value = "";
  $("#formula-meridian").value = "";
  loadFormulas(true).catch(() => showNotice("方剂目录读取失败"));
});
$("#formula-more").addEventListener("click", () => {
  state.formulaPage += 1;
  loadFormulas().catch(() => showNotice("方剂目录读取失败"));
});
$("#herb-query").addEventListener("input", debounce((event) => {
  state.herbQuery = event.target.value.trim();
  loadHerbs(true).catch(() => showNotice("药物目录读取失败"));
}));
$("#herb-category").addEventListener("change", (event) => {
  state.herbCategory = event.target.value;
  loadHerbs(true).catch(() => showNotice("药物目录读取失败"));
});
$("#herb-clear").addEventListener("click", () => {
  state.herbQuery = "";
  state.herbCategory = "";
  $("#herb-query").value = "";
  $("#herb-category").value = "";
  loadHerbs(true).catch(() => showNotice("药物目录读取失败"));
});
$("#herb-more").addEventListener("click", () => {
  state.herbPage += 1;
  loadHerbs().catch(() => showNotice("药物目录读取失败"));
});
$("#formula-list").addEventListener("click", (event) => {
  const item = event.target.closest("[data-kind='formula']");
  if (item) selectFormula(decodeURIComponent(item.dataset.id)).catch(() => showNotice("方剂读取失败"));
});
$("#herb-list").addEventListener("click", (event) => {
  const item = event.target.closest("[data-kind='herb']");
  if (item) selectHerb(decodeURIComponent(item.dataset.id)).catch(() => showNotice("药物读取失败"));
});
document.addEventListener("click", (event) => {
  const herbLink = event.target.closest("[data-herb-id]");
  if (herbLink) {
    event.preventDefault();
    openHerb(decodeURIComponent(herbLink.dataset.herbId));
  }
  const formulaLink = event.target.closest("[data-formula-id]");
  if (formulaLink) {
    event.preventDefault();
    openFormula(decodeURIComponent(formulaLink.dataset.formulaId));
  }
});
window.addEventListener("hashchange", () => {
  const match = location.hash.match(/^#\/(formulas|herbs)\/(.+)$/);
  if (!match) return;
  const [, kind, id] = match;
  if (kind === "formulas") selectFormula(decodeURIComponent(id)).catch(() => {});
  if (kind === "herbs") selectHerb(decodeURIComponent(id)).catch(() => {});
});

async function boot() {
  try {
    const overview = await request("/api/overview");
    $("#dataset-note").textContent = `${overview.formulas} 首方 · ${overview.herbs} 味药 · 本地原文`;
    const hash = location.hash.match(/^#\/(formulas|herbs)\//);
    if (hash?.[1] === "herbs") setView("herbs");
    await loadFormulas(true);
    if (state.view === "herbs") await loadHerbs(true);
  } catch (error) {
    showNotice("本地目录未启动或数据缺失");
  }
}

boot();
