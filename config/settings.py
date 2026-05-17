from langchain_openai import ChatOpenAI
import os
from typing import Dict, Optional

class LLMConfig:
    # ==================== 模式配置 ====================
    # MODE: "single" - 单模型模式（原有模式）
    #       "kong"   - Kong 网关多模型模式
    MODE = "single"  # 默认使用单模型模式
    
    # ==================== 单模型模式配置 ====================
    # 直接连接到单个 LLM 服务（如 Ollama、vLLM 等）
    BASE_URL = "http://localhost:8080/v1"
    API_KEY = "sk-no-key-required"
    MODEL_NAME = "qwen"
    TEMPERATURE = 0.7
    
    # ==================== Kong 网关模式配置 ====================
    # 通过 Kong API Gateway 路由到多个模型
    KONG_BASE_URL = "http://localhost:8000/v1"  # Kong 网关地址
    KONG_API_KEY = "your-kong-api-key"          # Kong API 密钥
    
    # Kong 模式下支持的模型列表
    # 格式: {"模型标识": {"model_name": "实际模型名", "description": "描述"}}
    KONG_MODELS: Dict[str, Dict[str, str]] = {
        "qwen": {
            "model_name": "qwen",
            "description": "Qwen 大语言模型"
        },
        "llama3": {
            "model_name": "llama3",
            "description": "Meta Llama 3 模型"
        },
        "mistral": {
            "model_name": "mistral",
            "description": "Mistral AI 模型"
        },
        "gemma": {
            "model_name": "gemma",
            "description": "Google Gemma 模型"
        }
    }
    # Kong 模式下的默认模型
    KONG_DEFAULT_MODEL = "qwen"


def get_llm(model_name: Optional[str] = None) -> ChatOpenAI:
    """
    获取 LLM 实例
    
    Args:
        model_name: 指定模型名称（仅在 Kong 模式下生效）
    
    Returns:
        ChatOpenAI 实例
    """
    if LLMConfig.MODE == "kong":
        # Kong 网关模式
        url = LLMConfig.KONG_BASE_URL
        api_key = LLMConfig.KONG_API_KEY
        # 使用指定的模型或默认模型
        selected_model = model_name or LLMConfig.KONG_DEFAULT_MODEL
        # 从配置中获取实际的模型名称
        model_info = LLMConfig.KONG_MODELS.get(selected_model)
        final_model_name = model_info["model_name"] if model_info else selected_model
    else:
        # 单模型模式（原有逻辑）
        url = LLMConfig.BASE_URL
        api_key = LLMConfig.API_KEY
        final_model_name = LLMConfig.MODEL_NAME
    
    return ChatOpenAI(
        base_url=url,
        api_key=api_key,
        model=final_model_name,
        temperature=LLMConfig.TEMPERATURE
    )


def get_kong_models() -> Dict[str, Dict[str, str]]:
    """
    获取 Kong 模式下支持的模型列表
    
    Returns:
        模型字典，key 为模型标识，value 包含 model_name 和 description
    """
    return LLMConfig.KONG_MODELS


def is_kong_mode() -> bool:
    """
    判断当前是否为 Kong 模式
    
    Returns:
        True 表示 Kong 模式，False 表示单模型模式
    """
    return LLMConfig.MODE == "kong"