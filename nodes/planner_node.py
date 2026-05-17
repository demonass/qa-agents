import os
from schemas.state import AgentState
from tools.document_tools import get_lang_instruction
from config.settings import get_llm

def format_messages(messages):
    if not messages:
        return "No previous messages."
    return "\n".join([f"{msg['role']}: {msg['content']}" for msg in messages])

def planner_node(state: AgentState) -> AgentState:
    print(f"\n--- 📝 [Planner] Drafting Test Plan... ---")
    
    # 获取用户选择的模型（Kong 模式下有效）
    selected_model = state.get('selected_model', '')
    llm = get_llm(model_name=selected_model)
    lang_instruction = get_lang_instruction(state['language'])
    
    template_context = ""
    if state.get('template_content'):
        template_context = f"\n\n### Reference Template Structure ###\n{state['template_content']}\nPlease follow this structure but adapt it to the requirements."
    
    # RAG 上下文
    rag_context = ""
    if state.get('use_rag') and state.get('rag_context'):
        rag_context = f"\n\n### Reference Documents (RAG) ###\n{state['rag_context']}\nUse this knowledge to enhance the test plan."
    
    prompt = f"""
    You are an expert QA Lead. Write a comprehensive Test Plan based on:
    
    --- Conversation History ---
    {format_messages(state.get('messages', []))}
    
    ### Requirement / Context ###
    {state.get('requirement', '')}
    
    ### Document Content ###
    {state.get('document_content', 'None')}
    
    {rag_context}
    
    {template_context}
    
    {lang_instruction}
    The plan should include: Scope, Strategy, Resources, Schedule, and Risks.
    """
    
    response = llm.invoke(prompt)
    return {"output_content": response.content, "messages": state.get('messages', [])}
