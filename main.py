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
from config.settings import is_kong_mode, get_kong_models, LLMConfig


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
    
    # 显示当前模式信息
    if is_kong_mode():
        print(f"🔄 当前模式: Kong 多模型网关模式")
        print(f"📡 Kong 网关地址: {LLMConfig.KONG_BASE_URL}")
    else:
        print(f"🔄 当前模式: 单模型模式")
        print(f"📡 LLM 服务地址: {LLMConfig.BASE_URL}")
        print(f"🤖 当前模型: {LLMConfig.MODEL_NAME}")
    
    selected_lang = "中文"
    lang_choice = input("\nLanguage (1.中文 / 2.English) [Enter for Chinese]: ").strip()
    if lang_choice == "2":
        selected_lang = "English"
    
    # Kong 模式下允许选择模型
    selected_model = ""
    if is_kong_mode():
        models = get_kong_models()
        print(f"\n🤖 可用模型 ({len(models)} 个):")
        for i, (model_key, model_info) in enumerate(models.items(), 1):
            print(f"   {i}. {model_key} - {model_info['description']}")
        
        model_choice = input(f"\n请选择模型 (输入序号或模型名，默认 {LLMConfig.KONG_DEFAULT_MODEL}): ").strip()
        if model_choice.isdigit():
            idx = int(model_choice) - 1
            if 0 <= idx < len(models):
                selected_model = list(models.keys())[idx]
        elif model_choice in models:
            selected_model = model_choice
        else:
            selected_model = LLMConfig.KONG_DEFAULT_MODEL
        
        print(f"✅ 已选择模型: {selected_model}")
    
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
                
                # 检查是否需要切换模型（仅 Kong 模式支持）
                if user_input.lower().startswith("/model"):
                    if not is_kong_mode():
                        print("❌ 模型切换仅在 Kong 多模型模式下可用")
                        print("💡 请在 config/settings.py 中设置 MODE = \"kong\" 启用多模型支持")
                        continue
                    
                    parts = user_input.split()
                    if len(parts) < 2:
                        models = get_kong_models()
                        print(f"\n🤖 当前模型: {selected_model or LLMConfig.KONG_DEFAULT_MODEL}")
                        print(f"\n📋 可用模型列表:")
                        for i, (model_key, model_info) in enumerate(models.items(), 1):
                            marker = " ← 当前" if model_key == (selected_model or LLMConfig.KONG_DEFAULT_MODEL) else ""
                            print(f"   {i}. {model_key} - {model_info['description']}{marker}")
                        print(f"\n💡 切换模型: /model <模型名称> 或 /model <序号>")
                        continue
                    
                    model_arg = parts[1]
                    models = get_kong_models()
                    
                    if model_arg.isdigit():
                        idx = int(model_arg) - 1
                        if 0 <= idx < len(models):
                            selected_model = list(models.keys())[idx]
                        else:
                            print(f"❌ 无效序号，有效范围: 1-{len(models)}")
                            continue
                    elif model_arg in models:
                        selected_model = model_arg
                    else:
                        print(f"❌ 未知模型: {model_arg}")
                        print(f"💡 可用模型: {', '.join(models.keys())}")
                        continue
                    
                    print(f"✅ 模型已切换为: {selected_model}")
                    continue
                
                doc_content = ""
                final_requirement = user_input
                
                if (user_input.endswith(".txt") or user_input.endswith(".md") or 
                    user_input.endswith(".docx") or user_input.endswith(".pdf")) and "/" in user_input:
                    doc_content = load_document.invoke({"file_path": user_input})
                    final_requirement = "Analyze this document." if selected_lang == "English" else "分析这份文档。"
                
                # 先获取当前状态中的消息历史
                current_state = app.get_state(config)
                existing_messages = []
                if current_state and current_state.values and 'messages' in current_state.values:
                    existing_messages = current_state.values['messages']
                
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
                    "test_results": "",
                    "messages": existing_messages,
                    "selected_model": selected_model
                }
                
                print("\n🚀 Agent is thinking...")
                
                # 使用持久化配置调用
                final_state = app.invoke(initial_state, config)
                
                # 更新消息历史，添加当前对话轮次
                new_messages = final_state.get('messages', [])
                new_messages.append({"role": "user", "content": user_input})
                new_messages.append({"role": "assistant", "content": final_state.get('output_content', '')})
                
                # 更新 final_state 中的 messages
                final_state['messages'] = new_messages
                
                # 保存更新后的状态
                app.update_state(config, final_state)
                
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
