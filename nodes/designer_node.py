from schemas.state import AgentState
from tools.document_tools import get_lang_instruction
from config.settings import get_llm

def designer_node(state: AgentState) -> AgentState:
    print(f"\n--- 🤖 [Designer] Writing Test Cases... ---")
    
    llm = get_llm()
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
