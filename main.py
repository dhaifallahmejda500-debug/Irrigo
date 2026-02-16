import os
import json
import time
import threading
from typing import Any, Dict, Optional, List

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

import paho.mqtt.client as mqtt


# =========================
# CONFIG MQTT
# =========================
MQTT_HOST = os.getenv("MQTT_HOST", "test.mosquitto.org")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
MQTT_USER = os.getenv("MQTT_USER", "").strip()
MQTT_PASS = os.getenv("MQTT_PASS", "").strip()

TOPIC_DATA = os.getenv("MQTT_TOPIC_DATA", "irrigo/data") # capteurs (JSON)
TOPIC_CMD = os.getenv("MQTT_TOPIC_CMD", "irrigo/cmd") # commandes (JSON)


# =========================
# APP + STATIC
# =========================
app = FastAPI(title="Irrigo WebApp", version="1.0.0")

# servir /static/*
app.mount("/static", StaticFiles(directory="static"), name="static")

# page principale = index.html
@app.get("/")
def serve_app():
   return FileResponse("index.html")


# =========================
# STATE
# =========================
lock = threading.Lock()

mqtt_connected = False

# capteurs
sensors: Dict[str, Any] = {
   "temperature": 25.5,
   "humidity": 60,
   "soil": 45,
   "tank": 80,
   "updated_at": None,
}

# actionneurs
actuators: Dict[str, Any] = {
   "valve": False,
   "motor": False,
}

# timers (simple en mémoire)
timers: List[Dict[str, Any]] = [] # [{"id": "...", "valve":"Valve 1","from":"2026-02-08 21:36","to":"2026-02-10 21:36"}]

mqtt_client = mqtt.Client()


# =========================
# MQTT callbacks
# =========================
def mqtt_publish(payload: Dict[str, Any]) -> None:
    mqtt_client.publish(TOPIC_CMD, json.dumps(payload), qos=0)

def on_connect(client, userdata, flags, rc, properties=None):
    global mqtt_connected
    mqtt_connected = (rc == 0)
    print("MQTT connect rc =", rc)
    if rc == 0:
       client.subscribe(TOPIC_DATA)
       print("Subscribed to:", TOPIC_DATA)

def on_message(client, userdata, msg):
   try:
      payload = msg.payload.decode("utf-8", errors="replace")
      data = json.loads(payload)
      with lock:
# attendu: {"temperature":..,"humidity":..,"soil":..,"tank":..}
        for k in ["temperature", "humidity", "soil", "tank"]:
           if k in data:
              sensors[k] = data[k]
        sensors["updated_at"] = int(time.time())
   except Exception as e:
        print("MQTT message error:", e)


@app.on_event("startup")
def start_mqtt():
# IMPORTANT: démarrage MQTT après uvicorn => pas de timeout Render
   try:
     mqtt_client.on_connect = on_connect
     mqtt_client.on_message = on_message
     if MQTT_USER or MQTT_PASS:
        mqtt_client.username_pw_set(MQTT_USER, MQTT_PASS)

     mqtt_client.connect(MQTT_HOST, MQTT_PORT, 60)
     mqtt_client.loop_start()
     print("MQTT started")
   except Exception as e:
     print("MQTT startup error:", e)


@app.on_event("shutdown")
def stop_mqtt():
  try:
     mqtt_client.loop_stop()
     mqtt_client.disconnect()
  except Exception:
   pass


# =========================
# API pour l'UI (app.js)
# =========================
@app.get("/api/dashboard")
def get_dashboard():
  with lock:
   return {
   "mqtt_connected": mqtt_connected,
   "sensors": sensors,
   "actuators": actuators,
   "config": {
      "MQTT_HOST": MQTT_HOST,
      "MQTT_PORT": MQTT_PORT,
      "TOPIC_DATA": TOPIC_DATA,
      "TOPIC_CMD": TOPIC_CMD,
}
}

@app.post("/api/actuators/valve")
def set_valve(body: Dict[str, Any]):
   if "on" not in body:
     raise HTTPException(status_code=400, detail="Missing 'on'")
   on = bool(body["on"])
   with lock:
     actuators["valve"] = on
   mqtt_publish({"device": "valve", "on": on})
   return {"ok": True, "valve": on}

@app.post("/api/actuators/motor")
def set_motor(body: Dict[str, Any]):
   if "on" not in body:
    raise HTTPException(status_code=400, detail="Missing 'on'")
   on = bool(body["on"])
   with lock:
     actuators["motor"] = on
   mqtt_publish({"device": "motor", "on": on})
   return {"ok": True, "motor": on}

@app.get("/api/timers")
def list_timers():
   with lock:
     return {"items": timers}

@app.post("/api/timers")
def add_timer(body: Dict[str, Any]):
# attendu: {"valve":"Valve 1","from":"YYYY-MM-DD HH:MM","to":"YYYY-MM-DD HH:MM"}
  for k in ["valve", "from", "to"]:
     if k not in body:
       raise HTTPException(status_code=400, detail=f"Missing '{k}'")

  item = {
    "id": str(int(time.time() * 1000))[-8:],
    "valve": str(body["valve"]),
    "from": str(body["from"]),
    "to": str(body["to"]),
}
  with lock:
    timers.insert(0, item)

  mqtt_publish({"type": "timer_add", **item})
  return {"ok": True, "item": item}

@app.delete("/api/timers/{timer_id}")
def delete_timer(timer_id: str):
  with lock:
    before = len(timers)
    timers[:] = [t for t in timers if t["id"] != timer_id]
    deleted = (len(timers) != before)
  mqtt_publish({"type": "timer_delete", "id": timer_id})
  return {"ok": True, "deleted": deleted}