from dotenv import load_dotenv
import os
from pathlib import Path

load_dotenv(Path(__file__).parent.parent / ".env")

# MQTT 配置
MQTT_BROKER = "localhost"
MQTT_PORT = 1883
MQTT_TOPICS = [
    ("factory/fa/#", 0),
    ("factory/fb/#", 0),
    ("factory/fc/#", 0),
    ("factory/fd/#", 0),
]

# InfluxDB 配置
INFLUXDB_URL = os.getenv("INFLUXDB_URL")
INFLUXDB_TOKEN = os.getenv("INFLUXDB_TOKEN")
INFLUXDB_ORG = os.getenv("INFLUXDB_ORG")
INFLUXDB_BUCKET = os.getenv("INFLUXDB_BUCKET")
