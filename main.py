import os
import json
import time
import threading
from typing import List, Optional, Dict, Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

import paho.mqtt.client as mqtt

# -----------------------------
# ENV
# -----------------------------
MQTT_HOST = os.getenv("MQTT_HOST", "test.mosquitto.org")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
MQTT_USER = os.getenv("MQTT_USER", "").strip()   
MQTT_PASS = os.getenv("MQTT_PASS", "").strip()
MQTT_TOPIC_DATA = os.getenv("MQTT_TOPIC_DATA", "irrigo/data")
MQTT_TOPIC_CMD = os.getenv("MQTT_TOPIC_CMD", "irrigo/cmd")

CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*")

# -----------------------------
# APP
# -----------------------------
app = FastAPI(title="Irrigo API", version="1.0.0")
app=FastAPI()

app.add_middleware(
   CORSMiddleware,
   allow_origins=[CORS_ORIGINS] if CORS_ORIGINS != "*" else ["*"],
   allow_credentials=True,
   allow_methods=["*"],
   allow_headers=["*"],
)

# Serve static (PWA)
app.mount("/static", StaticFiles(directory="static"), name="static")


# -----------------------------
# STATE
# -----------------------------
latest = {
   "temperature": None,
   "humidity": None,
   "soil": None,
   "tank": None,
   "valve": False,
   "motor": False,
}

last_update = 0.0

# Automatic timers (in-memory). Each timer: {id, device, start, end}
timers: List[Dict[str, Any]] = []
timer_id_counter = 1

# Smart settings
smart_enabled = False
smart_soil_threshold = 30 # %
smart_min_on_seconds = 20 # minimum ON duration
smart_last_action = 0.0

state_lock = threading.Lock()

# -----------------------------
# MQTT
# -----------------------------
mqtt_client = mqtt.Client()

def mqtt_publish(payload: dict):
   try:
       mqtt_client.publish(MQTT_TOPIC_CMD, json.dumps(payload), qos=0, retain=False)
   except Exception as e:
       print("MQTT publish error:", e)

def on_connect(client, userdata, flags, rc, properties=None):
    print("MQTT connected:", rc)
    client.subscribe(MQTT_TOPIC_DATA)
    print("Subscribed to:", MQTT_TOPIC_DATA)

def on_message(client, userdata, msg):
   global last_update
   try:
      payload = msg.payload.decode("utf-8", errors="ignore")
      data = json.loads(payload)

      with state_lock:
# accept multiple keys
          latest["temperature"] = data.get("temperature", data.get("temp", latest["temperature"]))
          latest["humidity"] = data.get("humidity", data.get("humidite", latest["humidity"]))
          latest["soil"] = data.get("soil", data.get("sol", latest["soil"]))
          latest["tank"] = data.get("tank", data.get("reservoir", latest["tank"]))
# keep valve/motor from current state unless sent
          if "valve" in data:
              latest["valve"] = bool(data["valve"])
          if "motor" in data:
              latest["motor"] = bool(data["motor"])

          last_update = time.time()

# print("Updated latest:", latest)
   except Exception as e:
      print("MQTT message parse error:", e)

def mqtt_thread():
   try:
         if MQTT_USER and MQTT_PASS:
             mqtt_client.username_pw_set(MQTT_USER, MQTT_PASS)
         mqtt_client.on_connect = on_connect
         mqtt_client.on_message = on_message
         mqtt_client.connect(MQTT_HOST, MQTT_PORT, keepalive=60)
         mqtt_client.loop_forever()
   except Exception as e:
           print("MQTT thread error:", e)

# Start MQTT in background thread (Render ok)
threading.Thread(target=mqtt_thread, daemon=True).start()


# -----------------------------
# TIMERS + SMART LOOP
# -----------------------------
def now_ts():
   return time.time()

def check_timers_and_smart():
   global smart_last_action

while True:
   time.sleep(1)

with state_lock:
# ---- Automatic timers ----
   current = now_ts()
   valve_should = latest["valve"]
   motor_should = latest["motor"]

