# CEG5003 Factory

AI-powered factory production management system integrated with JaamSim simulation.

## Components

- **factory_agent/** — LLM agent for production control and monitoring
- **mqtt_bridge/** — Bridges JaamSim MQTT output to InfluxDB
- **simulation_files/** — JaamSim simulation config and assets
- **grafana_dashboard.json** — Grafana dashboard (import via Grafana UI)

## Startup Order

1. Start **Mosquitto** (port 1883) and **InfluxDB** (port 8086)
2. Start **Grafana** (port 3000) and import `grafana_dashboard.json`:
   - Grafana → Dashboards → Import → Upload JSON file
3. Open **JaamSim** with `simulation_files/simulation.cfg` and run the simulation
4. Start **mqtt_bridge**:
   ```bash
   python mqtt_bridge/main.py
   ```
5. Start the **agent**:
   ```bash
   cd factory_agent
   python -m uvicorn web_app:app --host 127.0.0.1 --port 8891
   ```
   Then open `http://127.0.0.1:8891` in browser.

> **Note:** Grafana must be running before starting the agent, as the agent dashboard embeds Grafana via iframe on port 3000.

## Setup

Copy `.env.example` to `.env` and fill in your API keys and InfluxDB credentials.

## Agent Features

| Feature | Example prompts |
|---------|----------------|
| **Time-period production** | "过去一分钟的生产情况" / "Past 5 minutes production" |
| **Current overview** | "生产总览" / "Overall status" |
| **Logistics / wait queue** | "物流情况" / "Waiting queue" |
| **Trend analysis** | "生产趋势" / "Is output increasing?" |
| **Set production quantity** | "Set factory A plan quantity to 200" |
| **Set production speed** | "Set factory C production speed to 4 seconds" |
| **Emergency shutdown** | "Emergency shutdown factory B" |
| **Long-term memory** | Remembers preferences and past instructions across sessions |

Factory IDs: `fa_p1` / `fb_p2` / `fc_p3` / `fd_p4`. Control actions require manual approval in the UI.

## Supply Chain

```
FA (P1) ──→ FB: assembly → P12
FA (P1) ──→ FC: assembly → P13
FB (P2) ──→ FC: assembly → P23
FC (P23) ─→ FD: assembly → P234
FD also produces P4 internally
```

## Structure

```
CEG5003_factory/
├── README.md
├── grafana_dashboard.json     # Import into Grafana
├── factory_agent/
│   ├── config.py              # LLM / InfluxDB credentials and settings
│   ├── agent_core.py          # LLM client, session init, token/memory management
│   ├── web_app.py             # FastAPI server and agent loop
│   ├── tools.py               # Tool definitions and execute_function
│   ├── factory_service.py     # Read/write simulation control files
│   ├── influx_service.py      # Query production data from InfluxDB
│   ├── memory_service.py      # Long-term memory (markdown + SQLite FTS)
│   ├── memory/
│   │   ├── agent_profile.md   # Agent role and response style
│   │   ├── factory_knowledge.md  # Factory domain knowledge and tool rules
│   │   ├── session_log.md     # Auto-saved conversation summaries
│   │   └── history.md         # Full conversation history
│   └── static/
│       └── index.html         # Frontend UI
├── mqtt_bridge/
│   ├── config.py              # MQTT and InfluxDB connection config
│   └── main.py                # MQTT subscriber → InfluxDB writer
└── simulation_files/
    ├── simulation.cfg          # JaamSim simulation config
    ├── factory_files/          # Runtime control files (written by agent)
    └── display_model_logos/
```
