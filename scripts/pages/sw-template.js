const CONFIG = __PWA_CONFIG__;
const SHELL_CACHE = `tcm-brain-shell-${CONFIG.version}`;
const PRECACHE_SET = new Set(CONFIG.precache);

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(SHELL_CACHE).then((cache) => cache.addAll(CONFIG.precache)).then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) =>
        Promise.all(
          keys
            .filter((k) => k.startsWith("tcm-brain-shell-") && k !== SHELL_CACHE)
            .map((k) => caches.delete(k))
        )
      )
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (event) => {
  const req = event.request;
  if (req.method !== "GET") return;
  const url = new URL(req.url);
  if (url.origin !== self.location.origin) return;
  if (url.pathname.includes("/api/")) return;

  // Network-first for HTML navigations so new builds take effect cleanly on reload
  if (req.mode === "navigate" || url.pathname.endsWith("/") || url.pathname.endsWith("/index.html")) {
    event.respondWith(
      fetch(req)
        .then((resp) => {
          if (resp && resp.ok) {
            const clone = resp.clone();
            caches.open(SHELL_CACHE).then((c) => c.put(req, clone)).catch(() => {});
          }
          return resp;
        })
        .catch(() => caches.match(req).then((cached) => cached || caches.match("index.html")))
    );
    return;
  }

  // Cache-first for immutable versioned runtime / pre-cached static shell files
  event.respondWith(
    caches.match(req).then((cached) => {
      if (cached) return cached;
      return fetch(req).then((resp) => {
        if (resp && resp.ok && !url.pathname.endsWith(".pdf") && !url.pathname.endsWith("bundle.zip")) {
          const clone = resp.clone();
          caches.open(SHELL_CACHE).then((c) => c.put(req, clone)).catch(() => {});
        }
        return resp;
      });
    })
  );
});
