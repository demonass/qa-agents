from schemas.state import AgentState
from tools.document_tools import get_lang_instruction
from tools.cache_tools import get_cached_response, set_cached_response
from config.settings import get_llm

def format_messages(messages):
    if not messages:
        return "No previous messages."
    return "\n".join([f"{msg['role']}: {msg['content']}" for msg in messages])

def designer_node(state: AgentState) -> AgentState:
    print(f"\n--- 🤖 [Designer] Writing Test Cases... ---")

    cached = get_cached_response(state.get('intent_type', 'TEST_CASE'), state['user_input'])
    if cached:
        print(f"⚡ Cache hit! Returning cached response")
        return {"output_content": cached, "messages": state.get('messages', [])}

    lang_instruction = get_lang_instruction(state['language'])

    rag_context = ""
    if state.get('use_rag') and state.get('rag_context'):
        rag_context = f"\n\n### Reference Documents (RAG) ###\n{state['rag_context']}\nUse this knowledge to design better test cases."

    prompt = f"""
    You are a senior QA Engineer. Design detailed test cases based on:

    --- Conversation History ---
    {format_messages(state.get('messages', []))}

    ### Requirement ###
    {state['requirement']}

    ### Document Content ###
    {state.get('document_content', 'None')}

    {rag_context}

    {lang_instruction}
    Output structured test cases (ID, Steps, Expected Result).
    """

    llm = get_llm()
    response = llm.invoke(prompt)
    content = response.content

    set_cached_response(state.get('intent_type', 'TEST_CASE'), state['user_input'], content)

    return {"output_content": content, "messages": state.get('messages', [])}
