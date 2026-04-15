from openai import OpenAI
from memory_service import memory_service
from config import API_KEY, BASE_URL, MODEL_NAME, MAX_CONTEXT_TOKENS, MAX_HISTORY_KEEP

client = OpenAI(api_key=API_KEY, base_url=BASE_URL)

def init_session():
    """加载记忆文件，初始化消息历史"""
    profiles = []
    for filename in ["agent_profile.md", "factory_knowledge.md", "session_log.md"]:
        content = memory_service.read_file(filename)
        if "does not exist" not in content.lower():
            profiles.append(content)
    system_prompt = "\n\n".join(profiles) if profiles else "You are a smart factory assistant."
    return [{"role": "system", "content": system_prompt}]

def count_tokens(messages):
    """估算 token 数（字符数 × 0.1）"""
    total = 0
    for msg in messages:
        content = msg.get("content", "") or ""
        total += int(len(content) * 0.1)
    return total

def summarize_history(messages):
    """超出上下文限制时总结历史"""
    print(f"\n[System] Token limit exceeded, summarizing memory...")
    summary_prompt = {"role": "user", "content": "Summarize the key information, decisions, and user preferences from the conversation above. Keep only important facts, ignore chit-chat."}
    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=messages + [summary_prompt],
        temperature=0.1
    )
    summary = response.choices[0].message.content
    memory_service.write_memory("session_log.md", summary, mode="append")

    system_msg = messages[0] if messages and messages[0]["role"] == "system" else None
    recent = messages[-MAX_HISTORY_KEEP:]
    new_messages = ([system_msg] if system_msg else []) + recent
    print(f"[System] Summarized. Kept last {MAX_HISTORY_KEEP} messages.")
    return new_messages
