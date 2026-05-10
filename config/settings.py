from langchain_openai import ChatOpenAI
from langchain_mcp import MCP

class LLMConfig:
    # Traditional OpenAI-compatible API config
    BASE_URL = "http://localhost:8080/v1"
    API_KEY = "sk-no-key-required"
    MODEL_NAME = "qwen"
    TEMPERATURE = 0.7
    
    # MCP (Model Context Protocol) config
    USE_MCP = False
    MCP_SERVICE = "localhost:8899"  # Default MCP server address

def get_llm() -> ChatOpenAI:
    return ChatOpenAI(
        base_url=LLMConfig.BASE_URL,
        api_key=LLMConfig.API_KEY,
        model=LLMConfig.MODEL_NAME,
        temperature=LLMConfig.TEMPERATURE
    )

def get_mcp() -> MCP:
    """Get MCP client for connecting to MCP servers."""
    return MCP(LLMConfig.MCP_SERVICE)

def get_llm_from_mcp(mcp: MCP, model_name: str = None) -> ChatOpenAI:
    """Get LLM from MCP server."""
    return mcp.llm(model_name or LLMConfig.MODEL_NAME)
