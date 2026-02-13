 const CACHE = "irrigo-v1";
const ASSETS = [
"/",
"/static/index.html",
"/static/app.js",
"/static/manifest.json"
];

self.addEventListener("install", (e) => {
e.waitUntil(caches.open(CACHE).then((c) => c.addAll(ASSETS)));
});

self.addEventListener("fetch", (e) => {
const url = new URL(e.request.url);

// /data = toujours réseau (sinon tu gardes de vieilles valeurs)
if (url.pathname === "/data") {
e.respondWith(fetch(e.request).catch(() => new Response(JSON.stringify({
temperature: null, humidity: null, soil: null, tank: null, valve: false
}), { headers: { "Content-Type": "application/json" } })));
return;
}

e.respondWith(
caches.match(e.request).then((r) => r || fetch(e.request))
);
});