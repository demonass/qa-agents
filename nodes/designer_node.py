from schemas.state import AgentState
from langchain_openai import ChatOpenAI
from tools.document_tools import get_lang_instruction

def create_designer_node(llm: ChatOpenAI):
    def designer_node(state: AgentState) -> AgentState:
        print(f"\n--- 🤖 [Designer] Writing Test Cases... ---")
        
        lang_instruction = get_lang_instruction(state['language'])
        
        prompt = f"""
        You are a senior QA Engineer. Design detailed test cases based on:
        
        ### Requirement ###
        {state['requirement']}
        
        ### Document Content ###
        {state.get('document_content', 'None')}
        
        {lang_instruction}
        Output structured test cases (ID, Steps, Expected Result).
        """
        
        response = llm.invoke(prompt)
        return {"output_content": response.content}
    
    return designer_node