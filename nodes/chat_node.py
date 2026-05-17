from schemas.state import AgentState
from tools.document_tools import get_lang_instruction
from config.settings import get_llm

def format_messages(messages):
    if not messages:
        return "No previous messages."
    return "\n".join([f"{msg['role']}: {msg['content']}" for msg in messages])

def chat_node(state: AgentState) -> AgentState:
    print(f"\n--- 💬 [Chatting] ---")
    
    # 获取用户选择的模型（Kong 模式下有效）
    selected_model = state.get('selected_model', '')
    llm = get_llm(model_name=selected_model)
    lang_instruction = get_lang_instruction(state['language'])
    
    # RAG 上下文
    rag_context = ""
    if state.get('use_rag') and state.get('rag_context'):
        rag_context = f"\n\n### Reference Documents (RAG) ###\n{state['rag_context']}\nUse this knowledge to answer the user's question."
    
    prompt = f"""
    You are a helpful assistant.
    
    --- Conversation History ---
    {format_messages(state.get('messages', []))}
    
    Current User Input: "{state['user_input']}"
    
    {rag_context}
    
    {lang_instruction}
    """
    
    response = llm.invoke(prompt)
    return {"output_content": response.content, "messages": state.get('messages', [])}
