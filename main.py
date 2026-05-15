import os
import uuid
import argparse
import readline

# 在导入任何模块之前移除代理环境变量
os.environ.pop('HTTP_PROXY', None)
os.environ.pop('HTTPS_PROXY', None)
os.environ.pop('ALL_PROXY', None)
os.environ.pop('http_proxy', None)
os.environ.pop('https_proxy', None)
os.environ.pop('all_proxy', None)

from langgraph.graph import StateGraph, END, START
from langgraph.checkpoint.sqlite import SqliteSaver

from schemas.state import AgentState
from nodes.intent_node import intent_node
from nodes.chat_node import chat_node
from nodes.planner_node import planner_node
from nodes.designer_node import designer_node
from nodes.code_analysis_node import code_analysis_node, ask_project_path_node
from nodes.rag_retrieve_node import rag_retrieve_node
from nodes.test_executor_node import test_executor_node, ask_test_path_node
from tools.document_tools import load_document
from tools.file_tools import save_test_plan


def ask_template_node(state: AgentState) -> AgentState:
    print(f"\n--- 📂 [Planner] Checking for templates... ---")
    
    # 在节点内部处理用户输入
    template_path = input("📂 Do you have a template? (Enter path or press Enter to skip): ").strip()
    
    if template_path:
        print(f"📄 Loading template from: {template_path}")
        t_content = load_document.invoke({"file_path": template_path})
        return {"template_path": template_path, "template_content": t_content}
    else:
        print("⏭️ Skipping template.")
        return {"template_path": "", "template_content": ""}


def route_intent(state: AgentState) -> str:
    if state['intent_type'] == 'CHAT' or state['intent_type'] == 'RAG_QA':
        return "chat_node"
    elif state['intent_type'] == 'TEST_PLAN':
        return "ask_template_node"
    elif state['intent_type'] == 'CODE_ANALYSIS':
        return "ask_project_path_node"
    elif state['intent_type'] == 'RUN_TESTS':
        return "ask_test_path_node"
    else:
        return "designer_node"


def create_qa_agent():
    builder = StateGraph(AgentState)
    
    builder.add_node("rag_retrieve_node", rag_retrieve_node)
    builder.add_node("intent_node", intent_node)
    builder.add_node("chat_node", chat_node)
    builder.add_node("ask_template_node", ask_template_node)
    builder.add_node("planner_node", planner_node)
    builder.add_node("designer_node", designer_node)
    builder.add_node("ask_project_path_node", ask_project_path_node)
    builder.add_node("code_analysis_node", code_analysis_node)
    builder.add_node("ask_test_path_node", ask_test_path_node)
    builder.add_node("test_executor_node", test_executor_node)
    
    builder.add_edge(START, "rag_retrieve_node")
    builder.add_edge("rag_retrieve_node", "intent_node")
    builder.add_conditional_edges("intent_node", route_intent, {
        "chat_node": "chat_node",
        "ask_template_node": "ask_template_node",
        "designer_node": "designer_node",
        "ask_project_path_node": "ask_project_path_node",
        "ask_test_path_node": "ask_test_path_node"
    })
    
    builder.add_edge("ask_template_node", "planner_node")
    builder.add_edge("ask_project_path_node", "code_analysis_node")
    builder.add_edge("ask_test_path_node", "test_executor_node")
    builder.add_edge("planner_node", END)
    builder.add_edge("designer_node", END)
    builder.add_edge("chat_node", END)
    builder.add_edge("code_analysis_node", END)
    builder.add_edge("test_executor_node", END)
    
    return builder


def main():
    parser = argparse.ArgumentParser(description="Smart QA Agent - Test Plan and Test Case Generator")
    args = parser.parse_args()
    
    print("=" * 60)
    print("👋 Welcome to Smart QA Agent")
    print("=" * 60)
    
    selected_lang = "中文"
    lang_choice = input("\nLanguage (1.中文 / 2.English) [Enter for Chinese]: ").strip()
    if lang_choice == "2":
        selected_lang = "English"
    
    # 初始化持久化检查点
    with SqliteSaver.from_conn_string("memory.db") as memory:
        builder = create_qa_agent()
        app = builder.compile(checkpointer=memory)
        
        # 创建新对话
        thread_id = str(uuid.uuid4())
        config = {"configurable": {"thread_id": thread_id}}
        print(f"\n📝 New conversation started. Thread ID: {thread_id[:8]}...")
        
        while True:
            try:
                user_input = input(f"\n🔵 [{selected_lang}] 需求: ").strip()
                
                if user_input.lower() in ["quit", "exit", "q"]:
                    break
                if not user_input:
                    continue
                
                # 检查是否需要切换对话
                if user_input.lower().startswith("thread "):
                    parts = user_input.split()
                    if len(parts) >= 2:
                        thread_id = parts[1]
                        config = {"configurable": {"thread_id": thread_id}}
                        print(f"🔄 Switched to thread: {thread_id[:8]}...")
                        continue
                    else:
                        print("❌ Invalid thread command. Usage: thread <thread_id>")
                        continue
                
                doc_content = ""
                final_requirement = user_input
                
                if (user_input.endswith(".txt") or user_input.endswith(".md") or 
                    user_input.endswith(".docx") or user_input.endswith(".pdf")) and "/" in user_input:
                    doc_content = load_document.invoke({"file_path": user_input})
                    final_requirement = "Analyze this document." if selected_lang == "English" else "分析这份文档。"
                
                initial_state = {
                    "user_input": user_input,
                    "language": selected_lang,
                    "intent_type": "",
                    "template_path": "",
                    "template_content": "",
                    "requirement": final_requirement,
                    "document_content": doc_content,
                    "output_content": "",
                    "iteration": 0,
                    "code_analysis": "",
                    "rag_context": "",
                    "use_rag": False,
                    "test_path": "",
                    "test_framework": "pytest",
                    "test_results": ""
                }
                
                print("\n🚀 Agent is thinking...")
                
                # 使用持久化配置调用
                final_state = app.invoke(initial_state, config)
                
                intent = final_state['intent_type']
                result_content = final_state['output_content']
                
                if intent == 'TEST_PLAN' and result_content:
                    file_path = save_test_plan(result_content, user_input)
                    if not file_path.startswith("Failed"):
                        print(f"\n💾 SUCCESS! Test Plan saved to: {file_path}")
                    else:
                        print(f"\n❌ {file_path}")
                
                if intent == 'CHAT' or intent == 'RAG_QA':
                    print(f"\n🤖 Assistant: {result_content}")
                elif intent == 'RUN_TESTS':
                    print("\n" + "=" * 30)
                    print("🧪 Test Execution Report:")
                    print("-" * 30)
                    print(result_content)
                    print("=" * 30)
                else:
                    print("\n" + "=" * 30)
                    title = "Test Plan" if intent == 'TEST_PLAN' else "Test Cases"
                    print(f"✅ Generated {title}:")
                    print("-" * 30)
                    print(result_content)
                    print("=" * 30)
            
            except KeyboardInterrupt:
                break


if __name__ == "__main__":
    main()
