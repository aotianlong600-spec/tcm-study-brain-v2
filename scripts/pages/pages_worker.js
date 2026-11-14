import { loadPyodide } from "./runtime/pyodide/pyodide.mjs";

const RUNTIME_CACHE = "tcm-study-brain-runtime-v1";
const BUILD_TAG = "__BUILD_ID__";

let dispatchJson = null;

async function fetchCachedArrayBuffer(url) {
  if (typeof caches !== "undefined") {
    try {
      const cache = await caches.open(RUNTIME_CACHE);
      const cacheKey = `${url}?v=${BUILD_TAG}`;
      const hit = await cache.match(cacheKey);
      if (hit) {
        return await hit.arrayBuffer();
      }
      const resp = await fetch(url);
      if (!resp.ok) throw new Error(`HTTP ${resp.status} for ${url}`);
      const clone = resp.clone();
      await cache.put(cacheKey, clone).catch(() => {});
      return await resp.arrayBuffer();
    } catch (_err) {
      // Fallback straight to direct fetch
    }
  }
  const resp = await fetch(url);
  if (!resp.ok) throw new Error(`HTTP ${resp.status} for ${url}`);
  return await resp.arrayBuffer();
}

async function initEngine() {
  self.postMessage({ type: "status", text: "正在启动浏览器 Python 运行时（Pyodide）…" });
  const pyodide = await loadPyodide({
    indexURL: "./runtime/pyodide/",
  });
  self.postMessage({ type: "status", text: "正在载入全库经典与 17 册藏书索引包…" });
  const bundleBuf = await fetchCachedArrayBuffer("./runtime/bundle.zip");
  pyodide.unpackArchive(bundleBuf, "zip", { extractDir: "/tcm_brain" });
  pyodide.runPython(`
import sys
if "/tcm_brain" not in sys.path:
    sys.path.insert(0, "/tcm_brain")
from app.static_dispatch import dispatch_json as _tcm_dispatch_json
`);
  dispatchJson = pyodide.globals.get("_tcm_dispatch_json");
  self.postMessage({ type: "ready" });
}

const initPromise = initEngine().catch((err) => {
  self.postMessage({ type: "init_error", error: String(err?.message || err) });
  throw err;
});

self.addEventListener("message", async (event) => {
  const msg = event.data || {};
  if (msg.type !== "api") return;
  try {
    await initPromise;
    const raw = dispatchJson(String(msg.url || "/api/health"));
    self.postMessage({ type: "response", id: msg.id, raw: String(raw) });
  } catch (err) {
    self.postMessage({
      type: "response",
      id: msg.id,
      raw: JSON.stringify({ status: 500, body: { detail: String(err?.message || err) } }),
    });
  }
});
