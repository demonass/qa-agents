from typing import List, Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class ToolInfo:
    """工具信息"""
    name: str
    description: str
    parameters: str  # 简化的参数描述


@dataclass
class ReActPrompt:
    """ReAct 提示词模板
    
    支持渐进式披露工具集和 Skills。
    """
    
    # 系统提示词
    SYSTEM_PROMPT = """你是一个智能 QA 测试助手，采用 ReAct (Reasoning + Acting) 模式来解决问题。

ReAct 模式的核心循环：
1. Thought (思考)：分析当前情况，决定下一步行动
2. Action (行动)：调用工具或生成响应
3. Observation (观察)：获取行动结果
4. 重复直到完成任务

重要原则：
- 在做出判断前，先思考和分析
- 只使用提供的工具
- 提供清晰、完整的回答
- 如果无法完成任务，说明原因
"""
    
    # 工具披露提示词（渐进式）
    TOOLS_PROMPT = """
## 可用工具

你当前可用的工具：

{tool_list}

## 响应格式（必须严格遵循）

你必须按以下格式回复，每一步都必须包含 Thought:

1. 先写思考：
   Thought: [分析问题，决定行动，说明理由]

2. 然后决定是否需要使用工具：
   - 如果需要使用工具：
     Action: tool_name
     Action Input: {{
       "param1": "value1",
       "param2": "value2"
     }}
   
   - 如果可以直接回答：
     Final Answer: [你的完整回答]

3. 当你收到工具的观察结果后，继续思考下一步：
   Thought: [基于观察结果的分析]
   - 如果需要继续使用工具，重复步骤2
   - 如果已经有足够信息，输出 Final Answer

重要：
- 每一次回复都必须以 "Thought:" 开头
- 不要一次性输出多个 Thought 和 Action
- 每次只执行一个 Action，等待观察结果后再继续
"""
    
    # 思考过程提示词
    THOUGHT_PROMPT = """
## 推理过程

请按照以下步骤思考：

1. 理解问题：
   - 用户想要什么？
   - 需要哪些信息？

2. 分析可用资源：
   - 有哪些工具可用？
   - 需要调用哪些工具？

3. 制定计划：
   - 步骤1：...
   - 步骤2：...

4. 执行并验证：
   - 调用工具获取结果
   - 验证结果是否正确
"""
    
    # Skill 选择提示词
    SKILL_SELECTION_PROMPT = """根据用户问题，选择最合适的技能：

{skill_list}

请选择最匹配的一个技能，并说明理由。

Skills: {skill_names}

Selected: [选择一个]
Reason: [说明理由]
"""
    
    # 渐进式披露提示词
    PROGRADE_DISCLOSURE_PROMPT = """
## 渐进式工具披露

当前阶段只需要以下工具：

{visible_tools}

其他工具将在需要时逐步提供。
"""
    
    @classmethod
    def build_system_prompt(
        cls, 
        tools: List[ToolInfo],
        skills: Optional[List[str]] = None,
        progressive: bool = False
    ) -> str:
        """构建完整的系统提示词
        
        Args:
            tools: 可用工具列表
            skills: 可用技能列表（可选）
            progressive: 是否启用渐进式披露
        """
        prompt = cls.SYSTEM_PROMPT
        
        # 添加工具信息
        tool_list = cls._format_tools(tools, progressive)
        prompt += cls.TOOLS_PROMPT.format(tool_list=tool_list)
        
        # 添加技能信息
        if skills:
            prompt += f"\n## 可用技能\n\n"
            prompt += "\n".join([f"- {s}" for s in skills])
        
        # 添加思考提示
        prompt += cls.THOUGHT_PROMPT
        
        return prompt
    
    @classmethod
    def _format_tools(cls, tools: List[ToolInfo], progressive: bool = False) -> str:
        """格式化工具列表"""
        if progressive:
            # 渐进式：只显示前几个工具
            visible = tools[:3]
            hidden = len(tools) - 3
            tool_text = "\n".join([
                f"- **{t.name}**: {t.description}" 
                for t in visible
            ])
            if hidden > 0:
                tool_text += f"\n- ... 还有 {hidden} 个工具可用（按需披露）"
            return tool_text
        else:
            return "\n".join([
                f"- **{t.name}**: {t.description}" 
                for t in tools
            ])
    
    @classmethod
    def select_skill_prompt(cls, skills: List[Dict[str, str]], query: str) -> str:
        """生成技能选择提示词
        
        Args:
            skills: 技能列表 [{"name": "...", "description": "..."}]
            query: 用户查询
        """
        skill_list = "\n".join([
            f"- {s['name']}: {s['description']}"
            for s in skills
        ])
        return cls.SKILL_SELECTION_PROMPT.format(
            skill_list=skill_list,
            skill_names=", ".join([s['name'] for s in skills])
        )


class ReActMessage:
    """ReAct 消息格式"""
    
    THOUGHT = "Thought"
    ACTION = "Action"
    ACTION_INPUT = "Action Input"
    OBSERVATION = "Observation"
    FINAL_ANSWER = "Final Answer"
    
    @classmethod
    def parse_response(cls, response: str) -> Dict[str, str]:
        """解析 LLM 响应，提取 ReAct 元素
        
        Args:
            response: LLM 响应文本
            
        Returns:
            解析后的字典，包含 thought, action, observation 等
        """
        result = {}
        lines = response.strip().split("\n")
        current_key = None
        current_value = []
        
        for line in lines:
            line = line.strip()
            
            # 检查是否是新元素
            if line.startswith("Thought:"):
                if current_key:
                    result[current_key] = "\n".join(current_value)
                current_key = cls.THOUGHT
                current_value = [line.replace("Thought:", "").strip()]
            elif line.startswith("Action:"):
                if current_key:
                    result[current_key] = "\n".join(current_value)
                current_key = cls.ACTION
                current_value = [line.replace("Action:", "").strip()]
            elif line.startswith("Action Input:"):
                if current_key:
                    result[current_key] = "\n".join(current_value)
                current_key = cls.ACTION_INPUT
                current_value = [line.replace("Action Input:", "").strip()]
            elif line.startswith("Observation:"):
                if current_key:
                    result[current_key] = "\n".join(current_value)
                current_key = cls.OBSERVATION
                current_value = [line.replace("Observation:", "").strip()]
            elif line.startswith("Final Answer:"):
                if current_key:
                    result[current_key] = "\n".join(current_value)
                current_key = cls.FINAL_ANSWER
                current_value = [line.replace("Final Answer:", "").strip()]
            else:
                if current_key:
                    current_value.append(line)
        
        if current_key:
            result[current_key] = "\n".join(current_value)
        
        return result
    
    @classmethod
    def format_action(cls, tool_name: str, tool_input: Dict[str, Any]) -> str:
        """格式化 Action 消息
        
        Args:
            tool_name: 工具名称
            tool_input: 工具输入参数
        """
        import json
        return f"""Action: {tool_name}
Action Input: {json.dumps(tool_input, ensure_ascii=False)}"""
    
    @classmethod
    def format_observation(cls, observation: str) -> str:
        """格式化 Observation 消息"""
        return f"Observation: {observation}"
    
    @classmethod
    def format_final_answer(cls, answer: str) -> str:
        """格式化 Final Answer"""
        return f"Final Answer: {answer}"


# 导出便捷函数
def build_react_system_prompt(tools: List[Dict], **kwargs) -> str:
    """便捷函数：构建 ReAct 系统提示词"""
    tool_infos = [ToolInfo(**t) for t in tools]
    return ReActPrompt.build_system_prompt(tool_infos, **kwargs)
