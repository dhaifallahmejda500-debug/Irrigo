import os
import json
import threading
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import paho.mqtt.client as mqtt

app = FastAPI()

# ---------- CONFIG MQTT ----------
MQTT_BROKER = os.getenv("MQTT_BROKER", "test.mosquitto.org")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
MQTT_TOPIC = os.getenv("MQTT_TOPIC", "irrigo/data")

# Valeurs par défaut (pas de "No data" -> on met null au début)
latest = {
  "temperature": None,
  "humidity": None,
  "soil": None,
  "tank": None,
  "valve": False
}

# ---------- MQTT CALLBACKS ----------
def on_connect(client, userdata, flags, rc):
   print("MQTT connected:", rc)
   client.subscribe(MQTT_TOPIC)
   print("Subscribed to:", MQTT_TOPIC)

def on_message(client, userdata, msg):
   global latest
   try:
     payload = msg.payload.decode("utf-8")
     data = json.loads(payload)

# Accepte plusieurs noms possibles si tu as changé (optionnel)
     latest["temperature"] = data.get("temperature", data.get("temp", latest["temperature"]))
     latest["humidity"] = data.get("humidity", data.get("humidite", latest["humidity"]))
     latest["soil"] = data.get("soil", data.get("sol", latest["soil"]))
     latest["tank"] = data.get("tank", data.get("reservoir", latest["tank"]))
     if "valve" in data:
        latest["valve"] = bool(data["valve"])

     print("Updated latest:", latest)
   except Exception as e:
     print("MQTT parse error:", e)

def mqtt_loop():
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message

    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    client.loop_forever()

# Lancer MQTT en background au démarrage
threading.Thread(target=mqtt_loop, daemon=True).start()

# ---------- STATIC FRONTEND ----------
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def home():
   return FileResponse("static/index.html")

@app.get("/data")
def get_data():
   return latest
