import sys
import os
import json
import time

from datetime import datetime
import paho.mqtt.client as mqtt
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS
from config import (
    MQTT_BROKER, MQTT_PORT, MQTT_TOPICS,
    INFLUXDB_URL, INFLUXDB_TOKEN, INFLUXDB_ORG, INFLUXDB_BUCKET
)

try:
    influx_client = InfluxDBClient(url=INFLUXDB_URL, token=INFLUXDB_TOKEN, org=INFLUXDB_ORG)
    write_api = influx_client.write_api(write_options=SYNCHRONOUS)
    print(f"Connected to InfluxDB: {INFLUXDB_URL}")
except Exception as e:
    print(f"InfluxDB connection failed: {e}")
    exit(1)

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Connected to MQTT broker")
        client.subscribe(MQTT_TOPICS)
        print(f"Subscribed to: {[t[0] for t in MQTT_TOPICS]}")
    else:
        print(f"MQTT connection failed, rc={rc}")

def on_message(client, userdata, msg):
    try:
        topic = msg.topic
        payload = msg.payload.decode("utf-8")
        
        fields = {}
        try:
            data = json.loads(payload)
            if isinstance(data, dict):
                for k, v in data.items():
                    if isinstance(v, (int, float, bool)):
                        fields[k] = v
                    else:
                        fields[k] = str(v)
            else:
                fields["value"] = float(data)
        except ValueError:
            try:
                fields["value"] = float(payload)
            except ValueError:
                fields["raw_value"] = payload

        if not fields:
            return

        parts = topic.split("/")
        measurement = parts[0] if len(parts) > 0 else "mqtt_data"
        factory_id = parts[1] if len(parts) > 1 else "unknown"
        sub_topic = parts[2] if len(parts) > 2 else "generic"

        point = Point(measurement)\
            .tag("factory_id", factory_id)\
            .tag("sub_topic", sub_topic)\
            .tag("topic", topic)
        
        for k, v in fields.items():
            point = point.field(k, v)
            
        point = point.time(datetime.utcnow(), WritePrecision.NS)

        write_api.write(bucket=INFLUXDB_BUCKET, org=INFLUXDB_ORG, record=point)
        print(f"wrote: {topic} -> {fields}")

    except Exception as e:
        print(f"message handling error: {e}")

client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

print(f"Connecting to MQTT broker: {MQTT_BROKER}:{MQTT_PORT}...")
try:
    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    client.loop_forever()
except KeyboardInterrupt:
    print("\nStopped.")
except Exception as e:
    print(f"\nError: {e}")
finally:
    client.disconnect()
    influx_client.close()