# timers use UNIX timestamps
for t in timers:
    if t["device"] == "valve":
       if t["start"] <= current <= t["end"]:
          valve_should = True
    if t["device"] == "motor":
       if t["start"] <= current <= t["end"]:
          motor_should = True

# ---- Smart mode ----
if smart_enabled:
   soil = latest.get("soil")
# if soil is known and below threshold -> turn valve ON
   if isinstance(soil, (int, float)) and soil < smart_soil_threshold:
# avoid spamming: only act if last action older than min_on_seconds
       if (current - smart_last_action) > smart_min_on_seconds:
         valve_should = True
         smart_last_action = current

# apply commands if needed
if valve_should != latest["valve"]:
   latest["valve"] = valve_should
   mqtt_publish({"valve": valve_should})

if motor_should != latest["motor"]:
   latest["motor"] = motor_should
   mqtt_publish({"motor": motor_should})

threading.Thread(target=check_timers_and_smart, daemon=True).start()


# -----------------------------
# ROUTES
# -----------------------------
@app.get("/", response_class=HTMLResponse)
def home():
# Serve SPA
   with open("static/index.html", "r", encoding="utf-8") as f:
      return f.read()

@app.get("/data")
def get_data():
   with state_lock:
      return {
         "temperature": latest["temperature"],
         "humidity": latest["humidity"],
         "soil": latest["soil"],
         "tank": latest["tank"],
         "valve": latest["valve"],
         "motor": latest["motor"],
}

@app.get("/status")
def status():
    with state_lock:
       online = (time.time() - last_update) < 10 if last_update else False
       return {"online": online, "last_update": last_update}

@app.post("/set/valve")
def set_valve(body: Dict[str, Any]):
    if "value" not in body:
      raise HTTPException(400, "Missing 'value'")
    value = bool(body["value"])
    with state_lock:
       latest["valve"] = value
    mqtt_publish({"valve": value})
    return {"ok": True, "valve": value}

@app.post("/set/motor")
def set_motor(body: Dict[str, Any]):
    if "value" not in body:
       raise HTTPException(400, "Missing 'value'")
    value = bool(body["value"])
    with state_lock:
       latest["motor"] = value
    mqtt_publish({"motor": value})
    return {"ok": True, "motor": value}

# ---- Timers ----
@app.get("/timers")
def list_timers():
    with state_lock:
        return {"timers": timers}

@app.post("/timers")
def add_timer(body: Dict[str, Any]):
    """
    body: {device:"valve"|"motor", start: unix_ts, end: unix_ts}
    """
    global timer_id_counter
    device = body.get("device")
    start = body.get("start")
    end = body.get("end")

    if device not in ("valve", "motor"):
       raise HTTPException(400, "device must be 'valve' or 'motor'")
    if not isinstance(start, (int, float)) or not isinstance(end, (int, float)):
       raise HTTPException(400, "start/end must be unix timestamps")
    if end <= start:
       raise HTTPException(400, "end must be > start")

    with state_lock:
       t = {"id": timer_id_counter, "device": device, "start": float(start), "end": float(end)}
       timer_id_counter += 1
       timers.append(t)
    return {"ok": True, "timer": t}

@app.delete("/timers/{timer_id}")
def delete_timer(timer_id: int):
    with state_lock:
       idx = next((i for i, t in enumerate(timers) if t["id"] == timer_id), None)
       if idx is None:
          raise HTTPException(404, "timer not found")
       timers.pop(idx)
    return {"ok": True}

# ---- Smart ----
@app.get("/smart")
def get_smart():
   with state_lock:
      return {
           "enabled": smart_enabled,
           "soil_threshold": smart_soil_threshold,
           "min_on_seconds": smart_min_on_seconds,
}
@app.get("/")
def read_root():
   return{"status":"irrigo ok"}

@app.post("/smart")
def set_smart(body: Dict[str, Any]):
    global smart_enabled, smart_soil_threshold, smart_min_on_seconds
    with state_lock:
       if "enabled" in body:
          smart_enabled = bool(body["enabled"])
       if "soil_threshold" in body:
          smart_soil_threshold = int(body["soil_threshold"])
       if "min_on_seconds" in body:
          smart_min_on_seconds = int(body["min_on_seconds"])
    return {"ok": True}
