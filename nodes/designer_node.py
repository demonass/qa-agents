from schemas.state import AgentState
from tools.document_tools import get_lang_instruction
from config.settings import get_llm

def designer_node(state: AgentState) -> AgentState:
    print(f"\n--- 🤖 [Designer] Writing Test Cases... ---")
    
    llm = get_llm()
    lang_instruction = get_lang_instruction(state['language'])
    
    # RAG 上下文
    rag_context = ""
    if state.get('use_rag') and state.get('rag_context'):
        rag_context = f"\n\n### Reference Documents (RAG) ###\n{state['rag_context']}\nUse this knowledge to design better test cases."
    
    prompt = f"""
    You are a senior QA Engineer. Design detailed test cases based on:
    
    ### Requirement ###
    {state['requirement']}
    
    ### Document Content ###
    {state.get('document_content', 'None')}
    
    {rag_context}
    
    {lang_instruction}
    Output structured test cases (ID, Steps, Expected Result).
    """
    
    response = llm.invoke(prompt)
    return {"output_content": response.content}
