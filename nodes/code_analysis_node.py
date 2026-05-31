from schemas.state import AgentState
from tools.code_analyzer import analyze_project, generate_analysis_report, get_code_summary, is_test_file
from tools.document_tools import get_lang_instruction
from config.settings import get_llm


def ask_project_path_node(state: AgentState) -> AgentState:
    """询问项目路径节点"""
    print("\n--- 📂 [Code Analyzer] Checking project path... ---")
    
    project_path = input("📂 请输入要分析的项目目录路径: ").strip()
    
    return {"requirement": project_path, "messages": state.get('messages', [])}


def code_analysis_node(state: AgentState) -> AgentState:
    """代码分析节点：分析项目代码并调用 AI 进行智能分析"""
    print("\n--- 🔍 [Code Analyzer] Analyzing project code... ---")
    
    project_path = state.get('requirement', '').strip()
    
    if not project_path:
        return {"output_content": "请提供要分析的项目路径", "messages": state.get('messages', [])}
    
    try:
        # 分析项目代码
        analysis_results = analyze_project(project_path)
        
        if not analysis_results:
            return {"output_content": f"在路径 '{project_path}' 中未找到任何支持的代码文件", "messages": state.get('messages', [])}
        
        # 检查是否全是测试文件
        if all(is_test_file(r['file_path']) for r in analysis_results):
            report = generate_analysis_report(analysis_results)
            return {"output_content": "检测到分析的代码全部为测试代码。\n\n代码分析报告：\n\n" + report, "messages": state.get('messages', [])}
        
        # 本地统计（简化版）
        report = generate_analysis_report(analysis_results)
        
        # 获取代码详细摘要供 AI 分析
        code_summary = get_code_summary(analysis_results)

        # 调用 AI 进行智能分析
        llm = get_llm()
        lang_instruction = get_lang_instruction(state['language'])
        
        prompt = f"""
        请分析以下项目代码，输出详细的分析结果：
        
        项目统计信息：
        {report}
        
        代码结构摘要：
        {code_summary}
        
        {lang_instruction}
        
        请输出：
        1. 🎯 项目用途：这个项目是做什么的
        2. 📦 模块结构：项目包含哪些主要模块/包
        3. 🔑 核心功能：项目的核心功能和特点
        """
        
        print("--- 🤖 [Code Analyzer] AI 正在分析代码... ---")
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