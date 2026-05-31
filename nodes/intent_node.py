from schemas.state import AgentState
from config.settings import get_llm

def format_messages(messages):
    if not messages:
        return "No previous messages."
    return "\n".join([f"{msg['role']}: {msg['content']}" for msg in messages])

def intent_node(state: AgentState) -> AgentState:
    print("\n--- 🔍 [Receptionist] Analyzing intent... ---")

    selected_model = state.get('selected_model', '')
    llm = get_llm(model_name=selected_model)

    prompt = f"""Classify the user's intent into one of these categories:
- CHAT: Greetings or casual talk
- TEST_CASE: Write specific test cases/scenarios
- TEST_PLAN: Write test strategy/scope/schedule
- CODE_ANALYSIS: Analyze code or project
- RAG_QA: Questions needing document knowledge (what is..., explain..., how to...)
- RUN_TESTS: Execute tests or analyze results

Examples:
User: "Hello, how are you?" → CHAT
User: "Write test cases for login functionality" → TEST_CASE
User: "Generate a test plan for the API" → TEST_PLAN
User: "Analyze this codebase" → CODE_ANALYSIS
User: "What is the architecture described in the docs?" → RAG_QA
User: "Run pytest on the tests directory" → RUN_TESTS
User: "How do I configure the database?" → RAG_QA

--- Conversation History ---
{format_messages(state.get('messages', []))}

User: "{state['user_input']}"

Output ONLY the category name."""
    
    response = llm.invoke(prompt)
    intent = response.content.strip().upper()
    
    return {"intent_type": intent, "messages": state.get('messages', [])}
