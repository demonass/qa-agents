from langchain_openai import ChatOpenAI
import os

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
    # 保存原始环境变量
    original_http_proxy = os.environ.get('HTTP_PROXY')
    original_https_proxy = os.environ.get('HTTPS_PROXY')
    original_all_proxy = os.environ.get('ALL_PROXY')
    
    # 临时移除代理环境变量，避免 socks 代理问题
    os.environ.pop('HTTP_PROXY', None)
    os.environ.pop('HTTPS_PROXY', None)
    os.environ.pop('ALL_PROXY', None)
    
    try:
        llm = ChatOpenAI(
            base_url=LLMConfig.BASE_URL,
            api_key=LLMConfig.API_KEY,
            model=LLMConfig.MODEL_NAME,
            temperature=LLMConfig.TEMPERATURE
        )
    finally:
        # 恢复原始环境变量
        if original_http_proxy is not None:
            os.environ['HTTP_PROXY'] = original_http_proxy
        if original_https_proxy is not None:
            os.environ['HTTPS_PROXY'] = original_https_proxy
        if original_all_proxy is not None:
            os.environ['ALL_PROXY'] = original_all_proxy
    
    return llm

def get_mcp():
    """Get MCP client for connecting to MCP servers."""
    if not MCP_AVAILABLE:
        raise ImportError("langchain_mcp is not installed. Please install it with: pip install langchain-mcp")
    return MCP(LLMConfig.MCP_SERVICE)

def get_llm_from_mcp(mcp, model_name: str = None) -> ChatOpenAI:
    """Get LLM from MCP server."""
    return mcp.llm(model_name or LLMConfig.MODEL_NAME)
