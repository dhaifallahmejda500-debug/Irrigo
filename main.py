from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import paho.mqtt.client as mqtt
import json
import os 

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

# ---- DATA GLOBAL ----
last_data = {
"temperature": None,
"humidity": None,
"soil": None,
"tank": None,
"valve": False
}

# ---- MQTT ----
MQTT_BROKER = os.getenv("MQTT_BROKER","test.mosquitto.org") # si mosquitto est sur le même PC
MQTT_PORT = int(os.getenv("MQTT_PORT","1883"))
MQTT_TOPIC = "irrigation/data"

def on_connect(client, userdata, flags, rc):
    print("Connected to MQTT")
    client.subscribe(MQTT_TOPIC)

def on_message(client, userdata, msg):
    global last_data
    try:
       payload = msg.payload.decode()
       data = json.loads(payload) # ex: {"humidity":40,"temperature":25.5,"soil":45,"tank":80,"valve":true}

# on met à jour seulement ce qui existe
       for k in last_data.keys():
           if k in data:
              last_data[k] = data[k]

       print("Message received:", last_data)

    except Exception as e:
       print("MQTT error:", e)

mqtt_client = mqtt.Client()
mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message
mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
mqtt_client.loop_start()

# ---- ROUTES ----

# page principale
@app.get("/")
def home():
    return FileResponse("static/index.html")

# api status
@app.get("/data")
def get_data():
    return JSONResponse(last_data)

# toggle valve (simple)
@app.post("/toggle_valve")
def toggle_valve():
    global last_data
    last_data["valve"] = not last_data["valve"]

# option : publier l'état valve vers mqtt
    mqtt_client.publish("irrigation/valve", json.dumps({"valve": last_data["valve"]}))

    return JSONResponse({"valve": last_data["valve"]})