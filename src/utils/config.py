"""
配置管理模块
- API key 從 .env 讀（環境變數）
- 其他設定從 config.py 讀（若存在），否則用 dataclass 預設值
"""

import os
from dataclasses import dataclass
from typing import Optional

from dotenv import load_dotenv


@dataclass
class Config:
    """配置类"""
    # API密钥（來源：.env / 環境變數）
    openai_api_key: Optional[str] = None
    tavily_api_key: Optional[str] = None

    # 模型配置
    default_llm_provider: str = "openai"
    openai_model: str = "gpt-4o-mini"

    # 搜索配置
    max_search_results: int = 3
    search_timeout: int = 240
    max_content_length: int = 20000

    # Agent配置
    max_reflections: int = 2
    max_paragraphs: int = 5

    # 输出配置
    output_dir: str = "reports"
    save_intermediate_states: bool = True

    def validate(self) -> bool:
        """验证配置"""
        if self.default_llm_provider == "openai" and not self.openai_api_key:
            print("错误: OPENAI_API_KEY 未设置（請填入 .env）")
            return False

        if not self.tavily_api_key:
            print("错误: TAVILY_API_KEY 未设置（請填入 .env）")
            return False

        return True


def _load_settings_from_py(path: str) -> dict:
    """從 config.py 動態載入非機密設定。檔案不存在時回傳 {}。"""
    if not os.path.exists(path):
        return {}

    import importlib.util

    spec = importlib.util.spec_from_file_location("config", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    setting_keys = [
        "DEFAULT_LLM_PROVIDER",
        "OPENAI_MODEL",
        "SEARCH_RESULTS_PER_QUERY",
        "SEARCH_TIMEOUT",
        "SEARCH_CONTENT_MAX_LENGTH",
        "MAX_REFLECTIONS",
        "MAX_PARAGRAPHS",
        "OUTPUT_DIR",
        "SAVE_INTERMEDIATE_STATES",
    ]
    return {k: getattr(module, k) for k in setting_keys if hasattr(module, k)}


def load_config(config_file: Optional[str] = None) -> Config:
    """
    加载配置

    - API key：從 .env / 環境變數讀取
    - 其他設定：從 config.py 讀取（若存在），否則使用 Config dataclass 的預設值

    Args:
        config_file: 設定檔路徑（.py），若不指定則讀取 cwd 的 config.py

    Returns:
        配置对象
    """
    # 1. 載入 .env 到環境變數（檔案不存在會靜默跳過）
    load_dotenv()

    # 2. 載入 config.py 內的非機密設定
    settings_path = config_file or "config.py"
    settings = _load_settings_from_py(settings_path)

    # 3. 組裝 Config（key 來自環境變數，設定來自 config.py / 預設值）
    config = Config(
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        tavily_api_key=os.getenv("TAVILY_API_KEY"),
        default_llm_provider=settings.get("DEFAULT_LLM_PROVIDER", "openai"),
        openai_model=settings.get("OPENAI_MODEL", "gpt-4o-mini"),
        max_search_results=settings.get("SEARCH_RESULTS_PER_QUERY", 3),
        search_timeout=settings.get("SEARCH_TIMEOUT", 240),
        max_content_length=settings.get("SEARCH_CONTENT_MAX_LENGTH", 20000),
        max_reflections=settings.get("MAX_REFLECTIONS", 2),
        max_paragraphs=settings.get("MAX_PARAGRAPHS", 5),
        output_dir=settings.get("OUTPUT_DIR", "reports"),
        save_intermediate_states=settings.get("SAVE_INTERMEDIATE_STATES", True),
    )

    if not config.validate():
        raise ValueError("配置验证失败，请检查 .env 中的 API 密钥")

    return config


def print_config(config: Config):
    """打印配置信息（隐藏敏感信息）"""
    print("\n=== 当前配置 ===")
    print(f"LLM提供商: {config.default_llm_provider}")
    print(f"OpenAI模型: {config.openai_model}")
    print(f"最大搜索结果数: {config.max_search_results}")
    print(f"搜索超时: {config.search_timeout}秒")
    print(f"最大内容长度: {config.max_content_length}")
    print(f"最大反思次数: {config.max_reflections}")
    print(f"最大段落数: {config.max_paragraphs}")
    print(f"输出目录: {config.output_dir}")
    print(f"保存中间状态: {config.save_intermediate_states}")

    # 显示API密钥状态（不显示实际密钥）
    print(f"OpenAI API Key: {'已设置' if config.openai_api_key else '未设置'}")
    print(f"Tavily API Key: {'已设置' if config.tavily_api_key else '未设置'}")
    print("==================\n")
