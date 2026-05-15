from schemas.state import AgentState
from tools.rag_tools import rag_retrieve


def rag_retrieve_node(state: AgentState) -> AgentState:
    """统一的 RAG 检索节点：为所有后续节点提供文档上下文"""
    print("\n--- 🔍 [RAG] Retrieving relevant documents... ---")
    
    user_query = state.get('user_input', '')
    
    # 执行 RAG 检索
    context = rag_retrieve(user_query, k=3)
    
    # 判断是否找到相关内容
    has_context = bool(context) and context != "RAG 系统未初始化"
    
    if has_context:
        print(f"📄 Found relevant context (length: {len(context)} chars)")
    else:
        print("📭 No relevant documents found")
    
    return {
        "rag_context": context,
        "use_rag": has_context
    }