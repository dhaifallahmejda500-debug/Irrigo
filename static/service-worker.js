 
const CACHE = "irrigo-v1";
const ASSETS = [
"/",
"/static/style.css",
"/static/app.js",
"/static/manifest.json",
"/static/icon-192.png",
"/static/icon-512.png"
];

self.addEventListener("install", (e) => {
e.waitUntil(caches.open(CACHE).then(c => c.addAll(ASSETS)));
});

self.addEventListener("fetch", (e) => {
e.respondWith(
caches.match(e.request).then(cached => cached || fetch(e.request))
);
});