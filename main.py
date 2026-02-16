 
import os
import json
import time
import threading

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

import paho.mqtt.client as mqtt


# ===============================
# CONFIG MQTT
# ===============================
MQTT_HOST = os.getenv("MQTT_HOST", "test.mosquitto.org")
MQTT_PORT = int(os.getenv("MQTT_PORT", 1883))

MQTT_TOPIC_DATA = "irrigo/data"
MQTT_TOPIC_CMD = "irrigo/cmd"


# ===============================
# APP FASTAPI
# ===============================
app = FastAPI(title="Irrigo API")

app.add_middleware(
  CORSMiddleware,
  allow_origins=["*"],
  allow_credentials=True,
  allow_methods=["*"],
  allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")


# ===============================
# DATA STATE
# ===============================
state_lock = threading.Lock()

last_data = {
  "temperature": 25.5,
  "humidity": 60,
  "soil": 45,
  "tank": 80,
  "motor": False,
  "valve": False
}


# ===============================
# MQTT
# ===============================
mqtt_client = mqtt.Client()


def on_connect(client, userdata, flags, rc):
  print("MQTT connected:", rc)
  client.subscribe(MQTT_TOPIC_DATA)


def on_message(client, userdata, msg):
  global last_data
  try:
    payload = msg.payload.decode()
    data = json.loads(payload)

    with state_lock:
      last_data.update(data)

    print("MQTT DATA:", data)

  except Exception as e:
    print("MQTT error:", e)


@app.on_event("startup")
def start_mqtt():
  try:
   mqtt_client.on_connect = on_connect
   mqtt_client.on_message = on_message

   mqtt_client.connect(MQTT_HOST, MQTT_PORT, 60)
   mqtt_client.loop_start()

   print("MQTT started")

  except Exception as e:
   print("MQTT start error:", e)


# ===============================
# ROUTES
# ===============================

@app.get("/")
def root():
  return FileResponse("static/index.html")


@app.get("/data")
def get_data():
  with state_lock:
   return last_data


@app.post("/cmd")
async def send_cmd(request: Request):
  body = await request.json()

  mqtt_client.publish(MQTT_TOPIC_CMD, json.dumps(body))

  return {"sent": True, "cmd": body}