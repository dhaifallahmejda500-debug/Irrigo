 async function loadData() {
try {
const res = await fetch("/data");
const data = await res.json();

document.getElementById("temperature").innerText =
data.temperature ?? "--";

document.getElementById("humidity").innerText =
data.humidity ?? "--";

document.getElementById("soil").innerText =
data.soil ?? "--";

document.getElementById("tank").innerText =
data.tank ?? "--";

document.getElementById("status").innerText = "Online";
} catch (e) {
document.getElementById("status").innerText = "Offline";
}
}

loadData();
setInterval(loadData, 2000);
