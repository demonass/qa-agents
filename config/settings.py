from langchain_openai import ChatOpenAI
import os
from typing import Dict, Optional

class LLMConfig:
    BASE_URL = "http://localhost:8080/v1"
    API_KEY = "sk-no-key-required"
    MODEL_NAME = "qwen"
    TEMPERATURE = 0.7

    # ==================== Redis 缓存配置 ====================
    # LLM 响应缓存开关（默认关闭，需安装 Redis 并设置 True 启用）
    LLM_CACHE_ENABLED = False

    # Redis 连接配置
    REDIS_HOST = "localhost"
    REDIS_PORT = 6379
    REDIS_DB = 0
    REDIS_PASSWORD = None  # 如果有密码请设置

    # 缓存过期时间（秒），默认 7 天
    LLM_CACHE_TTL = 60 * 60 * 24 * 7


def get_llm() -> ChatOpenAI:
    return ChatOpenAI(
        base_url=LLMConfig.BASE_URL,
        api_key=LLMConfig.API_KEY,
        model=LLMConfig.MODEL_NAME,
        temperature=LLMConfig.TEMPERATURE
    )