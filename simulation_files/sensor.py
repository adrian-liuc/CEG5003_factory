#!/usr/bin/env python
# -*- coding: utf-8 -*-
# MQTT JSON-RPC server — reads JSON requests from stdin, responds on stdout

import sys
import json
import paho.mqtt.client as mqtt
import threading
import time

# MQTT Configuration
BROKER_HOST = "localhost"  # Server IP or domain name
BROKER_PORT = 1883  # MQTT default port

# Global MQTT client
mqtt_client = None
connected = False
lock = threading.Lock()
subscribed_topics = set()


def log_info(message):
    print(f"[INFO] {message}", file=sys.stderr)
    sys.stderr.flush()


def log_error(message):
    print(f"[ERROR] {message}", file=sys.stderr)
    sys.stderr.flush()


def on_connect(client, userdata, flags, rc):
    global connected
    if rc == 0:
        connected = True
        log_info(f"Successfully connected to MQTT broker: {BROKER_HOST}:{BROKER_PORT}")
        # Re-subscribe to previous topics
        with lock:
            for topic in subscribed_topics:
                client.subscribe(topic, qos=1)
                log_info(f"Re-subscribed to topic: {topic}")
    else:
        connected = False
        log_error(f"Failed to connect to MQTT broker, return code: {rc}")


def on_disconnect(client, userdata, rc):
    global connected
    connected = False
    if rc != 0:
        log_error(f"Unexpected disconnection, return code: {rc}")
    else:
        log_info("Disconnected from MQTT broker")


def on_message(client, userdata, msg):
    try:
        message = msg.payload.decode('utf-8')
        log_info(f"Received message - Topic: {msg.topic}, Message: {message}")
    except Exception as e:
        log_error(f"Error processing received message: {e}")


def init_mqtt():
    global mqtt_client

    import uuid
    suffix = uuid.uuid4().hex[:8]
    client_id = f"mqtt_json_rpc_{suffix}"

    mqtt_client = mqtt.Client(client_id=client_id)

    mqtt_client.on_connect = on_connect
    mqtt_client.on_disconnect = on_disconnect
    mqtt_client.on_message = on_message

    try:
        mqtt_client.connect(BROKER_HOST, BROKER_PORT, 60)
        mqtt_client.loop_start()
        log_info(f"MQTT client '{client_id}' started, connecting to {BROKER_HOST}:{BROKER_PORT}")
    except Exception as e:
        log_error(f"Failed to connect to MQTT broker: {e}")


def publish_message(params):
    try:
        msg = params[0]
        topic = params[1]
        
        if not msg or not topic:
            return {"status": "error", "message": "Missing msg or topic parameter"}
        
        if not connected:
            return {"status": "error", "message": "MQTT not connected"}
        
        # Use thread lock to ensure concurrent safety
        with lock:
            result = mqtt_client.publish(topic, msg, qos=1)
        
        if result.rc == mqtt.MQTT_ERR_SUCCESS:
            log_info(f"Message published successfully - Topic: {topic}, Message: {msg}")
            return {
                "status": "success",
                "message": "Message published successfully",
                "topic": topic
            }
        else:
            log_error(f"Failed to publish message - Topic: {topic}, Error code: {result.rc}")
            return {
                "status": "error",
                "message": f"Publish failed, error code: {result.rc}",
                "topic": topic
            }
    
    except Exception as e:
        log_error(f"Exception occurred while publishing message: {e}")
        return {"status": "error", "message": str(e)}


def subscribe_message(params):
    try:
        topic = params.get("topic")
        
        if not topic:
            return {"status": "error", "message": "Missing topic parameter"}
        
        if not connected:
            return {"status": "error", "message": "MQTT not connected"}
        
        # Use thread lock to ensure concurrent safety
        with lock:
            result = mqtt_client.subscribe(topic, qos=1)
            subscribed_topics.add(topic)
        
        if result[0] == mqtt.MQTT_ERR_SUCCESS:
            log_info(f"Successfully subscribed to topic: {topic}")
            return {
                "status": "success",
                "message": "Subscribed successfully",
                "topic": topic
            }
        else:
            log_error(f"Failed to subscribe to topic - Topic: {topic}, Error code: {result[0]}")
            return {
                "status": "error",
                "message": f"Subscribe failed, error code: {result[0]}",
                "topic": topic
            }
    
    except Exception as e:
        log_error(f"Exception occurred while subscribing to topic: {e}")
        return {"status": "error", "message": str(e)}


def get_status(params):
    return {
        "connected": connected,
        "broker_host": BROKER_HOST,
        "broker_port": BROKER_PORT,
        "subscribed_topics": list(subscribed_topics)
    }


# Method dispatch table
methods = {
    "publish_message": publish_message,
    "subscribe_message": subscribe_message,
    "get_status": get_status
}


def main():
    init_mqtt()
    log_info("JSON-RPC service started")

    for line in sys.stdin:
        try:
            request = json.loads(line)
            method = request.get("method")
            params = request.get("params", {})
            req_id = request.get("id")

            log_info(f"method={method} id={req_id}")

            if method in methods:
                try:
                    result = methods[method](params)
                    if isinstance(result, dict) and result.get("status") == "error":
                        response = {
                            "jsonrpc": "2.0",
                            "id": req_id,
                            "error": {"message": result.get("message", "Unknown error")}
                        }
                    else:
                        response = {
                            "jsonrpc": "2.0",
                            "id": req_id,
                            "result": result,
                        }
                except Exception as e:
                    log_error(f"Exception in method {method}: {e}")
                    response = {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "error": {"message": str(e)}
                    }
            else:
                log_error(f"Unknown method: {method}")
                response = {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {"message": f"Unknown method: {method}"}
                }
            
            print(json.dumps(response, ensure_ascii=False))
            sys.stdout.flush()
        
        except json.JSONDecodeError as e:
            log_error(f"JSON parsing error: {e}")
            err = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {"message": f"JSON parsing error: {str(e)}"}
            }
            print(json.dumps(err, ensure_ascii=False))
            sys.stdout.flush()
        
        except Exception as e:
            log_error(f"Exception occurred while processing request: {e}")
            err = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {"message": str(e)}
            }
            print(json.dumps(err, ensure_ascii=False))
            sys.stdout.flush()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log_info("Interrupt signal received, shutting down...")
    finally:
        if mqtt_client:
            mqtt_client.loop_stop()
            mqtt_client.disconnect()
            log_info("MQTT client closed")
