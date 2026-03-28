from factory_service import factory_service
from influx_service import influx_service
from memory_service import memory_service

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_memory",
            "description": "Search long-term memory (markdown files) to get relevant info.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search keyword"}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_memory_file",
            "description": "Read the entire content of a specific memory file. Available: 'agent_profile.md', 'factory_knowledge.md', 'session_log.md', 'history.md'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "Filename, e.g. 'factory_knowledge.md'"}
                },
                "required": ["filename"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "save_memory",
            "description": "Save information to memory. filename options: 'agent_profile.md', 'factory_knowledge.md', 'session_log.md', 'history.md'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "content": {"type": "string", "description": "Content to save"},
                    "filename": {"type": "string", "description": "Filename", "default": "history.md"},
                    "mode": {"type": "string", "enum": ["append", "overwrite"], "default": "append"}
                },
                "required": ["content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_memory_files",
            "description": "List all available memory files.",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "set_plan_quantity",
            "description": "Set the planned production quantity for factories.",
            "parameters": {
                "type": "object",
                "properties": {
                    "factory_id": {"type": "string", "description": "Factory ID: 'fa_p1', 'fb_p2', 'fc_p3', 'fd_p4', or 'all'"},
                    "quantity": {"type": "integer", "description": "Planned production quantity"}
                },
                "required": ["factory_id", "quantity"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "set_production_speed",
            "description": "Set factory production speed (InterArrival time in seconds).",
            "parameters": {
                "type": "object",
                "properties": {
                    "factory_id": {"type": "string", "description": "Factory ID: 'fa_p1', 'fb_p2', 'fc_p3', 'fd_p4', or 'all'"},
                    "speed": {"type": "number", "description": "Interarrival time in seconds, e.g. 4 or 4.5"}
                },
                "required": ["factory_id", "speed"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "emergency_shutdown",
            "description": "Emergency shutdown: sets factory maxnum to 0.",
            "parameters": {
                "type": "object",
                "properties": {
                    "factory_id": {"type": "string", "description": "Factory ID: 'fa_p1', 'fb_p2', 'fc_p3', 'fd_p4', or 'all'"}
                },
                "required": ["factory_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_trend_data",
            "description": "Get per-minute production data aggregated into 1-minute buckets for trend analysis. Use when the user asks about trends, patterns, rising/falling output, or wants to see how production changed over time (e.g. '趋势', '变化', 'trend', 'increasing', 'decreasing').",
            "parameters": {
                "type": "object",
                "properties": {
                    "factory_id": {"type": "string", "description": "Factory: 'fa', 'fb', 'fc', 'fd', or 'all'"},
                    "minutes": {"type": "integer", "description": "How many minutes of history to fetch. Default is 10."}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_production_delta",
            "description": "Get units produced within a time window (last value minus first value of each production metric). Use when the user asks about production over a time period: '过去N分钟', '最近N分钟', 'past N minutes', 'last N minutes'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "factory_id": {"type": "string", "description": "Factory: 'fa', 'fb', 'fc', 'fd', or 'all'"},
                    "minutes": {"type": "integer", "description": "Time window in minutes. Default is 1."}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_current_status",
            "description": "Get the latest value of every metric across all factories (one data point per metric). Use for: logistics/waiting queue queries ('物流', '上下游', '等待队列', 'wait queue'), and overall production overview ('总体情况', '生产总览', 'overview').",
            "parameters": {
                "type": "object",
                "properties": {
                    "factory_id": {"type": "string", "description": "Factory: 'fa', 'fb', 'fc', 'fd', or 'all'. Default is 'all'."}
                }
            }
        }
    }
]

NEEDS_APPROVAL = {"set_plan_quantity", "set_production_speed", "emergency_shutdown"}

def execute_function(name, arguments):
    if name == "search_memory":
        results = memory_service.search(arguments["query"])
        if not results:
            return "No matching memory found."
        return "Relevant memories found:\n" + "".join(f"- [{r['file']}] ...{r['snippet']}...\n" for r in results)

    elif name == "read_memory_file":
        return memory_service.read_file(arguments["filename"])

    elif name == "save_memory":
        return memory_service.write_memory(
            arguments.get("filename", "history.md"),
            arguments["content"],
            arguments.get("mode", "append")
        )

    elif name == "list_memory_files":
        return f"Available memory files: {', '.join(memory_service.list_files())}"

    elif name == "set_plan_quantity":
        return factory_service.set_plan_quantity(arguments["factory_id"], arguments["quantity"])

    elif name == "set_production_speed":
        return factory_service.set_production_speed(arguments["factory_id"], arguments["speed"])

    elif name == "emergency_shutdown":
        return factory_service.emergency_shutdown(arguments["factory_id"])

    elif name == "get_trend_data":
        return influx_service.get_trend_data(
            arguments.get("factory_id", "all"),
            arguments.get("minutes", 10)
        )

    elif name == "get_production_delta":
        return influx_service.get_production_delta(
            arguments.get("factory_id", "all"),
            arguments.get("minutes", 1)
        )

    elif name == "get_current_status":
        return influx_service.get_current_status(
            arguments.get("factory_id", "all")
        )

    return "Unknown function"
