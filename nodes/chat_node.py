from schemas.state import AgentState
from tools.document_tools import get_lang_instruction
from tools.cache_tools import get_cached_response, set_cached_response
from config.settings import get_llm

def format_messages(messages):
    if not messages:
        return "No previous messages."
    return "\n".join([f"{msg['role']}: {msg['content']}" for msg in messages])

def chat_node(state: AgentState) -> AgentState:
    print(f"\n--- 💬 [Chatting] ---")

    selected_model = state.get('selected_model', '')
    lang_instruction = get_lang_instruction(state['language'])

    cache_key = f"{state.get('intent_type', 'CHAT')}:{state['user_input']}"
    cached = get_cached_response(state.get('intent_type', 'CHAT'), state['user_input'], selected_model)
    if cached:
        print(f"⚡ Cache hit! Returning cached response")
        return {"output_content": cached, "messages": state.get('messages', [])}

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

    llm = get_llm(model_name=selected_model)
    response = llm.invoke(prompt)
    content = response.content

    set_cached_response(state.get('intent_type', 'CHAT'), state['user_input'], content, selected_model)

    return {"output_content": content, "messages": state.get('messages', [])}
