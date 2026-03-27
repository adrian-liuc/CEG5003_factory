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
            "description": "Read the entire content of a specific memory file. Available: 'bot_profile.md', 'user_profile.md', 'important_memory.md', 'history.md'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "Filename, e.g. 'bot_profile.md'"}
                },
                "required": ["filename"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "save_memory",
            "description": "Save information to memory. filename options: 'bot_profile.md', 'user_profile.md', 'important_memory.md', 'history.md'.",
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
            "name": "get_factory_data",
            "description": "Query factory production data from InfluxDB for a given time range.",
            "parameters": {
                "type": "object",
                "properties": {
                    "factory_id": {"type": "string", "description": "Factory: 'fa', 'fb', 'fc', 'fd', or 'all'"},
                    "minutes": {"type": "integer", "description": "Query data from the past N minutes. Default is 5."}
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
            arguments["content"],
            arguments.get("filename", "history.md"),
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

    elif name == "get_factory_data":
        return influx_service.get_factory_data(
            arguments.get("factory_id", "all"),
            arguments.get("minutes", 5)
        )

    return "Unknown function"
