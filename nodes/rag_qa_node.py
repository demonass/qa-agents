from schemas.state import AgentState
from tools.rag_tools import rag_retrieve
from tools.document_tools import get_lang_instruction
from config.settings import get_llm


def rag_qa_node(state: AgentState) -> AgentState:
    """RAG 问答节点：检索相关文档并生成答案"""
    print("\n--- 🔍 [RAG] Retrieving relevant documents... ---")
    
    user_query = state.get('user_input', '')
    language = state.get('language', '中文')
    
    # 检索相关文档
    rag_context = rag_retrieve(user_query, k=3)
    
    if not rag_context:
        return {"output_content": "抱歉，暂时无法检索到相关文档。请确保 documents 目录中存在文档文件。"}
    
    print(f"📄 Found relevant context (length: {len(rag_context)} chars)")
    
    # 调用 LLM 生成答案
    llm = get_llm()
    lang_instruction = get_lang_instruction(language)
    
    prompt = f"""
    基于以下检索到的文档内容，回答用户的问题。
    
    检索到的文档：
    {rag_context}
    
    用户问题：{user_query}
    
    {lang_instruction}
    
    请基于文档内容生成准确、完整的回答。如果文档中没有相关信息，请明确说明。
    """
    
    print("--- 🤖 [RAG] Generating answer... ---")
    response = llm.invoke(prompt)
    
    return {
        "rag_context": rag_context,
        "output_content": response.content
    }