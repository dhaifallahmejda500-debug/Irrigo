 
 // -------------------------
// Helpers
// -------------------------
const $ = (id) => document.getElementById(id);

function setActivePage(name) {
const pages = ["Home", "Irrigate", "Settings"];
pages.forEach(p => {
const el = document.getElementById("page" + p);
el.classList.toggle("active", p === name);
});

document.querySelectorAll(".navBtn").forEach(btn => {
btn.classList.toggle("active", btn.dataset.page === name);
});
}

function setGauge(el, percent) {
const p = Math.max(0, Math.min(100, Number(percent || 0)));
const deg = p * 3.6;
el.style.background = `conic-gradient(var(--ok) ${deg}deg, #dbeff0 ${deg}deg)`;
}

function toLocalInputValue(date) {
// yyyy-MM-ddTHH:mm
const pad = (n) => String(n).padStart(2, "0");
return `${date.getFullYear()}-${pad(date.getMonth()+1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

function toDisplayValue(dtLocalStr) {
// dtLocalStr = "2026-02-08T21:36"
return dtLocalStr.replace("T", " ");
}

// -------------------------
// API
// -------------------------
async function apiGet(path) {
const r = await fetch(path);
if (!r.ok) throw new Error(await r.text());
return await r.json();
}

async function apiPost(path, body) {
const r = await fetch(path, {
method: "POST",
headers: {"Content-Type":"application/json"},
body: JSON.stringify(body)
});
if (!r.ok) throw new Error(await r.text());
return await r.json();
}

async function apiDel(path) {
const r = await fetch(path, {method:"DELETE"});
if (!r.ok) throw new Error(await r.text());
return await r.json();
}

// -------------------------
// State + Refresh
// -------------------------
async function refreshAll() {
const data = await apiGet("/api/dashboard");

// MQTT dot
const dot = $("mqttDot");
dot.style.background = data.mqtt_connected ? "#20c997" : "#ff3b30";

// sensors
const s = data.sensors || {};
$("tempVal").textContent = (s.temperature ?? "--");
$("humVal").textContent = (s.humidity ?? "--");

$("soilVal").textContent = ((s.soil ?? "--") + "%");
$("tankVal").textContent = ((s.tank ?? "--") + "%");

setGauge($("soilRing"), s.soil ?? 0);
setGauge($("tankRing"), s.tank ?? 0);

// actuators
const a = data.actuators || {};
const motorOn = !!a.motor;
const valveOn = !!a.valve;

$("motorText").textContent = motorOn ? "ON" : "OFF";
$("motorText").className = motorOn ? "on" : "off";

$("valveStatus").textContent = valveOn ? "ON" : "OFF";
$("valveStatus").style.color = valveOn ? "#20c997" : "#ff3b30";

$("valveSwitch").checked = valveOn;
$("valveSwitch2").checked = valveOn;
$("motorSwitch").checked = motorOn;

// settings
$("backendUrl").textContent = window.location.origin;
$("cfgHost").textContent = data.config?.MQTT_HOST ?? "--";
$("cfgPort").textContent = data.config?.MQTT_PORT ?? "--";
$("cfgData").textContent = data.config?.TOPIC_DATA ?? "--";
$("cfgCmd").textContent = data.config?.TOPIC_CMD ?? "--";
}

async function refreshTimers() {
const t = await apiGet("/api/timers");
const list = $("timerList");
list.innerHTML = "";

(t.items || []).forEach(item => {
const div = document.createElement("div");
div.className = "timerItem";
div.innerHTML = `
<div class="timerText">🧰 ${item.valve}<br>From: ${item.from}<br>To: ${item.to}</div>
<button class="timerX" title="Delete">✕</button>
`;
div.querySelector(".timerX").addEventListener("click", async () => {
await apiDel(`/api/timers/${item.id}`);
await refreshTimers();
});
list.appendChild(div);
});
}

// -------------------------
// Events
// -------------------------
document.querySelectorAll(".navBtn").forEach(btn => {
btn.addEventListener("click", () => setActivePage(btn.dataset.page));
});

document.querySelectorAll(".tab").forEach(tab => {
tab.addEventListener("click", () => {
document.querySelectorAll(".tab").forEach(t => t.classList.remove("active"));
tab.classList.add("active");

const mode = tab.dataset.mode;
["Manual","Automatic","Smart"].forEach(m => {
document.getElementById("mode"+m).classList.remove("active");
});

if (mode === "manual") document.getElementById("modeManual").classList.add("active");
if (mode === "automatic") document.getElementById("modeAutomatic").classList.add("active");
if (mode === "smart") document.getElementById("modeSmart").classList.add("active");
});
});

// switches
$("valveSwitch").addEventListener("change", async (e) => {
await apiPost("/api/actuators/valve", {on: e.target.checked});
await refreshAll();
});
$("valveSwitch2").addEventListener("change", async (e) => {
await apiPost("/api/actuators/valve", {on: e.target.checked});
await refreshAll();
});
$("motorSwitch").addEventListener("change", async (e) => {
await apiPost("/api/actuators/motor", {on: e.target.checked});
await refreshAll();
});

// buttons
$("btnRefreshHome").addEventListener("click", async () => {
await refreshAll();
});
$("btnRefreshManual").addEventListener("click", async () => {
await refreshAll();
});
$("btnRefreshSettings").addEventListener("click", async () => {
await refreshAll();
});

$("btnAddTimer").addEventListener("click", async () => {
const valve = $("timerValve").value;
const fromV = $("timerFrom").value;
const toV = $("timerTo").value;

if (!fromV || !toV) {
alert("Choisis From et To");
return;
}
await apiPost("/api/timers", {
valve,
from: toDisplayValue(fromV),
to: toDisplayValue(toV),
});

$("timerFrom").value = "";
$("timerTo").value = "";
await refreshTimers();
});

// init
(async function init() {
// default date suggestions
const now = new Date();
$("timerFrom").value = toLocalInputValue(now);
const plus = new Date(now.getTime() + 60*60*1000);
$("timerTo").value = toLocalInputValue(plus);

await refreshAll();
await refreshTimers();

// auto-refresh (optionnel)
setInterval(async () => {
try { await refreshAll(); } catch(e) {}
}, 5000);

// PWA service worker
if ("serviceWorker" in navigator) {
try { await navigator.serviceWorker.register("/static/service-worker.js"); } catch(e) {}
}
})();