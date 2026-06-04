from abc import ABC, abstractmethod
from typing import Dict, Any, List, Callable, Optional
from dataclasses import dataclass, field
import inspect
import json


@dataclass
class Tool:
    """工具定义
    
    工具是 Agent 可以调用的外部函数，支持渐进式披露。
    """
    name: str
    description: str
    function: Callable
    parameters_schema: Dict[str, Any] = field(default_factory=dict)
    is_available: bool = True
    availability_reason: str = ""
    
    def __post_init__(self):
        """自动从函数签名生成参数模式"""
        if not self.parameters_schema and callable(self.function):
            sig = inspect.signature(self.function)
            self.parameters_schema = self._generate_schema(sig)
    
    def _generate_schema(self, sig: inspect.Signature) -> Dict[str, Any]:
        """从函数签名生成 JSON Schema"""
        properties = {}
        required = []
        
        for name, param in sig.parameters.items():
            if name in ('self', 'cls'):
                continue
            
            param_type = "string"
            if param.annotation == int:
                param_type = "integer"
            elif param.annotation == float:
                param_type = "number"
            elif param.annotation == bool:
                param_type = "boolean"
            elif param.annotation == list:
                param_type = "array"
            elif param.annotation == dict:
                param_type = "object"
            
            prop = {"type": param_type}
            if param.default != inspect.Parameter.empty:
                prop["default"] = param.default
            else:
                required.append(name)
            
            properties[name] = prop
        
        return {
            "type": "object",
            "properties": properties,
            "required": required
        }
    
    def to_openai_format(self) -> Dict[str, Any]:
        """转换为 OpenAI 函数调用格式"""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters_schema
            }
        }
    
    def execute(self, **kwargs) -> Any:
        """执行工具"""
        if not self.is_available:
            return f"Tool unavailable: {self.availability_reason}"
        
        try:
            return self.function(**kwargs)
        except TypeError as e:
            return f"Parameter error: {e}"
        except Exception as e:
            return f"Execution error: {str(e)}"
    
    def check_availability(self) -> bool:
        """检查工具是否可用"""
        return self.is_available


class ToolManager:
    """工具管理器
    
    负责工具的注册、查找、按需加载和渐进式披露。
    """
    
    def __init__(self):
        self._tools: Dict[str, Tool] = {}
        self._tool_categories: Dict[str, List[str]] = {}  # category -> tool_names
        self._loaded_by_skill: Dict[str, List[str]] = {}  # skill -> loaded_tool_names
    
    def register(self, tool: Tool, category: str = "general") -> None:
        """注册工具
        
        Args:
            tool: 工具实例
            category: 工具分类（用于渐进式披露）
        """
        self._tools[tool.name] = tool
        if category not in self._tool_categories:
            self._tool_categories[category] = []
        if tool.name not in self._tool_categories[category]:
            self._tool_categories[category].append(tool.name)
    
    def register_function(
        self, 
        name: str, 
        description: str, 
        func: Callable,
        category: str = "general",
        **kwargs
    ) -> Tool:
        """便捷方法：直接注册函数"""
        tool = Tool(
            name=name,
            description=description,
            function=func,
            **kwargs
        )
        self.register(tool, category)
        return tool
    
    def get(self, name: str) -> Optional[Tool]:
        """获取工具"""
        return self._tools.get(name)
    
    def list_all(self) -> List[Tool]:
        """列出所有已注册的工具"""
        return list(self._tools.values())
    
    def list_by_category(self, category: str) -> List[Tool]:
        """按分类列出工具"""
        tool_names = self._tool_categories.get(category, [])
        return [self._tools[name] for name in tool_names if name in self._tools]
    
    def get_for_skill(self, skill_name: str) -> List[Tool]:
        """获取特定技能可用的工具（渐进式披露）
        
        Args:
            skill_name: 技能名称
            
        Returns:
            该技能可用的工具列表
        """
        # 如果技能有预加载的工具列表，返回这些
        if skill_name in self._loaded_by_skill:
            tool_names = self._loaded_by_skill[skill_name]
            return [self._tools[name] for name in tool_names if name in self._tools]
        
        # 默认返回该技能分类下的所有工具
        return self.list_by_category(skill_name)
    
    def load_tools_for_skill(self, skill_name: str, tool_names: List[str]) -> None:
        """为技能显式加载工具
        
        Args:
            skill_name: 技能名称
            tool_names: 要加载的工具名称列表
        """
        self._loaded_by_skill[skill_name] = tool_names
    
    def get_available_tools(self) -> List[Tool]:
        """获取所有可用的工具"""
        return [t for t in self._tools.values() if t.check_availability()]
    
    def get_tool_schemas(self) -> List[Dict[str, Any]]:
        """获取所有工具的 schema（用于 LLM 函数调用）"""
        return [t.to_openai_format() for t in self.get_available_tools()]
    
    def set_tool_availability(self, name: str, available: bool, reason: str = "") -> None:
        """设置工具可用性"""
        if name in self._tools:
            self._tools[name].is_available = available
            self._tools[name].availability_reason = reason


# 全局工具管理器实例
tool_manager = ToolManager()
