from schemas.state import AgentState
from langchain_openai import ChatOpenAI
from tools.document_tools import get_lang_instruction

def create_chat_node(llm: ChatOpenAI):
    def chat_node(state: AgentState) -> AgentState:
        print(f"\n--- 💬 [Chatting] ---")
        
        lang_instruction = get_lang_instruction(state['language'])
        
        prompt = f"""
        You are a helpful assistant. User said: "{state['user_input']}"
        {lang_instruction}
        """
        
        response = llm.invoke(prompt)
        return {"output_content": response.content}
    
    return chat_node