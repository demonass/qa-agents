from schemas.state import AgentState
from tools.code_analyzer import analyze_project, generate_analysis_report
from tools.document_tools import get_lang_instruction
from config.settings import get_llm


def format_messages(messages):
    if not messages:
        return "No previous messages."
    return "\n".join([f"{msg['role']}: {msg['content']}" for msg in messages])


def ask_project_path_node(state: AgentState) -> AgentState:
    """询问项目路径节点"""
    print("\n--- 📂 [Code Analyzer] Checking project path... ---")
    
    project_path = input("📂 请输入要分析的项目目录路径: ").strip()
    
    return {"requirement": project_path, "messages": state.get('messages', [])}


def code_analysis_node(state: AgentState) -> AgentState:
    """代码分析节点：分析项目代码并生成测试计划"""
    print("\n--- 🔍 [Code Analyzer] Analyzing project code... ---")
    
    project_path = state.get('requirement', '').strip()
    
    if not project_path:
        return {"output_content": "请提供要分析的项目路径", "messages": state.get('messages', [])}
    
    try:
        # 分析项目代码
        analysis_results = analyze_project(project_path)
        
        if not analysis_results:
            return {"output_content": f"在路径 '{project_path}' 中未找到任何 Python 文件", "messages": state.get('messages', [])}
        
        # 生成分析报告
        report = generate_analysis_report(analysis_results)
        
        # 调用 LLM 生成测试计划
        llm = get_llm()
        lang_instruction = get_lang_instruction(state['language'])
        
        # RAG 上下文
        rag_context = ""
        if state.get('use_rag') and state.get('rag_context'):
            rag_context = f"\n\n### Reference Documents (RAG) ###\n{state['rag_context']}\nUse this knowledge to enhance test case design."
        
        prompt = f"""
        基于以下代码分析结果，为该项目生成详细的测试计划和测试用例：
        
        --- Conversation History ---
        {format_messages(state.get('messages', []))}
        
        {report}
        
        {rag_context}
        
        {lang_instruction}
        
        请输出：
        1. 测试范围和策略
        2. 关键模块测试要点
        3. 推荐的测试用例（按模块分组）
        4. 测试覆盖建议
        """
        
        print("--- 📝 [Code Analyzer] Generating test plan... ---")
        response = llm.invoke(prompt)
        
        return {
            "code_analysis": report,
            "output_content": response.content,
            "messages": state.get('messages', [])
        }
    
    except Exception as e:
        error_msg = f"代码分析失败: {str(e)}"
        print(f"❌ Error: {error_msg}")
        return {"output_content": error_msg, "messages": state.get('messages', [])}