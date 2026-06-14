from __future__ import annotations
import json
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from enum import Enum
from langchain_openai import ChatOpenAI

from agents.tool_manager import Tool, ToolManager
from agents.skill_router import SkillRouter, SkillInfo, skill_router
from prompts.react_prompt import (
    ReActMessage, ToolInfo, build_react_system_prompt
)
from config.settings import get_llm


class AgentState(Enum):
    """Agent 状态"""
    IDLE = "idle"
    THINKING = "thinking"
    ACTING = "acting"
    OBSERVING = "observing"
    FINISHED = "finished"
    ERROR = "error"


@dataclass
class ReActStep:
    """ReAct 循环中的单步"""
    thought: str = ""
    action: str = ""
    action_input: Dict[str, Any] = field(default_factory=dict)
    observation: str = ""


@dataclass
class ConversationContext:
    """对话上下文"""
    skill: Optional[SkillInfo] = None
    history: List[Dict[str, str]] = field(default_factory=list)
    state: AgentState = AgentState.IDLE
    metadata: Dict[str, Any] = field(default_factory=dict)


class ReActAgent:
    """ReAct Agent 核心类

    实现 Reasoning + Acting 模式的智能代理。
    支持渐进式工具披露和动态技能选择。
    """

    def __init__(
        self,
        tool_mgr: Optional[ToolManager] = None,
        skill_rtr: Optional[SkillRouter] = None,
        llm: Optional[ChatOpenAI] = None,
        max_iterations: int = 10,
        verbose: bool = False
    ):
        """
        Args:
            tool_mgr: 工具管理器
            skill_rtr: 技能路由器
            llm: 语言模型实例
            max_iterations: 最大迭代次数
            verbose: 是否输出详细日志
        """
        self.tool_manager = tool_mgr or ToolManager()
        self.skill_router = skill_rtr or skill_router
        self.llm = llm or get_llm()
        self.max_iterations = max_iterations
        self.verbose = verbose

        self._context: Optional[ConversationContext] = None

    def chat(self, query: str, skill_name: Optional[str] = None) -> str:
        """与 Agent 对话

        Args:
            query: 用户查询
            skill_name: 指定技能（可选，默认自动路由）

        Returns:
            Agent 响应
        """
        # 1. 初始化上下文
        self._context = ConversationContext()

        # 2. 路由到技能
        if skill_name:
            self._context.skill = self.skill_router._skills.get(skill_name)
        else:
            primary_skill = self.skill_router.get_primary_skill(query)
            self._context.skill = primary_skill

        if self._context.skill:
            if self.verbose:
                print(f"🎯 Selected skill: {self._context.skill.name}")

            # 3. 渐进式披露：只加载技能需要的工具
            available_tools = self._get_skill_tools(self._context.skill)
        else:
            available_tools = self.tool_manager.get_available_tools()

        # 4. 构建系统提示词
        system_prompt = self._build_system_prompt(available_tools)

        # 5. 执行 ReAct 循环
        response = self._run_react_loop(query, system_prompt, available_tools)

        return response

    def _get_skill_tools(self, skill: SkillInfo) -> List[Tool]:
        """获取技能需要的工具"""
        if not skill.tools:
            # 如果技能没有指定工具，返回所有可用工具
            return self.tool_manager.get_available_tools()

        tools = []
        for tool_name in skill.tools:
            tool = self.tool_manager.get(tool_name)
            if tool:
                tools.append(tool)

        # 如果没有找到指定工具，返回基础工具
        if not tools:
            return self.tool_manager.get_available_tools()[:3]

        return tools

    def _build_system_prompt(self, tools: List[Tool]) -> str:
        """构建系统提示词"""
        tool_infos = [
            ToolInfo(
                name=t.name,
                description=t.description,
                parameters=json.dumps(t.parameters_schema, ensure_ascii=False)
            )
            for t in tools
        ]

        skills = [s.name for s in self.skill_router.list_skills()]

        return build_react_system_prompt(
            tools=[{"name": t.name, "description": t.description, "parameters": ""} for t in tools],
            skills=skills,
            progressive=True
        )

    def _run_react_loop(
        self, 
        query: str, 
        system_prompt: str,
        available_tools: List[Tool]
    ) -> str:
        """执行 ReAct 循环

        循环：Thought → Action → Observation → ...
        直到得到 Final Answer 或达到最大迭代次数。
        """
        conversation = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": query}
        ]

        steps: List[ReActStep] = []
        final_answer = None

        for iteration in range(self.max_iterations):
            if self.verbose:
                print(f"\n{'='*60}")
                print(f"🔄 迭代 {iteration + 1}/{self.max_iterations}")
                print(f"{'='*60}")

            # 1. 调用 LLM 获取下一步行动
            self._context.state = AgentState.THINKING

            response = self._call_llm(conversation)
            conversation.append({"role": "assistant", "content": response})

            # 2. 解析响应
            parsed = ReActMessage.parse_response(response)

            # 3. 显示思考过程
            if ReActMessage.THOUGHT in parsed and self.verbose:
                thought = parsed[ReActMessage.THOUGHT]
                print(f"\n💡 [思考] {thought}")

            # 4. 检查是否有 Final Answer
            if ReActMessage.FINAL_ANSWER in parsed:
                final_answer = parsed[ReActMessage.FINAL_ANSWER]
                if self.verbose:
                    print(f"\n✅ [最终答案] {final_answer[:100]}...")
                break

            # 5. 解析 Action
            if ReActMessage.ACTION in parsed:
                action_name = parsed[ReActMessage.ACTION]
                action_input = {}

                if ReActMessage.ACTION_INPUT in parsed:
                    try:
                        action_input = json.loads(parsed[ReActMessage.ACTION_INPUT])
                    except json.JSONDecodeError:
                        action_input = {"input": parsed[ReActMessage.ACTION_INPUT]}

                # 6. 显示要执行的工具
                if self.verbose:
                    print(f"\n🔧 [执行工具] {action_name}")
                    print(f"   └── 参数: {json.dumps(action_input, ensure_ascii=False)}")

                # 7. 执行 Action
                self._context.state = AgentState.ACTING
                step = ReActStep(
                    thought=parsed.get(ReActMessage.THOUGHT, ""),
                    action=action_name,
                    action_input=action_input
                )

                observation = self._execute_action(action_name, action_input, available_tools)
                step.observation = observation
                steps.append(step)

                # 8. 显示工具执行结果
                if self.verbose:
                    print(f"\n📋 [工具返回]")
                    print(f"   └── {observation}")

                # 9. 添加 Observation 到对话
                conversation.append({
                    "role": "user",
                    "content": ReActMessage.format_observation(observation)
                })
            else:
                # 没有 Action，可能需要直接回答
                if ReActMessage.THOUGHT in parsed:
                    final_answer = parsed[ReActMessage.THOUGHT]
                break

        # 保存历史
        self._context.history = conversation[1:]  # 去掉 system prompt

        return final_answer or "抱歉，我无法完成这个任务。"

    def _call_llm(self, conversation: List[Dict]) -> str:
        """调用 LLM"""
        from langchain.schema import HumanMessage, AIMessage, SystemMessage

        messages = []
        for msg in conversation:
            if msg["role"] == "system":
                messages.append(SystemMessage(content=msg["content"]))
            elif msg["role"] == "user":
                messages.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                messages.append(AIMessage(content=msg["content"]))

        response = self.llm.invoke(messages)
        return response.content

    def _execute_action(
        self, 
        action_name: str, 
        action_input: Dict[str, Any],
        available_tools: List[Tool]
    ) -> str:
        """执行 Action"""
        self._context.state = AgentState.ACTING

        # 查找工具
        tool = None
        for t in available_tools:
            if t.name == action_name:
                tool = t
                break

        if not tool:
            return f"Error: Tool '{action_name}' not found. Available tools: {[t.name for t in available_tools]}"

        # 执行工具
        try:
            result = tool.execute(**action_input)
            self._context.state = AgentState.OBSERVING
            return str(result)
        except Exception as e:
            self._context.state = AgentState.ERROR
            return f"Error executing {action_name}: {str(e)}"

    def get_context(self) -> ConversationContext:
        """获取当前上下文"""
        return self._context


# 全局 Agent 实例
react_agent = ReActAgent(verbose=True)


def create_agent(
    tool_manager: Optional[ToolManager] = None,
    skill_router: Optional[SkillRouter] = None,
    **kwargs
) -> ReActAgent:
    """工厂函数：创建 ReAct Agent"""
    return ReActAgent(
        tool_manager=tool_manager,
        skill_router=skill_router,
        **kwargs
    )
