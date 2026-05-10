import os
import uuid
import argparse
import readline  # 添加 readline 支持，修复 backspace 删除问题

# 在导入任何模块之前移除代理环境变量，避免 socks 代理问题
os.environ.pop('HTTP_PROXY', None)
os.environ.pop('HTTPS_PROXY', None)
os.environ.pop('ALL_PROXY', None)
os.environ.pop('http_proxy', None)
os.environ.pop('https_proxy', None)
os.environ.pop('all_proxy', None)

from langgraph.graph import StateGraph, END, START
from langgraph.checkpoint.sqlite import SqliteSaver

from schemas.state import AgentState
from nodes.intent_node import create_intent_node
from nodes.chat_node import create_chat_node
from nodes.planner_node import create_planner_node
from nodes.designer_node import create_designer_node
from tools.document_tools import load_document
from tools.file_tools import save_test_plan
from config.settings import get_llm, get_mcp, get_llm_from_mcp, LLMConfig, MCP_AVAILABLE


def ask_template_node(state: AgentState) -> AgentState:
    print(f"\n--- 📂 [Planner] Checking for templates... ---")
    return {"template_path": "", "template_content": ""}


def route_intent(state: AgentState) -> str:
    if state['intent_type'] == 'CHAT':
        return "chat_node"
    elif state['intent_type'] == 'TEST_PLAN':
        return "ask_template_node"
    else:
        return "designer_node"


def create_qa_agent(llm):
    builder = StateGraph(AgentState)
    
    builder.add_node("intent_node", create_intent_node(llm))
    builder.add_node("chat_node", create_chat_node(llm))
    builder.add_node("ask_template_node", ask_template_node)
    builder.add_node("planner_node", create_planner_node(llm))
    builder.add_node("designer_node", create_designer_node(llm))
    
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
    
    return builder


def main():
    parser = argparse.ArgumentParser(description="Smart QA Agent - Test Plan and Test Case Generator")
    parser.add_argument("--mcp", action="store_true", help="Use MCP (Model Context Protocol) instead of direct API")
    parser.add_argument("--mcp-server", type=str, default=LLMConfig.MCP_SERVICE, 
                        help=f"MCP server address (default: {LLMConfig.MCP_SERVICE})")
    parser.add_argument("--model", type=str, default=LLMConfig.MODEL_NAME,
                        help=f"Model name (default: {LLMConfig.MODEL_NAME})")
    args = parser.parse_args()
    
    print("=" * 60)
    print("👋 Welcome to Smart QA Agent")
    print("=" * 60)
    
    # Initialize LLM based on MCP or direct API
    if args.mcp:
        if not MCP_AVAILABLE:
            print(f"❌ langchain_mcp is not installed")
            print(f"   Please install it with: pip install langchain-mcp")
            print(f"� Falling back to direct API")
            llm = get_llm()
        else:
            print(f"�� Using MCP server: {args.mcp_server}")
            try:
                mcp = get_mcp()
                llm = get_llm_from_mcp(mcp, args.model)
                print(f"✅ Connected to MCP server successfully")
            except Exception as e:
                print(f"❌ Failed to connect to MCP server: {e}")
                print(f"🔄 Falling back to direct API")
                llm = get_llm()
    else:
        print(f"🔌 Using direct API: {LLMConfig.BASE_URL}")
        llm = get_llm()
    
    selected_lang = "中文"
    lang_choice = input("\nLanguage (1.中文 / 2.English) [Enter for Chinese]: ").strip()
    if lang_choice == "2":
        selected_lang = "English"
    
    builder = create_qa_agent(llm)
    
    with SqliteSaver.from_conn_string("memory.db") as memory:
        app = builder.compile(checkpointer=memory)
        
        while True:
            try:
                user_input = input(f"\n🔵 [{selected_lang}] 需求: ").strip()
                
                if user_input.lower() in ["quit", "exit", "q"]:
                    break
                if not user_input:
                    continue
                
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
                
                for event in app.stream(initial_state, config, checkpointer=memory):
                    if "ask_template_node" in event:
                        print("\n--- 🛑 PAUSED FOR USER INPUT ---")
                        template_path = input("📂 Do you have a template? (Enter path or press Enter to skip): ").strip()
                        
                        if template_path:
                            print(f"📄 Loading template from: {template_path}")
                            t_content = load_document(template_path)
                            app.update_state(config, {"template_content": t_content})
                        else:
                            print("⏭️ Skipping template.")
                            app.update_state(config, {"template_content": ""})
                
                final_state = app.get_state(config)
                intent = final_state.values['intent_type']
                result_content = final_state.values['output_content']
                
                if intent == 'TEST_PLAN' and result_content:
                    file_path = save_test_plan(result_content, user_input)
                    if not file_path.startswith("Failed"):
                        print(f"\n💾 SUCCESS! Test Plan saved to: {file_path}")
                    else:
                        print(f"\n❌ {file_path}")
                
                if intent == 'CHAT':
                    print(f"\n🤖 Assistant: {result_content}")
                else:
                    print("\n" + "=" * 30)
                    title = "Test Plan" if intent == 'TEST_PLAN' else "Test Cases"
                    print(f"✅ Generated {title}:")
                    print("-" * 30)
                    print(result_content)
                    print("=" * 30)
            
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"\n❌ Error: {e}")


if __name__ == "__main__":
    main()
