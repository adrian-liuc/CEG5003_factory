import os
import re
import json
import uuid
from datetime import datetime
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from agent_core import client, init_session, count_tokens, summarize_history
from tools import TOOLS, execute_function, NEEDS_APPROVAL
from memory_service import memory_service
from factory_service import factory_service
from config import MODEL_NAME

# Patterns that indicate "production over a time period" — force get_production_delta
_TIME_RANGE_PATTERN = re.compile(
    r"(过去|最近|last|past|前)\s*(\d+)?\s*(分钟|minute|min|hour|小时|秒|second)",
    re.IGNORECASE
)

def _extract_minutes(text: str) -> int:
    """Extract minutes from a time-range expression, defaulting to 1."""
    m = _TIME_RANGE_PATTERN.search(text)
    if not m:
        return 1
    num = m.group(2)
    unit = m.group(3).lower()
    n = int(num) if num else 1
    if unit in ("hour", "小时"):
        return n * 60
    if unit in ("second", "秒"):
        return max(1, n // 60)
    return n  # minutes

app = FastAPI(title="Factory Agent Dashboard")

os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

SESSION_MESSAGES = []


@app.on_event("startup")
async def startup_event():
    global SESSION_MESSAGES
    SESSION_MESSAGES = init_session()


@app.get("/", response_class=HTMLResponse)
async def get_index():
    if os.path.exists("static/index.html"):
        with open("static/index.html", "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>Static file not found.</h1>"


async def agent_loop(logs, forced_tool_choice=None, forced_args=None):
    global SESSION_MESSAGES

    # If a specific tool is forced, execute it immediately before the LLM loop
    if forced_tool_choice and forced_args:
        func_name = forced_tool_choice["function"]["name"]
        forced_id = f"forced_{uuid.uuid4().hex[:8]}"
        result = execute_function(func_name, forced_args)
        logs.append({"type": "call", "func_name": func_name, "args": forced_args})
        logs.append({"type": "result", "func_name": func_name, "result": str(result)[:500]})
        # Inject as if the assistant called the tool and got a result
        SESSION_MESSAGES.append({
            "role": "assistant", "content": "",
            "tool_calls": [{"id": forced_id, "type": "function",
                            "function": {"name": func_name, "arguments": json.dumps(forced_args)}}]
        })
        SESSION_MESSAGES.append({"role": "tool", "tool_call_id": forced_id, "content": str(result)})

    for _ in range(10):
        try:
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=SESSION_MESSAGES,
                tools=TOOLS,
                tool_choice="auto",
                temperature=0.1
            )
            assistant_message = response.choices[0].message
            assistant_msg = {"role": "assistant", "content": assistant_message.content or ""}
            if assistant_message.tool_calls:
                assistant_msg["tool_calls"] = [
                    {"id": tc.id, "type": tc.type, "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                    for tc in assistant_message.tool_calls
                ]
            SESSION_MESSAGES.append(assistant_msg)

            if not assistant_message.tool_calls:
                reply = assistant_message.content or "No response generated."
                try:
                    last_user = next((m for m in reversed(SESSION_MESSAGES) if m["role"] == "user"), None)
                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    memory_service.write_memory("history.md", f"**User** [{timestamp}]: {last_user['content']}\n**Agent**: {reply}", mode="append")
                except Exception as e:
                    logs.append({"type": "error", "content": f"Failed to save history: {e}"})
                return JSONResponse({"reply": reply, "logs": logs})

            pending_approvals = []
            for tool_call in assistant_message.tool_calls:
                func_name = tool_call.function.name
                func_args = json.loads(tool_call.function.arguments)

                if func_name in NEEDS_APPROVAL:
                    pending_approvals.append({"tool_call_id": tool_call.id, "func_name": func_name, "func_args": func_args})
                else:
                    logs.append({"type": "call", "func_name": func_name, "args": func_args})
                    result = execute_function(func_name, func_args)
                    logs.append({"type": "result", "func_name": func_name, "result": str(result)[:500]})
                    SESSION_MESSAGES.append({"role": "tool", "tool_call_id": tool_call.id, "content": str(result)})

            if pending_approvals:
                return JSONResponse({"reply": "Awaiting your approval.", "logs": logs, "pending_approvals": pending_approvals})

        except Exception as e:
            return JSONResponse({"reply": f"Internal error: {e}", "logs": logs})

    return JSONResponse({"reply": "Max iterations reached.", "logs": logs})


class ChatRequest(BaseModel):
    message: str

@app.post("/api/chat")
async def chat_endpoint(req: ChatRequest):
    global SESSION_MESSAGES
    user_input = req.message.strip()
    if not user_input:
        return JSONResponse({"reply": "Invalid input"})

    SESSION_MESSAGES.append({"role": "user", "content": user_input})

    if count_tokens(SESSION_MESSAGES) > 22000:
        SESSION_MESSAGES = summarize_history(SESSION_MESSAGES)

    # If the message is clearly about production over a time range, force the right tool
    forced_tool_choice = None
    forced_args = None
    if _TIME_RANGE_PATTERN.search(user_input):
        minutes = _extract_minutes(user_input)
        forced_tool_choice = {"type": "function", "function": {"name": "get_production_delta"}}
        forced_args = {"factory_id": "all", "minutes": minutes}

    return await agent_loop(logs=[], forced_tool_choice=forced_tool_choice, forced_args=forced_args)


class ApproveItem(BaseModel):
    tool_call_id: str
    approved: bool

class ApproveRequest(BaseModel):
    approvals: list[ApproveItem]

@app.post("/api/approve")
async def approve_endpoint(req: ApproveRequest):
    global SESSION_MESSAGES
    logs = []

    last_assistant = next((m for m in reversed(SESSION_MESSAGES) if m["role"] == "assistant"), None)
    if not last_assistant or not last_assistant.get("tool_calls"):
        return JSONResponse({"reply": "No pending tool calls found.", "logs": logs})

    for approval in req.approvals:
        tc = next((t for t in last_assistant["tool_calls"] if t["id"] == approval.tool_call_id), None)
        if not tc:
            continue
        func_name = tc["function"]["name"]
        func_args = json.loads(tc["function"]["arguments"])
        logs.append({"type": "call", "func_name": func_name, "args": func_args})

        if approval.approved:
            result = execute_function(func_name, func_args)
            content = str(result)
        else:
            result = "Action rejected by user."
            content = result
        logs.append({"type": "result", "func_name": func_name, "result": str(result)[:500]})
        SESSION_MESSAGES.append({"role": "tool", "tool_call_id": approval.tool_call_id, "content": content})

    return await agent_loop(logs=logs)


@app.post("/api/reset")
async def reset_session():
    global SESSION_MESSAGES
    SESSION_MESSAGES = init_session()
    return JSONResponse({"status": "ok"})


@app.get("/api/status")
async def get_factory_status():
    return JSONResponse(factory_service.get_status())
