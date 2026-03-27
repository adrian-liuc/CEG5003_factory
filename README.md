# CEG5003 Factory

AI-powered factory production management system integrated with JaamSim simulation.

## Components

- **factory_agent/** — LLM agent for production control and monitoring
- **mqtt_bridge/** — Bridges JaamSim MQTT output to InfluxDB
- **simulation_files/** — JaamSim simulation config and assets

## Setup

Copy `.env.example` to `.env` and fill in your API keys.

## Startup Order

1. Start Mosquitto (port 1883) and InfluxDB (port 8086)
2. Open JaamSim with `simulation_files/simulation.cfg` and run the simulation
3. Start mqtt_bridge:
   ```bash
   python mqtt_bridge/main.py
   ```
4. Start the agent:
   ```bash
   cd factory_agent
   python -m uvicorn web_app:app --host 127.0.0.1 --port 8891
   ```
   Then open `http://127.0.0.1:8891` in browser.

## Features

| Feature | Example prompts |
|---------|----------------|
| **Query production data** | "Get factory B production data for the past 3 minutes" / "Show all factories data for the last 5 minutes" |
| **Set production quantity** | "Set factory A plan quantity to 200" / "Set all factories quantity to 100" |
| **Set production speed** | "Set factory C production speed to 4 seconds" |
| **Emergency shutdown** | "Emergency shutdown factory B" / "Shutdown all factories for maintenance" |
| **Long-term memory** | Remembers user preferences and past instructions across sessions |

Factories: `fa_p1` / `fb_p2` / `fc_p3` / `fd_p4`. Control actions require manual approval in the UI before taking effect.

## Structure

```
CEG5003_factory/
├── .env.example
├── factory_agent/
│   ├── config.py          # LLM / InfluxDB credentials and settings
│   ├── tools.py           # Tool definitions + execute_function
│   ├── agent_core.py      # LLM client, session init, token/memory management
│   ├── web_app.py         # FastAPI web server and routes
│   ├── factory_service.py # Read/write simulation control files
│   ├── influx_service.py  # Query production data from InfluxDB
│   ├── memory_service.py  # Long-term memory (markdown + SQLite FTS)
│   ├── memory/            # Memory files (bot_profile, user_profile, history...)
│   └── static/            # Frontend (index.html)
├── mqtt_bridge/
│   ├── config.py          # MQTT and InfluxDB connection config
│   └── main.py            # MQTT subscriber → InfluxDB writer
└── simulation_files/
    ├── simulation.cfg      # JaamSim simulation config
    ├── factory_files/      # Runtime control files (written by agent)
    ├── files/              # Branch data files
    └── display_model_logos/
```
