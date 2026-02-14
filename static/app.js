 
const $ = (id) => document.getElementById(id);

const API = {
data: "/data",
status: "/status",
setValve: "/set/valve",
setMotor: "/set/motor",
timers: "/timers",
smart: "/smart",
};

let current = {
temperature: null,
humidity: null,
soil: null,
tank: null,
valve: false,
motor: false,
};

function setText(id, val) {
$(id).innerText = (val === null || val === undefined) ? "--" : String(val);
}

function setSwitch(sw, on) {
if (on) sw.classList.add("on");
else sw.classList.remove("on");
}

async function apiGet(url) {
const r = await fetch(url);
if (!r.ok) throw new Error("GET failed");
return await r.json();
}
async function apiPost(url, body) {
const r = await fetch(url, {
method: "POST",
headers: { "Content-Type":"application/json" },
body: JSON.stringify(body),
});
if (!r.ok) throw new Error("POST failed");
return await r.json();
}
async function apiDelete(url) {
const r = await fetch(url, { method: "DELETE" });
if (!r.ok) throw new Error("DELETE failed");
return await r.json();
}

async function loadStatus() {
try {
const s = await apiGet(API.status);
const badge = $("statusBadge");
const txt = $("statusText");
if (s.online) {
badge.classList.add("online");
txt.innerText = "Online";
} else {
badge.classList.remove("online");
txt.innerText = "Offline";
}
} catch {
$("statusBadge").classList.remove("online");
$("statusText").innerText = "Offline";
}
}

async function loadData() {
try {
const d = await apiGet(API.data);
current = d;

setText("tempVal", d.temperature);
setText("humVal", d.humidity);
setText("soilVal", d.soil);
setText("tankVal", d.tank);

$("valveText").innerText = d.valve ? "ON" : "OFF";

// manual switches page
setSwitch($("swValve"), !!d.valve);
setSwitch($("swMotor"), !!d.motor);

} catch (e) {
// if backend unreachable, keep UI
}
}

async function toggleValve() {
const newVal = !current.valve;
await apiPost(API.setValve, { value: newVal });
await loadData();
}

async function toggleMotor() {
const newVal = !current.motor;
await apiPost(API.setMotor, { value: newVal });
await loadData();
}

// ---------------- Timers UI ----------------
function formatDT(ts) {
const d = new Date(ts * 1000);
return d.toISOString().slice(0,16).replace("T"," ");
}

async function refreshTimers() {
const box = $("timerList");
box.innerHTML = "";
try {
const res = await apiGet(API.timers);
for (const t of res.timers) {
const div = document.createElement("div");
div.className = "timerItem";
const deviceLabel = (t.device === "valve") ? "Valve 1" : "Tank motor";
div.innerHTML = `
<div class="meta">
${deviceLabel}<br/>
From: ${formatDT(t.start)}<br/>
To: ${formatDT(t.end)}
</div>
<button class="xbtn" title="Delete">×</button>
`;
div.querySelector(".xbtn").onclick = async () => {
await apiDelete(`${API.timers}/${t.id}`);
await refreshTimers();
};
box.appendChild(div);
}
} catch {}
}

function dtLocalToUnix(dtLocal) {
// dtLocal: "YYYY-MM-DDTHH:MM"
const d = new Date(dtLocal);
return Math.floor(d.getTime() / 1000);
}

async function addTimer() {
const device = $("timerDevice").value;
const from = $("timerFrom").value;
const to = $("timerTo").value;

if (!from || !to) {
alert("Choisis From et To");
return;
}
const start = dtLocalToUnix(from);
const end = dtLocalToUnix(to);
if (end <= start) {
alert("To doit être après From");
return;
}

await apiPost(API.timers, { device, start, end });
$("timerFrom").value = "";
$("timerTo").value = "";
await refreshTimers();
}

// ---------------- Smart UI ----------------
async function loadSmart() {
try {
const s = await apiGet(API.smart);
setSwitch($("swSmart"), !!s.enabled);
$("soilThreshold").value = s.soil_threshold;
$("minOn").value = s.min_on_seconds;
} catch {}
}

async function saveSmart() {
const enabled = $("swSmart").classList.contains("on");
const soil_threshold = parseInt($("soilThreshold").value || "30", 10);
const min_on_seconds = parseInt($("minOn").value || "20", 10);

await apiPost(API.smart, { enabled, soil_threshold, min_on_seconds });
alert("Smart saved ✅");
}

// ---------------- Tabs / Navigation ----------------
function showPage(page) {
$("pageHome").classList.add("hidden");
$("pageIrrigate").classList.add("hidden");
$("pageSettings").classList.add("hidden");

$("navHome").classList.remove("active");
$("navIrrigate").classList.remove("active");
$("navSettings").classList.remove("active");

if (page === "home") { $("pageHome").classList.remove("hidden"); $("navHome").classList.add("active"); }
if (page === "irrigate") { $("pageIrrigate").classList.remove("hidden"); $("navIrrigate").classList.add("active"); }
if (page === "settings") { $("pageSettings").classList.remove("hidden"); $("navSettings").classList.add("active"); }
}

function setTab(tab) {
$("tabManual").classList.remove("active");
$("tabAuto").classList.remove("active");
$("tabSmart").classList.remove("active");

$("manualBox").classList.add("hidden");
$("autoBox").classList.add("hidden");
$("smartBox").classList.add("hidden");

if (tab === "manual") {
$("tabManual").classList.add("active");
$("manualBox").classList.remove("hidden");
}
if (tab === "auto") {
$("tabAuto").classList.add("active");
$("autoBox").classList.remove("hidden");
refreshTimers();
}
if (tab === "smart") {
$("tabSmart").classList.add("active");
$("smartBox").classList.remove("hidden");
loadSmart();
}
}

// ---------------- PWA Service Worker ----------------
if ("serviceWorker" in navigator) {
navigator.serviceWorker.register("/static/service-worker.js")
.then(() => console.log("SW OK"))
.catch(e => console.log("SW ERR", e));
}

// ---------------- Events ----------------
$("btnValve").onclick = toggleValve;
$("btnMotor").onclick = toggleMotor;

$("swValve").onclick = toggleValve;
$("swMotor").onclick = toggleMotor;

$("addTimerBtn").onclick = addTimer;

$("swSmart").onclick = () => {
$("swSmart").classList.toggle("on");
};
$("saveSmartBtn").onclick = saveSmart;

$("navHome").onclick = () => showPage("home");
$("navIrrigate").onclick = () => showPage("irrigate");
$("navSettings").onclick = () => showPage("settings");

$("tabManual").onclick = () => setTab("manual");
$("tabAuto").onclick = () => setTab("auto");
$("tabSmart").onclick = () => setTab("smart");

// ---------------- Start loop ----------------
showPage("home");
setTab("manual");

loadStatus();
loadData();

setInterval(loadStatus, 2000);
setInterval(loadData, 2000);