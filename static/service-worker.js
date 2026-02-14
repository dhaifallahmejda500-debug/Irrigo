 const CACHE = "irrigo-cache-v1";
const ASSETS = [
"/",
"/static/index.html",
"/static/app.js",
"/static/manifest.json",
];

self.addEventListener("install", (event) => {
event.waitUntil(
caches.open(CACHE).then((c) => c.addAll(ASSETS))
);
});

self.addEventListener("activate", (event) => {
event.waitUntil(
caches.keys().then(keys =>
Promise.all(keys.map(k => (k !== CACHE ? caches.delete(k) : null)))
)
);
});

self.addEventListener("fetch", (event) => {
const url = new URL(event.request.url);

// API: network-first
if (url.pathname.startsWith("/data") || url.pathname.startsWith("/status") || url.pathname.startsWith("/timers") || url.pathname.startsWith("/smart") || url.pathname.startsWith("/set/")) {
event.respondWith(
fetch(event.request).catch(() => new Response(JSON.stringify({offline:true}), {headers:{"Content-Type":"application/json"}}))
);
return;
}

// Static: cache-first
event.respondWith(
caches.match(event.request).then(res => res || fetch(event.request))
);
});
