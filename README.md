# CEG5003 Factory

AI-powered factory production management system integrated with JaamSim simulation.

## Components

- **[factory_agent/](factory_agent/README.md)** — LLM agent for production control and monitoring
- **mqtt_bridge/** — Bridges JaamSim MQTT output to InfluxDB
- **simulation_files/** — JaamSim simulation config and assets

## Quick Start

1. Copy `.env.example` to `.env` and fill in your API keys
2. Start Mosquitto, InfluxDB, and JaamSim simulation
3. Run mqtt_bridge: `python mqtt_bridge/main.py`
4. Run agent: `cd factory_agent && python -m uvicorn web_app:app --host 127.0.0.1 --port 8891`
