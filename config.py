# Deep Search Agent 設定（非機密）
# API key 請放 .env（範本見 .env.example）

# LLM 提供商
DEFAULT_LLM_PROVIDER = "openai"
OPENAI_MODEL = "gpt-5.4-mini-2026-03-17"

# Agent / Search 參數
MAX_REFLECTIONS = 2
SEARCH_RESULTS_PER_QUERY = 3
SEARCH_CONTENT_MAX_LENGTH = 20000

# 輸出
OUTPUT_DIR = "reports"
SAVE_INTERMEDIATE_STATES = True
