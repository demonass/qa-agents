from schemas.state import AgentState
from tools.document_tools import get_lang_instruction
from config.settings import get_llm

def chat_node(state: AgentState) -> AgentState:
    print(f"\n--- 💬 [Chatting] ---")
    
    llm = get_llm()
    lang_instruction = get_lang_instruction(state['language'])
    
    prompt = f"""
    You are a helpful assistant. User said: "{state['user_input']}"
    {lang_instruction}
    """
    
    response = llm.invoke(prompt)
    return {"output_content": response.content}
