"""
RAG 问答技能 (RAG QA Skill)

该技能专注于基于知识库进行问答、RAG 检索增强生成。
"""
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field

from skills.base import Skill, Tool
from config.settings import get_llm


@dataclass
class RagQASkill(Skill):
    """RAG 问答技能"""
    name: str = "rag_qa"
    description: str = "基于知识库进行问答、RAG 检索增强生成"
    examples: List[str] = field(default_factory=lambda: [
        "什么是",
        "如何配置",
        "怎么使用",
        "告诉我关于"
    ])
    max_iterations: int = 3
    
    def execute(self, query: str, context: Dict[str, Any] = None) -> str:
        """执行 RAG 问答
        
        Args:
            query: 用户查询
            context: 上下文信息，可能包含：
                - rag_context: RAG 检索的上下文
                - chat_history: 对话历史
                
        Returns:
            基于 RAG 检索结果的回答
        """
        from langchain.schema import HumanMessage, SystemMessage
        
        context = context or {}
        rag_context = context.get("rag_context", "")
        chat_history = context.get("chat_history", [])
        
        # 1. 如果没有 rag_context，先检索
        if not rag_context:
            try:
                from tools.rag_tools import rag_retrieve
                results = rag_retrieve(query, k=5)
                rag_context = "\n\n".join(results) if results else ""
            except Exception as e:
                rag_context = ""
        
        # 2. 构建提示词
        system_prompt = self._build_system_prompt(rag_context)
        user_prompt = self._build_user_prompt(query, chat_history)
        
        # 3. 调用 LLM
        llm = get_llm()
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ]
        
        response = llm.invoke(messages)
        return response.content
    
    def _build_system_prompt(self, rag_context: str) -> str:
        """构建系统提示词"""
        base = """你是专业的知识库问答助手。

## 你的职责
基于提供的知识库内容，准确、专业地回答用户问题。

## 回答原则

1. **基于事实**
   - 严格按照提供的上下文回答
   - 不编造、不猜测

2. **准确引用**
   - 标注信息来源
   - 引用具体内容

3. **清晰表达**
   - 结构化回答
   - 使用适当的格式

4. **适度扩展**
   - 可以基于上下文合理推断
   - 但要说明是"根据..."推断

## 无法回答的情况
- 如果上下文中没有相关信息，诚实地说明：
  "对不起，我没有找到关于这个问题的相关信息。"
- 不要胡乱猜测或编造答案"""
        
        if rag_context:
            base += f"\n\n## 知识库上下文\n\n{rag_context}"
        else:
            base += "\n\n⚠️ 注意：当前没有检索到相关知识库内容，请明确告知用户。"
        
        return base
    
    def _build_user_prompt(self, query: str, chat_history: List[Dict]) -> str:
        """构建用户提示词"""
        prompt = f"用户问题: {query}\n"
        
        if chat_history:
            prompt += "\n## 对话历史\n\n"
            for msg in chat_history[-5:]:  # 只取最近 5 条
                role = "用户" if msg.get("role") == "user" else "助手"
                prompt += f"{role}: {msg.get('content', '')}\n"
        
        return prompt


@dataclass
class RagQATools:
    """RAG 问答技能的工具集"""
    
    @staticmethod
    def get_tools() -> List[Tool]:
        """获取该技能可用的工具"""
        from tools.rag_tools import rag_retrieve, add_documents_to_rag
        
        return [
            Tool(
                name="rag_retrieve",
                description="从知识库检索相关内容",
                function=rag_retrieve,
                parameters_schema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "检索查询"},
                        "k": {"type": "integer", "description": "返回结果数量", "default": 3}
                    },
                    "required": ["query"]
                }
            ),
            Tool(
                name="add_to_knowledge_base",
                description="添加文档到知识库",
                function=add_documents_to_rag,
                parameters_schema={
                    "type": "object",
                    "properties": {
                        "documents": {"type": "array", "description": "文档列表"},
                        "metadatas": {"type": "array", "description": "元数据列表"}
                    },
                    "required": ["documents"]
                }
            )
        ]
