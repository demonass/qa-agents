"""
代码分析技能 (Code Analysis Skill)

该技能专注于分析代码结构、代码质量、代码统计等。
"""
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field

from skills.base import Skill, Tool
from config.settings import get_llm


@dataclass
class CodeAnalysisSkill(Skill):
    """代码分析技能"""
    name: str = "code_analysis"
    description: str = "分析代码结构、代码质量、代码行数统计"
    examples: List[str] = field(default_factory=lambda: [
        "分析代码",
        "代码质量怎么样",
        "统计代码行数",
        "代码结构是什么"
    ])
    max_iterations: int = 3
    
    def execute(self, query: str, context: Dict[str, Any] = None) -> str:
        """执行代码分析
        
        Args:
            query: 用户查询
            context: 上下文信息，可能包含：
                - project_path: 项目路径
                - code_stats: 代码统计信息
                
        Returns:
            代码分析报告
        """
        from langchain.schema import HumanMessage, SystemMessage
        
        context = context or {}
        project_path = context.get("project_path", "")
        code_stats = context.get("code_stats", "")
        
        # 1. 如果没有统计信息，先统计
        if not code_stats and project_path:
            from tools.code_analyzer import analyze_project
            code_stats = analyze_project(project_path)
        
        # 2. 分析查询类型
        analysis_type = self._determine_analysis_type(query)
        
        # 3. 构建提示词
        system_prompt = self._build_system_prompt(analysis_type, code_stats)
        user_prompt = self._build_user_prompt(query, project_path, analysis_type)
        
        # 4. 调用 LLM
        llm = get_llm()
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ]
        
        response = llm.invoke(messages)
        return response.content
    
    def _determine_analysis_type(self, query: str) -> str:
        """判断分析类型"""
        query_lower = query.lower()
        
        if any(kw in query_lower for kw in ["质量", "review", "review", "best practice", "最佳实践"]):
            return "quality"
        elif any(kw in query_lower for kw in ["结构", "structure", "架构", "architecture"]):
            return "structure"
        elif any(kw in query_lower for kw in ["行数", "line", "统计", "count", "lines of code"]):
            return "statistics"
        elif any(kw in query_lower for kw in ["安全", "security", "漏洞", "vulnerability"]):
            return "security"
        elif any(kw in query_lower for kw in ["性能", "performance", "优化", "optimize"]):
            return "performance"
        else:
            return "comprehensive"
    
    def _build_system_prompt(self, analysis_type: str, code_stats: str) -> str:
        """构建系统提示词"""
        base = f"""你是专业的代码分析专家。

## 分析类型: {analysis_type}

"""
        
        if code_stats:
            base += f"## 代码统计信息\n\n{code_stats}\n\n"
        
        # 根据分析类型添加不同指导
        prompts = {
            "quality": """## 代码质量分析要点

1. **代码可读性**
   - 命名规范
   - 注释质量
   - 代码结构

2. **代码可维护性**
   - 复杂度
   - 耦合度
   - 重复代码

3. **代码可靠性**
   - 错误处理
   - 边界条件
   - 异常处理

4. **改进建议**
   - 列出具体问题
   - 提供优化方案
   - 给出代码示例（必要时）""",
            
            "structure": """## 代码结构分析要点

1. **目录结构**
   - 模块划分
   - 层次结构
   - 命名规范

2. **依赖关系**
   - 模块间依赖
   - 外部依赖
   - 循环依赖

3. **设计模式**
   - 使用的设计模式
   - 模式使用是否恰当

4. **架构建议**
   - 当前架构特点
   - 潜在问题
   - 改进方向""",
            
            "statistics": """## 代码统计要点

1. **语言分布**
   - 各语言代码行数
   - 占比分析

2. **文件分布**
   - 文件数量
   - 平均文件大小
   - 大文件识别

3. **趋势分析**
   - 主要代码贡献
   - 复杂度热点

4. **统计建议**
   - 合理的代码量范围
   - 异常检测""",
            
            "comprehensive": """## 综合分析要点

1. **整体概况**
   - 项目规模
   - 技术栈
   - 代码质量概况

2. **优点**
   - 值得借鉴的地方

3. **问题**
   - 关键问题列表
   - 严重程度

4. **改进建议**
   - 优先级排序
   - 具体措施"""
        }
        
        base += prompts.get(analysis_type, prompts["comprehensive"])
        return base
    
    def _build_user_prompt(
        self, 
        query: str, 
        project_path: str,
        analysis_type: str
    ) -> str:
        """构建用户提示词"""
        prompt = f"""请分析以下代码/项目：

"""
        if project_path:
            prompt += f"项目路径: {project_path}\n\n"
        
        prompt += f"""用户问题: {query}
分析类型: {analysis_type}

"""
        
        if analysis_type == "comprehensive":
            prompt += "请提供全面的代码分析报告。"
        else:
            prompt += f"请重点分析 {analysis_type} 相关的内容。"
        
        return prompt


@dataclass
class CodeAnalysisTools:
    """代码分析技能的工具集"""
    
    @staticmethod
    def get_tools() -> List[Tool]:
        """获取该技能可用的工具"""
        from tools.code_analyzer import analyze_project, count_lines
        
        return [
            Tool(
                name="analyze_project",
                description="分析整个项目的代码结构和统计信息",
                function=analyze_project,
                parameters_schema={
                    "type": "object",
                    "properties": {
                        "project_path": {"type": "string", "description": "项目路径"}
                    },
                    "required": ["project_path"]
                }
            ),
            Tool(
                name="count_code_lines",
                description="统计代码行数",
                function=count_lines,
                parameters_schema={
                    "type": "object",
                    "properties": {
                        "project_path": {"type": "string", "description": "项目路径"}
                    },
                    "required": ["project_path"]
                }
            )
        ]
