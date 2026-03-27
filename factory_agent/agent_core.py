from openai import OpenAI
from memory_service import memory_service
from config import API_KEY, BASE_URL, MODEL_NAME, MAX_CONTEXT_TOKENS, MAX_HISTORY_KEEP

client = OpenAI(api_key=API_KEY, base_url=BASE_URL)

def init_session():
    """加载记忆文件，初始化消息历史"""
    profiles = []
    for filename in ["bot_profile.md", "user_profile.md", "important_memory.md"]:
        content = memory_service.read_file(filename)
        if "does not exist" not in content.lower():
            profiles.append(content)
    system_prompt = "\n\n".join(profiles) if profiles else "You are a smart factory assistant."
    return [{"role": "system", "content": system_prompt}]

def count_tokens(messages):
    """估算 token 数（中文≈1.5，其他≈0.5）"""
    total = 0
    for msg in messages:
        content = msg.get("content", "") or ""
        chinese = sum(1 for c in content if '\u4e00' <= c <= '\u9fff')
        total += int(chinese * 1.5 + (len(content) - chinese) * 0.5)
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
    memory_service.write_memory("important_memory.md", summary, mode="append")

    system_msg = messages[0] if messages and messages[0]["role"] == "system" else None
    recent = messages[-MAX_HISTORY_KEEP:]
    new_messages = ([system_msg] if system_msg else []) + recent
    print(f"[System] Summarized. Kept last {MAX_HISTORY_KEEP} messages.")
    return new_messages
