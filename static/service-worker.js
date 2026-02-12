 const CACHE_NAME = "irrigo-cache-v1";

const FILES_TO_CACHE = [
"/",
"/static/index.html",
"/static/manifest.json",
"/static/service-worker.js",
"/static/icon-192.png",
"/static/icon-512.png"
];

self.addEventListener("install", (event) => {
event.waitUntil(
caches.open(CACHE_NAME).then((cache) => cache.addAll(FILES_TO_CACHE))
);
self.skipWaiting();
});

self.addEventListener("activate", (event) => {
event.waitUntil(
caches.keys().then((keys) =>
Promise.all(keys.map((k) => (k !== CACHE_NAME ? caches.delete(k) : null)))
)
);
self.clients.claim();
});

self.addEventListener("fetch", (event) => {
event.respondWith(
caches.match(event.request).then((resp) => resp || fetch(event.request))
);
});