import os
import sqlite3
from datetime import datetime

class MemoryService:
    def __init__(self, memory_dir="memory", db_path="memory/memory.db"):
        self.memory_dir = memory_dir
        self.db_path = db_path

        if not os.path.exists(self.memory_dir):
            os.makedirs(self.memory_dir)
            self._ensure_file("bot_profile.md", "# Bot Profile\nStores the core identity and role of the bot.\n")
            self._ensure_file("user_profile.md", "# User Profile\nMaintains collected information and preferences of the user.\n")
            self._ensure_file("important_memory.md", "# Important Memory\nAutomatically preserves critical long-term memories and rules.\n")
            self._ensure_file("history.md", "# Chat History\nLogs the historical context of past conversations.\n")

        self._init_db()
        self._sync_all()

    def _ensure_file(self, filename, initial_content=""):
        path = os.path.join(self.memory_dir, filename)
        if not os.path.exists(path):
            with open(path, "w", encoding="utf-8") as f:
                f.write(initial_content)

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        try:
            c.execute("CREATE VIRTUAL TABLE IF NOT EXISTS memories USING fts5(filename, content);")
        except sqlite3.OperationalError:
            pass
        conn.commit()
        conn.close()

    def _sync_all(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("DELETE FROM memories")
        for filename in os.listdir(self.memory_dir):
            if filename.endswith(".md"):
                path = os.path.join(self.memory_dir, filename)
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        c.execute("INSERT INTO memories (filename, content) VALUES (?, ?)", (filename, f.read()))
                except Exception as e:
                    print(f"Indexing error {filename}: {e}")
        conn.commit()
        conn.close()

    def search(self, query):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        try:
            c.execute("""
                SELECT filename, snippet(memories, 1, '<b>', '</b>', '...', 64)
                FROM memories WHERE memories MATCH ? ORDER BY rank LIMIT 5
            """, (query,))
            results = c.fetchall()
        except sqlite3.OperationalError as e:
            print(f"Search error: {e}")
            return []
        finally:
            conn.close()
        return [{"file": r[0], "snippet": r[1]} for r in results]

    def read_file(self, filename):
        path = os.path.join(self.memory_dir, filename)
        if not os.path.exists(path):
            return f"File {filename} does not exist."
        with open(path, "r", encoding="utf-8") as f:
            return f.read()

    def list_files(self):
        return [f for f in os.listdir(self.memory_dir) if f.endswith(".md")]

    def write_memory(self, filename, content, mode="append"):
        filename = os.path.basename(filename)
        if not filename.endswith(".md"):
            filename += ".md"
        path = os.path.join(self.memory_dir, filename)
        if mode == "overwrite":
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
        else:
            with open(path, "a", encoding="utf-8") as f:
                f.write(f"\n\n## [{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]\n{content}")
        self._sync_all()
        return f"Successfully saved to {filename}"

memory_service = MemoryService()
