#!/usr/bin/env python3
"""
Smart QA Agent - ReAct + Skills 架构 CLI

新的命令行入口，使用 ReAct 模式进行对话。
"""
import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 导入 readline 模块支持命令历史
try:
    import readline
    # 设置历史文件
    HISTORY_FILE = os.path.expanduser("~/.qa_agent_history")
    
    def load_history():
        try:
            readline.read_history_file(HISTORY_FILE)
            readline.set_history_length(1000)
        except FileNotFoundError:
            pass
    
    def save_history():
        try:
            readline.write_history_file(HISTORY_FILE)
        except Exception:
            pass
    
    # 加载历史记录
    load_history()
except ImportError:
    # 如果 readline 不可用，提供空实现
    readline = None
    def save_history():
        pass

from typing import Optional
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich import print as rprint

from agents import create_agent, tool_manager, skill_router
from agents.skill_router import SkillInfo
from config.settings import get_llm


console = Console()


def print_welcome():
    """打印欢迎信息"""
    console.print(Panel.fit(
        "[bold blue]Smart QA Agent[/bold blue] - ReAct + Skills 架构\n"
        "[dim]输入 'help' 查看帮助，输入 'quit' 或 'exit' 退出[/dim]",
        border_style="blue"
    ))


def print_help():
    """打印帮助信息"""
    help_text = """
## 命令

- `help` - 显示帮助信息
- `skills` - 显示所有可用技能
- `tools` - 显示所有可用工具
- `skill <name>` - 切换到指定技能
- `quit` / `exit` - 退出程序
- `clear` - 清屏

## 示例

```
> 为登录功能生成测试计划
> 设计用户注册的测试用例
> 分析这个项目的代码结构
> 什么是 RAG？
```
"""
    console.print(Markdown(help_text))


def print_skills():
    """显示所有技能"""
    skills = skill_router.list_skills()
    
    console.print("\n[bold]可用技能[/bold]\n")
    for skill in skills:
        console.print(f"[cyan]{skill.name}[/cyan]")
        console.print(f"  描述: {skill.description}")
        console.print(f"  工具: {', '.join(skill.tools) if skill.tools else '无'}")
        console.print()


def print_tools():
    """显示所有工具"""
    tools = tool_manager.list_all()
    
    console.print("\n[bold]可用工具[/bold]\n")
    for tool in tools:
        console.print(f"[cyan]{tool.name}[/cyan]")
        console.print(f"  描述: {tool.description}")
        console.print()


def register_tools():
    """注册所有工具到工具管理器"""
    from tools.file_tools import save_test_plan
    from tools.code_analyzer import analyze_project
    from tools.rag_tools import rag_retrieve
    from tools.document_tools import load_document
    
    # 注册文件工具
    tool_manager.register_function(
        name="save_test_plan",
        description="保存测试计划到文件",
        func=save_test_plan,
        category="test_planning"
    )
    
    tool_manager.register_function(
        name="load_requirements_doc",
        description="加载需求文档，返回文档内容",
        func=load_document,
        category="test_planning"
    )
    
    # 注册代码分析工具
    tool_manager.register_function(
        name="analyze_project",
        description="分析项目代码结构和统计信息",
        func=analyze_project,
        category="code_analysis"
    )
    
    # 注册 RAG 工具
    tool_manager.register_function(
        name="rag_retrieve",
        description="从知识库检索相关内容",
        func=rag_retrieve,
        category="rag_qa"
    )
    
    pass


def process_query(
    query: str, 
    agent, 
    selected_skill: Optional[str] = None
) -> str:
    """处理用户查询
    
    Args:
        query: 用户查询
        agent: ReAct Agent 实例
        selected_skill: 指定的技能名称
        
    Returns:
        Agent 响应
    """
    try:
        # 显示正在处理
        console.print(f"\n[dim]🎯 处理中... (技能: {selected_skill or 'auto'})[/dim]\n")
        
        # 调用 Agent
        response = agent.chat(query, skill_name=selected_skill)
        
        return response
        
    except Exception as e:
        return f"处理出错: {str(e)}"


def main():
    """主函数"""
    print_welcome()
    
    # 注册工具
    console.print("[dim]初始化工具...[/dim]")
    register_tools()
    console.print("[green]✓ 工具注册完成[/green]\n")
    
    # 创建 Agent
    console.print("[dim]初始化 Agent...[/dim]")
    try:
        agent = create_agent(
            tool_manager=tool_manager,
            skill_router=skill_router,
            verbose=False
        )
        console.print("[green]✓ Agent 初始化完成[/green]\n")
    except Exception as e:
        console.print(f"[red]✗ Agent 初始化失败: {e}[/red]\n")
        return
    
    selected_skill = None
    chat_history = []
    
    # 主循环
    while True:
        try:
            # 获取用户输入（使用标准 input 以支持 readline 历史）
            user_input = input("\n> ")
            
            # 处理空输入
            if not user_input.strip():
                continue
            
            # 命令处理
            cmd = user_input.strip().lower()
            
            if cmd in ['quit', 'exit', 'q']:
                console.print("\n[blue]再见！👋[/blue]\n")
                save_history()
                break
            
            elif cmd == 'help':
                print_help()
                continue
            
            elif cmd == 'skills':
                print_skills()
                continue
            
            elif cmd == 'tools':
                print_tools()
                continue
            
            elif cmd == 'clear':
                console.clear()
                print_welcome()
                continue
            
            elif cmd.startswith('skill '):
                skill_name = user_input[6:].strip()
                if skill_name:
                    # 验证技能是否存在
                    skill = skill_router._skills.get(skill_name)
                    if skill:
                        selected_skill = skill_name
                        console.print(f"[green]已切换到技能: {skill_name}[/green]")
                    else:
                        console.print(f"[red]未找到技能: {skill_name}[/red]")
                continue
            
            elif cmd == 'skill':
                selected_skill = None
                console.print("[green]已切换到自动模式[/green]")
                continue
            
            # 正常查询
            chat_history.append({"role": "user", "content": user_input})
            
            # 处理查询
            response = process_query(user_input, agent, selected_skill)
            
            # 显示响应
            console.print()
            console.print(Panel(
                Markdown(response),
                border_style="green",
                title="[bold]响应[/bold]"
            ))
            
            chat_history.append({"role": "assistant", "content": response})
            
        except KeyboardInterrupt:
            console.print("\n\n[blue]再见！👋[/blue]\n")
            break
        except Exception as e:
            console.print(f"\n[red]错误: {e}[/red]\n")


if __name__ == "__main__":
    main()
