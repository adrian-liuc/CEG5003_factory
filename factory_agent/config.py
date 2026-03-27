from dotenv import load_dotenv
import os
from pathlib import Path

load_dotenv(Path(__file__).parent.parent / ".env")

# LLM 配置
API_KEY = os.getenv("LLM_API_KEY")
BASE_URL = os.getenv("LLM_BASE_URL")
MODEL_NAME = os.getenv("LLM_MODEL")

# Agent 配置
MAX_CONTEXT_TOKENS = 22000
MAX_HISTORY_KEEP = 4

# InfluxDB 配置
INFLUXDB_URL = os.getenv("INFLUXDB_URL")
INFLUXDB_TOKEN = os.getenv("INFLUXDB_TOKEN")
INFLUXDB_ORG = os.getenv("INFLUXDB_ORG")
INFLUXDB_BUCKET = os.getenv("INFLUXDB_BUCKET")
