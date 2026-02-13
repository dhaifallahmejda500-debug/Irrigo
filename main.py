 from fastapi import FastAPI
import json
import paho.mqtt.client as mqtt

app = FastAPI()

data = {
  "temperature": None,
  "humidity": None,
  "soil": None,
  "tank": None,
  "valve": False
}

MQTT_BROKER = "test.mosquitto.org"
MQTT_PORT = 1883
MQTT_TOPIC = "irrigo/data"


def on_connect(client, userdata, flags, rc):
  print("MQTT connected:", rc)
  client.subscribe(MQTT_TOPIC)


def on_message(client, userdata, msg):
  global data
  payload = json.loads(msg.payload.decode())
  print("Received:", payload)

  data["temperature"] = payload.get("temperature")
  data["humidity"] = payload.get("humidity")
  data["soil"] = payload.get("soil")
  data["tank"] = payload.get("tank")
  data["valve"] = payload.get("valve")


client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

client.connect(MQTT_BROKER, MQTT_PORT, 60)
client.loop_start()


@app.get("/data")
def get_data():
  return data