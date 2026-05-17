from schemas.state import AgentState
from tools.test_executor import run_tests, analyze_test_results
from tools.document_tools import get_lang_instruction
from config.settings import get_llm


def format_messages(messages):
    if not messages:
        return "No previous messages."
    return "\n".join([f"{msg['role']}: {msg['content']}" for msg in messages])


def test_executor_node(state: AgentState) -> AgentState:
    """测试执行节点：运行测试并分析结果"""
    print("\n--- 🧪 [Test Executor] Running tests... ---")
    
    # 获取用户选择的模型（Kong 模式下有效）
    selected_model = state.get('selected_model', '')
    llm = get_llm(model_name=selected_model)
    lang_instruction = get_lang_instruction(state['language'])
    
    # 获取测试路径
    test_path = state.get('test_path', '')
    if not test_path:
        return {"output_content": "请提供测试文件或目录路径。", "messages": state.get('messages', [])}
    
    # 获取测试框架（默认为 pytest）
    test_framework = state.get('test_framework', 'pytest')
    
    print(f"📁 Test path: {test_path}")
    print(f"🔧 Framework: {test_framework}")
    
    # 运行测试
    try:
        results_json = run_tests.invoke({"test_path": test_path, "test_framework": test_framework})
        
        # 分析测试结果
        analysis = analyze_test_results.invoke({"results_json": results_json})
        
        # 使用LLM生成更详细的总结报告
        summary_prompt = f"""
        You are a QA Test Analyst. Summarize the following test results in {state['language']}:
        
        --- Conversation History ---
        {format_messages(state.get('messages', []))}
        
        {analysis}
        
        {lang_instruction}
        
        Provide a clear, professional summary including:
        1. Overall test status
        2. Key metrics
        3. Recommendations for fixing failures
        """
        
        summary = llm.invoke(summary_prompt)
        
        return {
            "output_content": summary.content,
            "test_results": results_json,
            "messages": state.get('messages', [])
        }
    
    except Exception as e:
        return {"output_content": f"测试执行失败: {str(e)}", "messages": state.get('messages', [])}


def ask_test_path_node(state: AgentState) -> AgentState:
    """询问测试路径节点"""
    print("\n--- 📂 [Test Executor] Asking for test path... ---")
    test_path = input("📁 请输入测试文件或目录的路径: ").strip()
    return {"test_path": test_path, "messages": state.get('messages', [])}
