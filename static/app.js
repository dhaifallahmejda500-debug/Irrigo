 async function loadData() {
const r = await fetch("/data");
const d = await r.json();

document.getElementById("temp").innerText = d.temperature;
document.getElementById("hum").innerText = d.humidity;
document.getElementById("soil").innerText = d.soil;
}

async function toggleValve() {
await fetch("/cmd", {
method: "POST",
headers: {"Content-Type": "application/json"},
body: JSON.stringify({ valve: true })
});
}

setInterval(loadData, 2000);
loadData();