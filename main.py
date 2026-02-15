import os
import json
import time
import threading
from typing import Any, Dict, Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import paho.mqtt.client as mqtt


# =========================
# CONFIG (ENV VARS)
# =========================
MQTT_HOST = os.getenv("MQTT_HOST", "test.mosquitto.org")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))

MQTT_USER = os.getenv("MQTT_USER", "").strip()
MQTT_PASS = os.getenv("MQTT_PASS", "").strip()

MQTT_TOPIC_DATA = os.getenv("MQTT_TOPIC_DATA", "irrigo/data")
MQTT_TOPIC_CMD = os.getenv("MQTT_TOPIC_CMD", "irrigo/cmd")


# =========================
# APP
# =========================
app = FastAPI(title="Irrigo API", version="1.0.0")

# CORS (si tu appelles l’API depuis un front)
app.add_middleware(
   CORSMiddleware,
   allow_origins=["*"],
   allow_credentials=False,
   allow_methods=["*"],
   allow_headers=["*"],
)

# =========================
# STATE
# =========================
state_lock = threading.Lock()
last_data: Optional[Dict[str, Any]] = None
mqtt_connected: bool = False

mqtt_client = mqtt.Client() # MQTT client global


# =========================
# MQTT CALLBACKS
# =========================
def on_connect(client, userdata, flags, rc, properties=None):
  global mqtt_connected
  mqtt_connected = (rc == 0)
  print("MQTT connected, rc =", rc)

  if rc == 0:
     try:
        client.subscribe(MQTT_TOPIC_DATA)
        print("Subscribed to:", MQTT_TOPIC_DATA)
     except Exception as e:
        print("MQTT subscribe error:", e)


def on_message(client, userdata, msg):
   global last_data
   try:
      payload = msg.payload.decode("utf-8", errors="replace")
      data = json.loads(payload) # si ton topic data envoie du JSON
      with state_lock:
         last_data = {
         "topic": msg.topic,
         "data": data,
         "received_at": time.time(),
}
   except Exception as e:
         print("MQTT message error:", e)


def mqtt_publish(payload: Dict[str, Any]) -> bool:
    """
Publie une commande sur MQTT_TOPIC_CMD.
Retourne True si publication lancée.
    """
    try:
       mqtt_client.publish(MQTT_TOPIC_CMD, json.dumps(payload), qos=0)
       return True
    except Exception as e:
       print("MQTT publish error:", e)
       return False


# =========================
# STARTUP / SHUTDOWN
# =========================
@app.on_event("startup")
def start_mqtt():
   """
IMPORTANT: On démarre MQTT ici (après que FastAPI soit lancé par uvicorn),
sinon Render peut timeout en pensant qu’aucun port n’est ouvert.
   """
   try:
     mqtt_client.on_connect = on_connect
     mqtt_client.on_message = on_message

# Auth optionnelle
     if MQTT_USER or MQTT_PASS:
         mqtt_client.username_pw_set(MQTT_USER, MQTT_PASS)

# Connexion + boucle non bloquante
     mqtt_client.connect(MQTT_HOST, MQTT_PORT, keepalive=60)
     mqtt_client.loop_start()
     print("MQTT started")
   except Exception as e:
     print("MQTT startup error:", e)


@app.on_event("shutdown")
def stop_mqtt():
   try:
     mqtt_client.loop_stop()
     mqtt_client.disconnect()
     print("MQTT stopped")
   except Exception as e:
     print("MQTT shutdown error:", e)


# =========================
# ROUTES
# =========================
@app.get("/")
def root():
   return {
     "service": "Irrigo API",
     "status": "ok",
     "mqtt_host": MQTT_HOST,
     "mqtt_port": MQTT_PORT,
     "mqtt_connected": mqtt_connected,
}


@app.get("/data")
def get_last_data():
   with state_lock:
     return {"last_data": last_data}


@app.post("/cmd")
def send_command(cmd: Dict[str, Any]):
   """
Exemple: POST /cmd avec body JSON:
{ "action": "start", "duration": 10 }
   """
   ok = mqtt_publish(cmd)
   return {"published": ok, "topic": MQTT_TOPIC_CMD, "cmd": cmd}