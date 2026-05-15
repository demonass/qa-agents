from schemas.state import AgentState
from config.settings import get_llm

def format_messages(messages):
    if not messages:
        return "No previous messages."
    return "\n".join([f"{msg['role']}: {msg['content']}" for msg in messages])

def intent_node(state: AgentState) -> AgentState:
    print("\n--- 🔍 [Receptionist] Analyzing intent... ---")
    
    llm = get_llm()
    
    prompt = f"""
    Analyze the user's input and classify the intent into one of the following categories:
    1. CHAT: Greetings, casual talk, or general questions that don't require document knowledge.
    2. TEST_CASE: Request to write specific test cases, scenarios, or steps.
    3. TEST_PLAN: Request to write a high-level test strategy, scope, approach, or schedule.
    4. CODE_ANALYSIS: Request to analyze code, analyze project, or generate tests from code.
    5. RAG_QA: Questions that need knowledge from documents to answer, such as 'what is...', 'explain...', 'how to...'.
    6. RUN_TESTS: Request to run automated tests, execute test suites, analyze test results, or generate test reports.
    
    --- Conversation History ---
    {format_messages(state.get('messages', []))}
    
    Current User Input: {state['user_input']}
    
    Output ONLY the category name (CHAT, TEST_CASE, TEST_PLAN, CODE_ANALYSIS, RAG_QA, or RUN_TESTS).
    """
    
    response = llm.invoke(prompt)
    intent = response.content.strip().upper()
    
    return {"intent_type": intent, "messages": state.get('messages', [])}
