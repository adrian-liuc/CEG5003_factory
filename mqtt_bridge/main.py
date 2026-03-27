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

# 连接
try:
    influx_client = InfluxDBClient(url=INFLUXDB_URL, token=INFLUXDB_TOKEN, org=INFLUXDB_ORG)
    write_api = influx_client.write_api(write_options=SYNCHRONOUS)
    print(f"已连接到 InfluxDB: {INFLUXDB_URL}")
except Exception as e:
    print(f"InfluxDB 连接失败: {e}")
    exit(1)

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("已连接到 MQTT Broker")
        client.subscribe(MQTT_TOPICS)
        print(f"已订阅主题: {[t[0] for t in MQTT_TOPICS]}")
    else:
        print(f"MQTT 连接失败, 返回码: {rc}")

def on_message(client, userdata, msg):
    try:
        topic = msg.topic
        payload = msg.payload.decode("utf-8")
        
        # 解析
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

        # InfluxDB 数据点
        # Measurement 名称，factory
        # Tags 从 topic 中提取，factory_id
        
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
        print(f"已写入: {topic} -> {fields}")

    except Exception as e:
        print(f"处理消息出错: {e}")

# 设置 MQTT 客户端
client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

print(f"正在连接 MQTT Broker: {MQTT_BROKER}:{MQTT_PORT}...")
try:
    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    client.loop_forever()
except KeyboardInterrupt:
    print("\n程序已停止")
except Exception as e:
    print(f"\n发生错误: {e}")
finally:
    client.disconnect()
    influx_client.close()
