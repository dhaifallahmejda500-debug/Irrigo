const el = (id) => document.getElementById(id);

function setOnlineStatus() {
el("status").textContent = navigator.onLine ? "Status: ONLINE ✅" : "Status: OFFLINE ❌";
}

async function loadData() {
try {
const r = await fetch("/data", { cache: "no-store" });
if (!r.ok) throw new Error("HTTP " + r.status);
const d = await r.json();

el("t").textContent = d.temperature ?? "No data";
el("h").textContent = d.humidity ?? "No data";
el("s").textContent = d.soil ?? "No data";
el("k").textContent = d.tank ?? "No data";
el("v").textContent = d.valve ? "ON" : "OFF";
} catch (e) {
console.log("fetch error", e);
}
}

window.addEventListener("online", setOnlineStatus);
window.addEventListener("offline", setOnlineStatus);

document.addEventListener("DOMContentLoaded", () => {
setOnlineStatus();
loadData();
setInterval(loadData, 3000);

const btn = document.getElementById("refresh");
if (btn) btn.addEventListener("click", loadData);

if ("serviceWorker" in navigator) {
navigator.serviceWorker.register("/static/service-worker.js");
}
});