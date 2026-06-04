from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field


@dataclass
class Tool:
    """工具定义"""
    name: str
    description: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    function: callable = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为工具描述字典"""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters
        }


@dataclass
class Skill:
    """技能基类
    
    每个 Skill 是一个独立的子代理，拥有自己的工具集和提示词。
    Skills 采用渐进式披露原则，只在需要时加载和暴露工具。
    """
    name: str
    description: str
    examples: List[str] = field(default_factory=list)
    tools: List[Tool] = field(default_factory=list)
    system_prompt: str = ""
    max_iterations: int = 10
    
    @abstractmethod
    def execute(self, query: str, context: Dict[str, Any] = None) -> str:
        """执行技能核心逻辑
        
        Args:
            query: 用户查询
            context: 上下文信息
            
        Returns:
            执行结果
        """
        pass
    
    def get_tools(self) -> List[Tool]:
        """获取该技能可用的工具列表（渐进式披露）
        
        默认返回所有工具，子类可重写实现按需加载
        """
        return self.tools
    
    def get_prompt(self) -> str:
        """获取技能的系统提示词"""
        return self.system_prompt or self._default_prompt()
    
    def _default_prompt(self) -> str:
        """生成默认提示词"""
        tools_desc = "\n".join([
            f"- {tool.name}: {tool.description}" 
            for tool in self.tools
        ])
        return f"""你是 {self.name} 专家。

技能描述：{self.description}

可用工具：
{tools_desc}

请分析用户问题，选择合适的工具来完成任务。"""

    def add_tool(self, tool: Tool) -> None:
        """动态添加工具"""
        self.tools.append(tool)
    
    def remove_tool(self, tool_name: str) -> None:
        """动态移除工具"""
        self.tools = [t for t in self.tools if t.name != tool_name]


class SkillRegistry:
    """技能注册中心
    
    管理系统中的所有技能，支持动态注册和查找。
    """
    
    def __init__(self):
        self._skills: Dict[str, Skill] = {}
    
    def register(self, skill: Skill) -> None:
        """注册技能"""
        self._skills[skill.name] = skill
    
    def get(self, name: str) -> Optional[Skill]:
        """获取技能"""
        return self._skills.get(name)
    
    def list_skills(self) -> List[Skill]:
        """列出所有技能"""
        return list(self._skills.values())
    
    def match_skills(self, query: str) -> List[tuple[Skill, float]]:
        """根据查询匹配最相关的技能
        
        Args:
            query: 用户查询
            
        Returns:
            按相关度排序的技能列表 [(skill, score), ...]
        """
        from nodes.intent_node import classify_intent
        # 使用已有的意图识别功能
        intent = classify_intent(query)
        
        matched = []
        for skill in self._skills.values():
            # 简单的关键词匹配，可替换为 embedding 相似度
            score = 0.0
            query_lower = query.lower()
            if skill.name.lower() in query_lower:
                score += 0.5
            if any(keyword in query_lower for keyword in skill.description.lower().split()):
                score += 0.3
            if any(ex in query_lower for ex in skill.examples):
                score += 0.2
            if score > 0:
                matched.append((skill, score))
        
        return sorted(matched, key=lambda x: x[1], reverse=True)


# 全局技能注册中心实例
skill_registry = SkillRegistry()
