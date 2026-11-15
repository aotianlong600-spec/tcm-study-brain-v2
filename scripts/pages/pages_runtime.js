(function () {
  window.__TCM_STATIC_WEB__ = true;
  window.__TCM_BUILD_VERSION__ = "__BUILD_ID__";

  const PLACEHOLDER_SVG =
    "data:image/svg+xml;utf8," +
    encodeURIComponent(
      `<svg xmlns="http://www.w3.org/2000/svg" width="640" height="120">` +
        `<rect width="100%" height="100%" rx="8" fill="#fbf7ee" stroke="#dfd3bd"/>` +
        `<text x="50%" y="54%" text-anchor="middle" font-family="sans-serif" font-size="14" fill="#5d4e3c">网页构建版：正在按需渲染原书 PDF 扫描页…</text>` +
        `</svg>`
    );

  const FAILED_SVG =
    "data:image/svg+xml;utf8," +
    encodeURIComponent(
      `<svg xmlns="http://www.w3.org/2000/svg" width="640" height="120">` +
        `<rect width="100%" height="100%" rx="8" fill="#fff8f6" stroke="#e4c7be"/>` +
        `<text x="50%" y="54%" text-anchor="middle" font-family="sans-serif" font-size="14" fill="#7a3e34">原书 PDF 扫描页暂未能在线渲染，下方已提供完整逐字校对原文</text>` +
        `</svg>`
    );

  function escapeAttr(val) {
    return String(val ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  window.tcmImgAttrs = function (apiUrl) {
    return `data-tcm-api-img="${escapeAttr(apiUrl)}" src="${PLACEHOLDER_SVG}"`;
  };

  const nativeFetch = window.fetch.bind(window);
  let reqSeq = 0;
  const pending = new Map();
  let workerReady = false;
  let workerFailed = null;
  let readyResolve;
  const readyPromise = new Promise((r) => {
    readyResolve = r;
  });

  const worker = new Worker("./pages_worker.js?v=__BUILD_ID__", { type: "module" });
  worker.addEventListener("message", (event) => {
    const msg = event.data || {};
    if (msg.type === "status") {
      const note = document.getElementById("dataset-note");
      if (note && !workerReady) note.textContent = `构建版 · ${msg.text}`;
      return;
    }
    if (msg.type === "ready") {
      workerReady = true;
      readyResolve();
      return;
    }
    if (msg.type === "init_error") {
      workerFailed = msg.error || "引擎初始化失败";
      const note = document.getElementById("dataset-note");
      if (note) note.textContent = `离线引擎初始化失败：${workerFailed}`;
      for (const [, p] of pending) {
        p.reject(new Error(workerFailed));
      }
      pending.clear();
      return;
    }
    if (msg.type === "response") {
      const item = pending.get(msg.id);
      if (!item) return;
      pending.delete(msg.id);
      try {
        const parsed = JSON.parse(msg.raw);
        item.resolve(
          new Response(JSON.stringify(parsed.body), {
            status: parsed.status || 200,
            headers: { "Content-Type": "application/json; charset=utf-8" },
          })
        );
      } catch (err) {
        item.reject(err);
      }
    }
  });

  worker.addEventListener("error", (err) => {
    workerFailed = err?.message || "Web Worker 加载失败";
    for (const [, p] of pending) p.reject(new Error(workerFailed));
    pending.clear();
  });

  window.fetch = async function (input, init) {
    const rawUrl = typeof input === "string" ? input : input?.url || "";
    try {
      const u = new URL(rawUrl, location.href);
      const apiIdx = u.pathname.indexOf("/api/");
      if (u.origin === location.origin && apiIdx >= 0) {
        const apiUrl = u.pathname.slice(apiIdx) + u.search;
        if (workerFailed) throw new Error(workerFailed);
        if (!workerReady) await readyPromise;
        const id = ++reqSeq;
        return await new Promise((resolve, reject) => {
          pending.set(id, { resolve, reject });
          worker.postMessage({ type: "api", id, url: apiUrl });
        });
      }
    } catch (err) {
      if (workerFailed) throw err;
    }
    return nativeFetch(input, init);
  };

  // On-demand PDF.js page image renderer for <img data-tcm-api-img="...">
  let pdfjsPromise = null;
  const pdfDocCache = new Map();
  const pageDataUrlCache = new Map();

  async function getPdfJs() {
    if (!pdfjsPromise) {
      pdfjsPromise = import("./runtime/pdfjs/pdf.min.mjs").then((lib) => {
        lib.GlobalWorkerOptions.workerSrc = new URL("./runtime/pdfjs/pdf.worker.min.mjs", location.href).href;
        return lib;
      });
    }
    return pdfjsPromise;
  }

  async function renderApiImageToImg(img) {
    const apiUrl = img.dataset.tcmApiImg;
    if (!apiUrl || img.dataset.tcmRendering === "1" || img.dataset.tcmRendered === apiUrl) return;
    img.dataset.tcmRendering = "1";
    try {
      if (pageDataUrlCache.has(apiUrl)) {
        img.src = pageDataUrlCache.get(apiUrl);
        img.dataset.tcmRendered = apiUrl;
        return;
      }
      const metaRes = await window.fetch(`/api/__pdf-source?url=${encodeURIComponent(apiUrl)}`);
      if (!metaRes.ok) throw new Error("未找到原书 PDF");
      const meta = await metaRes.json();
      const relUrl = "./" + meta.relative_path.split("/").map(encodeURIComponent).join("/");
      const pdfjs = await getPdfJs();
      let docPromise = pdfDocCache.get(relUrl);
      if (!docPromise) {
        docPromise = pdfjs.getDocument({ url: relUrl }).promise;
        pdfDocCache.set(relUrl, docPromise);
      }
      const doc = await docPromise;
      const page = await doc.getPage(Number(meta.pdf_page) || 1);
      const viewport = page.getViewport({ scale: 1.55 });
      const canvas = document.createElement("canvas");
      canvas.width = Math.floor(viewport.width);
      canvas.height = Math.floor(viewport.height);
      const ctx = canvas.getContext("2d", { alpha: false });
      await page.render({ canvasContext: ctx, viewport }).promise;
      const dataUrl = canvas.toDataURL("image/png");
      if (pageDataUrlCache.size >= 24) {
        const firstKey = pageDataUrlCache.keys().next().value;
        pageDataUrlCache.delete(firstKey);
      }
      pageDataUrlCache.set(apiUrl, dataUrl);
      img.src = dataUrl;
      img.dataset.tcmRendered = apiUrl;
    } catch (_err) {
      img.src = FAILED_SVG;
      img.dataset.tcmRendered = apiUrl;
    } finally {
      delete img.dataset.tcmRendering;
    }
  }

  function scanPendingImages(root = document.body) {
    if (!root) return;
    root.querySelectorAll?.("img[data-tcm-api-img]")?.forEach((img) => {
      renderApiImageToImg(img);
    });
  }

  document.addEventListener("DOMContentLoaded", () => {
    scanPendingImages();
    const obs = new MutationObserver((mutations) => {
      for (const m of mutations) {
        if (m.type === "attributes" && m.target?.matches?.("img[data-tcm-api-img]")) {
          renderApiImageToImg(m.target);
          continue;
        }
        for (const node of m.addedNodes) {
          if (node.nodeType !== 1) continue;
          if (node.matches?.("img[data-tcm-api-img]")) renderApiImageToImg(node);
          else scanPendingImages(node);
        }
      }
    });
    if (document.body) {
      obs.observe(document.body, {
        childList: true,
        subtree: true,
        attributes: true,
        attributeFilter: ["data-tcm-api-img"],
      });
    }

    function showSwUpdateToast() {
      if (document.getElementById("tcm-sw-update-toast")) return;
      const bar = document.createElement("div");
      bar.id = "tcm-sw-update-toast";
      bar.className = "tcm-sw-toast";
      bar.innerHTML =
        `<span>发现新版经方知识库与辨证引擎</span>` +
        `<button type="button" class="primary-btn small-btn" id="tcm-sw-reload-btn">点击刷新生效</button>`;
      document.body?.appendChild(bar);
      document.getElementById("tcm-sw-reload-btn")?.addEventListener("click", () => window.location.reload());
    }

    if ("serviceWorker" in navigator && (location.protocol === "https:" || location.hostname === "127.0.0.1" || location.hostname === "localhost")) {
      navigator.serviceWorker
        .register("./sw.js", { updateViaCache: "none" })
        .then((reg) => {
          if (reg.waiting && navigator.serviceWorker.controller) {
            showSwUpdateToast();
          }
          reg.addEventListener("updatefound", () => {
            const nextWorker = reg.installing;
            if (!nextWorker) return;
            nextWorker.addEventListener("statechange", () => {
              if (nextWorker.state === "installed" && navigator.serviceWorker.controller) {
                showSwUpdateToast();
              }
            });
          });
        })
        .catch(() => {});
    }
  });
})();
