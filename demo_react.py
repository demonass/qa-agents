#!/usr/bin/env python3
"""
ReAct Agent 演示脚本

演示新的 ReAct + Skills 架构的使用方式。
"""
import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def print_header(text: str):
    """打印标题"""
    print(f"\n{'='*60}")
    print(f" {text}")
    print('='*60)


def print_skill_info():
    """打印技能信息"""
    print_header("可用 Skills")
    
    from agents.skill_router import DEFAULT_QA_SKILLS
    
    for i, skill in enumerate(DEFAULT_QA_SKILLS, 1):
        print(f"\n{i}. {skill.name}")
        print(f"   描述: {skill.description}")
        if skill.examples:
            print(f"   示例: {', '.join(skill.examples[:3])}...")


def print_tools_info():
    """打印工具信息"""
    print_header("可用 Tools")
    
    from agents import tool_manager
    
    tools = tool_manager.list_all()
    for i, tool in enumerate(tools, 1):
        print(f"\n{i}. {tool.name}")
        print(f"   描述: {tool.description}")


def demo_skill_router():
    """演示技能路由"""
    print_header("Skill Router 演示")
    
    from agents import skill_router
    
    test_queries = [
        "帮我生成一个测试计划",
        "设计登录功能的测试用例",
        "分析一下这个项目的代码结构",
        "RAG 是什么？"
    ]
    
    for query in test_queries:
        print(f"\n查询: {query}")
        results = skill_router.route(query, top_k=2)
        for skill, score in results:
            print(f"  → {skill.name} (score: {score:.3f})")


def demo_react_chat():
    """演示 ReAct 对话"""
    print_header("ReAct Agent 对话演示")
    
    from agents import create_agent, tool_manager, skill_router
    from tools.file_tools import save_test_plan
    from tools.code_analyzer import analyze_project
    
    # 注册工具
    tool_manager.register_function(
        name="save_test_plan",
        description="保存测试计划到文件",
        func=save_test_plan,
        category="test_planning"
    )
    
    tool_manager.register_function(
        name="analyze_project",
        description="分析项目代码结构",
        func=analyze_project,
        category="code_analysis"
    )
    
    # 创建 Agent
    agent = create_agent(
        tool_manager=tool_manager,
        skill_router=skill_router,
        verbose=True
    )
    
    # 测试查询
    print("\n" + "-"*40)
    print("测试: 生成登录功能的测试计划")
    print("-"*40)
    
    response = agent.chat("为用户登录功能生成测试计划")
    print(f"\n📝 响应:\n{response[:500]}...")


def demo_skill_execution():
    """演示直接执行技能"""
    print_header("直接执行 Skill 演示")
    
    from skills import get_skill
    
    # 获取测试计划技能
    skill = get_skill("test_planning")
    if skill:
        print(f"\n执行 skill: {skill.name}")
        print(f"描述: {skill.description}")
        
        # 执行
        result = skill.execute(
            "为支付功能生成测试计划",
            context={
                "requirement": "支付功能需要支持微信支付、支付宝、银行卡三种方式",
                "save_to_file": True
            }
        )
        print(f"\n📝 结果长度: {len(result)} 字符")
        print(f"预览: {result[:300]}...")


def main():
    """主函数"""
    print("\n" + "="*60)
    print(" Smart QA Agent - ReAct + Skills 架构演示")
    print("="*60)
    
    # 1. 显示可用技能
    print_skill_info()
    
    # 2. 显示可用工具
    print_tools_info()
    
    # 3. 演示技能路由
    demo_skill_router()
    
    # 4. 演示技能执行
    demo_skill_execution()
    
    # 5. 演示 ReAct 对话（需要 LLM）
    try:
        demo_react_chat()
    except Exception as e:
        print(f"\n⚠️ ReAct 对话演示跳过 (需要 LLM 服务): {e}")
    
    print_header("演示完成")
    print("\n下一步：")
    print("1. 启动 LLM 服务 (如 Ollama)")
    print("2. 运行: python demo_react.py")
    print("3. 或集成到现有 main.py")


if __name__ == "__main__":
    main()
