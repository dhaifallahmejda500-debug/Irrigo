from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import paho.mqtt.client as mqtt
import json
import time

app = FastAPI()

# CORS (pour téléphone / navigateur)
app.add_middleware(
CORSMiddleware,
   allow_origins=["*"],
   allow_credentials=True,
   allow_methods=["*"],
   allow_headers=["*"],
)

# dossier static
app.mount("/static", StaticFiles(directory="static"), name="static")

# ========= MQTT CONFIG =========
MQTT_BROKER = "test.mosquitto.org"
MQTT_PORT = 1883
MQTT_TOPIC = "irrigo/data" # <-- IMPORTANT: mets ici ton topic exact

# ========= DATA STORAGE =========
last_data = {
   "temperature": None,
   "humidity": None,
   "soil": None,
   "tank": None,
   "valve": False
}
last_update = 0.0 # timestamp (seconds)

def on_connect(client, userdata, flags, rc):
   print("Connected to MQTT with code:", rc)
   client.subscribe(MQTT_TOPIC)

def on_message(client, userdata, msg):
   global last_data, last_update
   try:
     payload = msg.payload.decode()
     data = json.loads(payload)

# on met à jour seulement si la clé existe
     if "temperature" in data: last_data["temperature"] = data["temperature"]
     if "humidity" in data: last_data["humidity"] = data["humidity"]
     if "soil" in data: last_data["soil"] = data["soil"]
     if "tank" in data: last_data["tank"] = data["tank"]
     if "valve" in data: last_data["valve"] = data["valve"]

     last_update = time.time() # dernière fois qu'on a reçu une donnée MQTT
     print("MQTT data:", last_data)

   except Exception as e:
     print("MQTT decode error:", e)

mqtt_client = mqtt.Client()
mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message
mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
mqtt_client.loop_start()

# ========= ROUTES =========
@app.get("/")
def home():
    return FileResponse("static/index.html")

@app.get("/data")
def get_data():
# Online si on a reçu une donnée il y a moins de 10s
    now = time.time()
    seconds_since = (now - last_update) if last_update else None
    online = (seconds_since is not None) and (seconds_since <= 10)

    return {
     **last_data,
     "online": online,
     "seconds_since_update": seconds_since
}
@app.post("/toggle_valve")
def toggle_valve():
   last_data ["valve"]=not last_data["valve"]
   return {"valve":last_data["valve"]}