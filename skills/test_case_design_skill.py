"""
测试用例设计技能 (Test Case Design Skill)

该技能专注于设计测试用例、测试场景、测试数据等。
"""
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field

from skills.base import Skill, Tool
from config.settings import get_llm


@dataclass
class TestCaseDesignSkill(Skill):
    """测试用例设计技能"""
    name: str = "test_case_design"
    description: str = "设计测试用例、测试场景、测试数据"
    examples: List[str] = field(default_factory=lambda: [
        "设计测试用例",
        "生成测试场景",
        "写测试用例",
        "测试用例应该怎么写"
    ])
    max_iterations: int = 5
    
    def execute(self, query: str, context: Dict[str, Any] = None) -> str:
        """执行测试用例设计
        
        Args:
            query: 用户查询
            context: 上下文信息，可能包含：
                - document_content: 需求文档内容
                - rag_context: RAG 检索的上下文
                - test_plan: 相关测试计划
                
        Returns:
            生成的测试用例
        """
        from langchain.schema import HumanMessage, SystemMessage
        
        context = context or {}
        
        # 1. 收集信息
        document = context.get("document_content", "")
        rag_context = context.get("rag_context", "")
        test_plan = context.get("test_plan", "")
        requirements = context.get("requirement", query)
        
        # 2. 确定要设计的用例数量和范围
        scope = context.get("scope", "all")  # all, critical, normal
        
        # 3. 构建提示词
        system_prompt = self._build_system_prompt(document, rag_context, test_plan)
        user_prompt = self._build_user_prompt(requirements, scope)
        
        # 4. 调用 LLM
        llm = get_llm()
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ]
        
        response = llm.invoke(messages)
        return response.content
    
    def _build_system_prompt(
        self, 
        document: str, 
        rag_context: str,
        test_plan: str
    ) -> str:
        """构建系统提示词"""
        base = """你是专业的测试用例设计专家。

## 你的职责
根据需求设计完整、详细的测试用例。

## 测试用例标准格式

### 单个测试用例格式
```markdown
### TC-XXX: [用例名称]

| 字段 | 内容 |
|------|------|
| 用例ID | TC-XXX |
| 用例标题 | [简洁明确的标题] |
| 前置条件 | [执行前的准备条件] |
| 测试步骤 | 1. [步骤1] 2. [步骤2] ... |
| 预期结果 | [期望的输出/行为] |
| 优先级 | P0/P1/P2/P3 |
| 测试类型 | 功能/边界/异常/性能 |
```

## 测试用例设计原则

1. **等价类划分**
   - 将输入数据分成有效和无效等价类
   - 每个等价类选取代表性值

2. **边界值分析**
   - 测试边界值和边界值附近的值
   - 如：0, 1, N-1, N, N+1

3. **正交测试法**
   - 多因素组合时使用正交表

4. **场景测试**
   - 设计正常场景
   - 设计异常场景
   - 设计失败场景

## 用例数量建议
- 核心功能：10-20 个用例
- 一般功能：5-10 个用例
- 简单功能：3-5 个用例

## 优先级定义
- P0: 核心流程、主路径，必须通过
- P1: 重要功能，允许个别失败
- P2: 一般功能，允许失败
- P3: 边缘功能，可以跳过"""
        
        if test_plan:
            base += f"\n\n## 相关测试计划\n\n{test_plan}"
        
        if rag_context:
            base += f"\n\n## 相关文档上下文\n\n{rag_context}"
        
        if document:
            base += f"\n\n## 需求文档\n\n{document}"
        
        return base
    
    def _build_user_prompt(self, requirements: str, scope: str) -> str:
        """构建用户提示词"""
        scope_hint = {
            "all": "为所有功能点设计完整测试用例",
            "critical": "只设计 P0/P1 级别的关键测试用例",
            "normal": "设计常规测试用例"
        }.get(scope, "设计完整测试用例")
        
        return f"""请为以下需求设计测试用例：

{requirements}

{scope_hint}

请确保测试用例：
1. 覆盖正向、边界、异常场景
2. 步骤清晰、可执行
3. 预期结果明确
4. 优先级合理
"""


@dataclass
class TestCaseDesignTools:
    """测试用例设计技能的工具集"""
    
    @staticmethod
    def get_tools() -> List[Tool]:
        """获取该技能可用的工具"""
        from tools.file_tools import save_test_plan
        from tools.document_tools import load_document
        
        return [
            Tool(
                name="save_test_cases",
                description="保存测试用例到文件，返回文件路径",
                function=save_test_plan,
                parameters_schema={
                    "type": "object",
                    "properties": {
                        "content": {"type": "string", "description": "测试用例内容"},
                        "filename_prefix": {"type": "string", "description": "文件名前缀"}
                    },
                    "required": ["content", "filename_prefix"]
                }
            ),
            Tool(
                name="load_requirements",
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
