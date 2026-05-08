import sqlite3
import sys
import uuid
import os
from datetime import datetime
from typing import TypedDict
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END, START
from langgraph.checkpoint.sqlite import SqliteSaver

# ==========================================
# 1. Define State Schema
# ==========================================
class AgentState(TypedDict):
    user_input: str
    language: str
    intent_type: str          # 'chat', 'test_case', 'test_plan'
    template_path: str        # User provided template path
    template_content: str     # Content read from the template file
    requirement: str
    document_content: str
    output_content: str       # Final generated result (Plan or Case)
    iteration: int

# ==========================================
# 2. Initialize Model
# ==========================================
llm = ChatOpenAI(
    base_url="http://localhost:8080/v1",
    api_key="sk-no-key-required",
    model="qwen",
    temperature=0.7
)

# ==========================================
# 3. Helper Functions
# ==========================================
def load_document(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        return f"Failed to read file: {e}"

def get_lang_instruction(lang):
    if "中文" in lang:
        return "You must always respond in Simplified Chinese."
    else:
        return "You must always respond in English."

# ==========================================
# 4. Define Node Logic
# ==========================================

def intent_node(state: AgentState):
    """Intent Recognition: Distinguish between chat, test cases, and test plans"""
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

def chat_node(state: AgentState):
    """Chat Node"""
    print(f"\n--- 💬 [Chatting] ---")
    prompt = f"""
    You are a helpful assistant. User said: "{state['user_input']}"
    {get_lang_instruction(state['language'])}
    """
    response = llm.invoke(prompt)
    return {"output_content": response.content}

def ask_template_node(state: AgentState):
    """
    This is a special node. It doesn't call LLM to generate results directly,
    but prepares data to let the main program know it should stop and ask the user for a file path.
    """
    print(f"\n--- 📂 [Planner] Checking for templates... ---")
    return {} 

def planner_node(state: AgentState):
    """Core node for writing Test Plans"""
    print(f"\n--- 📝 [Planner] Drafting Test Plan... ---")
    
    lang_instruction = get_lang_instruction(state['language'])
    
    # If there is a template, use it as reference
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

def designer_node(state: AgentState):
    """Core node for writing Test Cases"""
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

# ==========================================
# 5. Build Graph Logic
# ==========================================
def route_intent(state: AgentState):
    if state['intent_type'] == 'CHAT':
        return "chat_node"
    elif state['intent_type'] == 'TEST_PLAN':
        return "ask_template_node" # Ask for template before writing plan
    else: # TEST_CASE
        return "designer_node"

builder = StateGraph(AgentState)
builder.add_node("intent_node", intent_node)
builder.add_node("chat_node", chat_node)
builder.add_node("ask_template_node", ask_template_node)
builder.add_node("planner_node", planner_node)
builder.add_node("designer_node", designer_node)

builder.add_edge(START, "intent_node")
builder.add_conditional_edges("intent_node", route_intent, {
    "chat_node": "chat_node", 
    "ask_template_node": "ask_template_node", 
    "designer_node": "designer_node"
})

builder.add_edge("ask_template_node", "planner_node")
builder.add_edge("planner_node", END)
builder.add_edge("designer_node", END)
builder.add_edge("chat_node", END)

# ==========================================
# 6. Main Interaction Loop
# ==========================================
print("="*50)
print("👋 Welcome to Smart QA Agent")
print("="*50)

# Language Selection
selected_lang = "中文"
lang_choice = input("\nLanguage (1.中文 / 2.English) [Enter for Chinese]: ").strip()
if lang_choice == "2": selected_lang = "English"

with SqliteSaver.from_conn_string("memory.db") as memory:
    
    app = builder.compile(checkpointer=memory)
    
    while True:
        try:
            # Changed prompt from 'User' to '需求' (Requirement)
            user_input = input(f"\n🔵 [{selected_lang}] 需求: ").strip()
            
            if user_input.lower() in ["quit", "exit", "q"]:
                break
            if not user_input: continue

            # Preprocess file path (Requirement Document)
            doc_content = ""
            final_requirement = user_input
            
            if (user_input.endswith(".txt") or user_input.endswith(".md")) and "/" in user_input:
                doc_content = load_document(user_input)
                final_requirement = "Analyze this document." if selected_lang == "English" else "分析这份文档。"

            thread_id = str(uuid.uuid4())
            config = {"configurable": {"thread_id": thread_id}}
            
            initial_state = {
                "user_input": user_input,
                "language": selected_lang,
                "intent_type": "",
                "template_path": "",
                "template_content": "",
                "requirement": final_requirement,
                "document_content": doc_content,
                "output_content": "",
                "iteration": 0
            }

            print("\n🚀 Agent is thinking...")
            
            # Stream execution
            for event in app.stream(initial_state, config, checkpointer=memory):
                # Check if entered ask_template_node
                if "ask_template_node" in event:
                    # --- Key Interaction Logic ---
                    print("\n--- 🛑 PAUSED FOR USER INPUT ---")
                    template_path = input("📂 Do you have a template? (Enter path or press Enter to skip): ").strip()
                    
                    if template_path:
                        print(f"📄 Loading template from: {template_path}")
                        t_content = load_document(template_path)
                        # Update state, pass template content down
                        app.update_state(config, {"template_content": t_content})
                    else:
                        print("⏭️ Skipping template.")
                        app.update_state(config, {"template_content": ""})
                    # ------------------

            # Get final result
            final_state = app.get_state(config)
            
            # ==========================================
            # ✨ Auto-save Logic Start
            # ==========================================
            intent = final_state.values['intent_type']
            result_content = final_state.values['output_content']

            # Only save file if intent is TEST_PLAN and there is content
            if intent == 'TEST_PLAN' and result_content:
                # 1. Generate safe filename
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                # Extract first few chars of user input as filename (remove special chars)
                safe_name = "".join([c for c in user_input[:10] if c.isalnum() or c in ['_', '-']])
                if not safe_name: safe_name = "TestPlan"
                
                filename = f"{safe_name}_{timestamp}.md"
                
                # 2. Write to file
                try:
                    with open(filename, 'w', encoding='utf-8') as f:
                        f.write(result_content)
                    print(f"\n💾 SUCCESS! Test Plan saved to: {os.path.abspath(filename)}")
                except Exception as e:
                    print(f"\n❌ Failed to save file: {e}")
            # ==========================================
            # ✨ Auto-save Logic End
            # ==========================================
            
            # Print screen output
            if intent == 'CHAT':
                print(f"\n🤖 Assistant: {result_content}")
            else:
                print("\n" + "="*30)
                title = "Test Plan" if intent == 'TEST_PLAN' else "Test Cases"
                print(f"✅ Generated {title}:")
                print("-" * 30)
                print(result_content)
                print("="*30)

        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")
