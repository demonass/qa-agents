from langchain_openai import ChatOpenAI

# Optional MCP import - only load when needed
try:
    from langchain_mcp import MCP
    MCP_AVAILABLE = True
except ImportError:
    MCP = None
    MCP_AVAILABLE = False

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

def get_mcp():
    """Get MCP client for connecting to MCP servers."""
    if not MCP_AVAILABLE:
        raise ImportError("langchain_mcp is not installed. Please install it with: pip install langchain-mcp")
    return MCP(LLMConfig.MCP_SERVICE)

def get_llm_from_mcp(mcp, model_name: str = None) -> ChatOpenAI:
    """Get LLM from MCP server."""
    return mcp.llm(model_name or LLMConfig.MODEL_NAME)
