from langchain_openai import ChatOpenAI
import os

class LLMConfig:
    BASE_URL = "http://localhost:8080/v1"
    API_KEY = "sk-no-key-required"
    MODEL_NAME = "qwen"
    TEMPERATURE = 0.7

def get_llm() -> ChatOpenAI:
    return ChatOpenAI(
        base_url=LLMConfig.BASE_URL,
        api_key=LLMConfig.API_KEY,
        model=LLMConfig.MODEL_NAME,
        temperature=LLMConfig.TEMPERATURE
    )
