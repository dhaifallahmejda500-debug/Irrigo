 const CACHE_NAME = "irrigio-cache-v1";

const ASSETS = [
"/",
"/static/index.html",
"/static/manifest.json",
"/static/service-worker.js",
"/static/icon-192.png",
"/static/icon-512.png"
];

// Install
self.addEventListener("install", (event) => {
event.waitUntil(
caches.open(CACHE_NAME).then((cache) => cache.addAll(ASSETS))
);
});

// Activate
self.addEventListener("activate", (event) => {
event.waitUntil(
caches.keys().then((keys) =>
Promise.all(keys.map((k) => (k !== CACHE_NAME ? caches.delete(k) : null)))
)
);
});

// Fetch
self.addEventListener("fetch", (event) => {
const url = new URL(event.request.url);

// Ne pas mettre /data en cache (car dynamique)
if (url.pathname === "/data") {
event.respondWith(
fetch(event.request).catch(() =>
new Response(JSON.stringify({
temperature: null,
humidity: null,
soil: null,
tank: null,
valve: false,
online: false,
seconds_since_update: null
}), { headers: { "Content-Type": "application/json" } })
)
);
return;
}

// Cache first pour le reste
event.respondWith(
caches.match(event.request).then((cached) => cached || fetch(event.request))
);
});