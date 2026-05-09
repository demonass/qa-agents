from schemas.state import AgentState
from langchain_openai import ChatOpenAI

def create_intent_node(llm: ChatOpenAI):
    def intent_node(state: AgentState) -> AgentState:
        print("\n--- 🔍 [Receptionist] Analyzing intent... ---")
        
        prompt = f"""
        Analyze the user's input and classify the intent into one of the following categories:
        1. CHAT: Greetings, casual talk, or general questions.
        2. TEST_CASE: Request to write specific test cases, scenarios, or steps.
        3. TEST_PLAN: Request to write a high-level test strategy, scope, approach, or schedule.
        
        User Input: {state['user_input']}
        
        Output ONLY the category name (CHAT, TEST_CASE, or TEST_PLAN).
        """
        
        response = llm.invoke(prompt)
        intent = response.content.strip().upper()
        
        return {"intent_type": intent}
    
    return intent_node