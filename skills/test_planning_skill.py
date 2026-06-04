"""
测试计划技能 (Test Planning Skill)

该技能专注于生成测试计划、测试策略、测试范围定义等。
"""
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field

from skills.base import Skill, Tool
from config.settings import get_llm


@dataclass
class TestPlanningSkill(Skill):
    """测试计划技能"""
    name: str = "test_planning"
    description: str = "生成测试计划、测试策略、测试范围定义"
    examples: List[str] = field(default_factory=lambda: [
        "生成测试计划",
        "制定测试策略",
        "定义测试范围",
        "测试计划应该包含什么"
    ])
    max_iterations: int = 5
    
    def execute(self, query: str, context: Dict[str, Any] = None) -> str:
        """执行测试计划生成
        
        Args:
            query: 用户查询
            context: 上下文信息，可能包含：
                - document_content: 需求文档内容
                - rag_context: RAG 检索的上下文
                - requirements: 需求描述
                
        Returns:
            生成的测试计划
        """
        from langchain.schema import HumanMessage, SystemMessage
        
        context = context or {}
        
        # 1. 收集信息
        document = context.get("document_content", "")
        rag_context = context.get("rag_context", "")
        requirements = context.get("requirement", query)
        
        # 2. 构建提示词
        system_prompt = self._build_system_prompt(document, rag_context)
        user_prompt = self._build_user_prompt(requirements)
        
        # 3. 调用 LLM
        llm = get_llm()
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ]
        
        response = llm.invoke(messages)
        test_plan = response.content
        
        # 4. 可选：保存到文件
        if context.get("save_to_file", False):
            from tools.file_tools import save_test_plan
            filename = save_test_plan(test_plan, requirements)
            if not filename.startswith("Failed"):
                test_plan += f"\n\n📁 测试计划已保存到: {filename}"
        
        return test_plan
    
    def _build_system_prompt(self, document: str, rag_context: str) -> str:
        """构建系统提示词"""
        base = """你是专业的测试计划生成专家。

## 你的职责
根据需求文档和上下文，生成完整、专业的测试计划。

## 测试计划标准结构

1. **测试范围 (Scope)**
   - 明确测试的内容
   - 明确不测试的内容
   - 测试对象和版本

2. **测试策略 (Strategy)**
   - 测试类型（功能测试、性能测试、安全测试等）
   - 测试方法
   - 测试重点和优先级

3. **资源计划 (Resources)**
   - 测试人员分工
   - 测试环境要求
   - 测试工具

4. **测试进度 (Schedule)**
   - 里程碑和时间节点
   - 每个阶段的交付物

5. **风险分析 (Risks)**
   - 已识别的风险
   - 风险应对措施

## 输出要求
- 使用 Markdown 格式
- 内容具体、可执行
- 优先级明确"""
        
        if rag_context:
            base += f"\n\n## 相关文档上下文\n\n{rag_context}"
        
        if document:
            base += f"\n\n## 需求文档\n\n{document}"
        
        return base
    
    def _build_user_prompt(self, requirements: str) -> str:
        """构建用户提示词"""
        return f"""请为以下需求生成测试计划：

{requirements}

请确保测试计划：
1. 覆盖所有关键功能点
2. 包含正向和异常场景
3. 优先级合理
4. 时间安排可行
"""


@dataclass  
class TestPlanningTools:
    """测试计划技能的工具集"""
    
    @staticmethod
    def get_tools() -> List[Tool]:
        """获取该技能可用的工具"""
        from tools.file_tools import save_test_plan
        from tools.document_tools import load_document
        
        return [
            Tool(
                name="save_test_plan",
                description="保存测试计划到文件，返回文件路径",
                function=save_test_plan,
                parameters_schema={
                    "type": "object",
                    "properties": {
                        "content": {"type": "string", "description": "测试计划内容"},
                        "filename_prefix": {"type": "string", "description": "文件名前缀"}
                    },
                    "required": ["content", "filename_prefix"]
                }
            ),
            Tool(
                name="load_requirements_doc",
                description="加载需求文档",
                function=load_document,
                parameters_schema={
                    "type": "object", 
                    "properties": {
                        "filepath": {"type": "string", "description": "文档路径"}
                    },
                    "required": ["filepath"]
                }
            )
        ]
