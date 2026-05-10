import os
from schemas.state import AgentState
from tools.document_tools import get_lang_instruction
from config.settings import get_llm

def planner_node(state: AgentState) -> AgentState:
    print(f"\n--- 📝 [Planner] Drafting Test Plan... ---")
    
    llm = get_llm()
    lang_instruction = get_lang_instruction(state['language'])
    
    template_context = ""
    if state.get('template_content'):
        template_context = f"\n\n### Reference Template Structure ###\n{state['template_content']}\nPlease follow this structure but adapt it to the requirements."
    
    prompt = f"""
    You are an expert QA Lead. Write a comprehensive Test Plan based on:
    
    ### Requirement / Context ###
    {state.get('requirement', '')}
    
    ### Document Content ###
    {state.get('document_content', 'None')}
    
    {template_context}
    
    {lang_instruction}
    The plan should include: Scope, Strategy, Resources, Schedule, and Risks.
    """
    
    response = llm.invoke(prompt)
    return {"output_content": response.content}
