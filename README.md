# CEG5003 Factory

AI-powered factory production management system with JaamSim simulation, MQTT data pipeline, and a conversational LLM agent.

## Agent Features

Supports natural language queries and control commands:

| Category | Examples |
|----------|---------|
| Production query | `Past 3 minutes production` / `Production overview` |
| Set plan quantity | `Set factory A plan quantity to 200` |
| Emergency shutdown | `Emergency shutdown factory B` / `Restart factory B` |
| Set production interval | `Set factory C production speed to 4 seconds` |
| Waiting queue | `Waiting queue status` |
| Trend analysis | `Is output increasing?` / `Trend analysis`  |
| Long/short-term memory | Remembers preferences and instructions across sessions |


## Startup

Copy `.env.example` to `.env` and fill in your API keys and InfluxDB credentials, then start services in order:

1. Start **Mosquitto** (port 1883) and **InfluxDB** (port 8086)
2. Start **Grafana** (port 3000) and import `grafana_dashboard.json` via Grafana → Dashboards → Import
3. Open **JaamSim** with `simulation_files/simulation.cfg` and run the simulation
4. Start the MQTT bridge:
   ```bash
   python mqtt_bridge/main.py
   ```
5. Start the agent:
   ```bash
   cd factory_agent
   python -m uvicorn web_app:app --host 127.0.0.1 --port 8891
   ```
   Open `http://127.0.0.1:8891` in browser.


## Structure

```
CEG5003_factory/
├── grafana_dashboard.json     # Import into Grafana
├── factory_agent/
│   ├── config.py              # LLM / InfluxDB credentials and settings
│   ├── agent_core.py          # LLM client, session init, token/memory management
│   ├── web_app.py             # FastAPI server and agent loop
│   ├── tools.py               # Tool definitions and dispatcher
│   ├── factory_service.py     # Read/write simulation control files
│   ├── influx_service.py      # Query production data from InfluxDB
│   ├── memory_service.py      # Long-term memory (markdown + SQLite FTS)
│   ├── memory/
│   │   ├── agent_profile.md   # Agent role and response style
│   │   ├── factory_knowledge.md  # Domain knowledge and tool rules
│   │   ├── session_log.md     # Auto-saved conversation summaries
│   │   └── history.md         # Full conversation history
│   └── static/index.html      # Frontend UI
├── mqtt_bridge/
│   ├── config.py              # MQTT and InfluxDB connection config
│   └── main.py                # MQTT subscriber → InfluxDB writer
└── simulation_files/
    ├── simulation.cfg          # JaamSim simulation config
    ├── factory_files/          # Runtime control files (written by agent)
    └── display_model_logos/
```


## Tools (11 total)

**Production data** (read from InfluxDB)

| Tool | Description |
|------|-------------|
| `get_current_status` | Latest snapshot of all metrics — used for overview and waiting queue queries |
| `get_production_delta` | Units produced within a time window (last − first value) |
| `get_trend_data` | Per-minute bucketed output over N minutes for trend analysis |

**Factory control** (write to simulation, require approval)

| Tool | Description |
|------|-------------|
| `set_plan_quantity` | Set planned production quantity for a factory |
| `set_production_speed` | Set production interval (interarrival time in seconds) |
| `emergency_shutdown` | Set maxnum to 0 (immediate halt); backs up current quantity |
| `restart_production` | Restart factory by restoring pre-shutdown plan quantity from backup |

**Memory** (markdown + SQLite FTS)

| Tool | Description |
|------|-------------|
| `search_memory` | Full-text search across all memory files |
| `read_memory_file` | Read a specific memory file in full |
| `save_memory` | Append or overwrite content to a memory file |
| `list_memory_files` | List all available memory files |