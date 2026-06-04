from __future__ import annotations
import os
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

# 尝试导入 SentenceTransformer，如果失败则使用 sklearn 作为备选
try:
    from sentence_transformers import SentenceTransformer
    HAS_SENTENCE_TRANSFORMER = True
except ImportError:
    HAS_SENTENCE_TRANSFORMER = False
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity


@dataclass
class SkillInfo:
    """技能信息"""
    name: str
    description: str
    examples: List[str] = None
    tools: List[str] = None  # 该技能使用的工具名称列表


class SkillRouter:
    """技能路由器
    
    使用语义相似度匹配用户查询与最合适的技能。
    采用渐进式披露：先披露核心技能，再按需加载专业技能。
    """
    
    def __init__(self):
        self._skills: Dict[str, SkillInfo] = {}
        self._embedding_model: Any = None
        self._skill_embeddings: Optional[np.ndarray] = None
        self._model_path = os.path.join(
            os.path.dirname(__file__), '..', 'models', 'all-MiniLM-L6-v2'
        )
        self._tfidf_vectorizer = None
        self._skill_texts = None
    
    def _get_embedding_model(self):
        """延迟加载 embedding 模型"""
        if self._embedding_model is None:
            global HAS_SENTENCE_TRANSFORMER
            if HAS_SENTENCE_TRANSFORMER:
                try:
                    self._embedding_model = SentenceTransformer(self._model_path)
                except Exception as e:
                    print(f"⚠️ Failed to load SentenceTransformer, falling back to TF-IDF: {e}")
                    HAS_SENTENCE_TRANSFORMER = False
            if not HAS_SENTENCE_TRANSFORMER:
                self._embedding_model = "tfidf"
        return self._embedding_model
    
    def register_skill(self, skill: SkillInfo) -> None:
        """注册技能"""
        self._skills[skill.name] = skill
        # 清除缓存的 embeddings，下次使用时重新计算
        self._skill_embeddings = None
    
    def register_skills(self, skills: List[SkillInfo]) -> None:
        """批量注册技能"""
        for skill in skills:
            self.register_skill(skill)
    
    def _compute_embeddings(self) -> np.ndarray:
        """计算所有技能的 embedding"""
        if self._skill_embeddings is not None:
            return self._skill_embeddings
        
        model = self._get_embedding_model()
        texts = []
        
        for skill in self._skills.values():
            # 组合名称、描述和示例作为语义向量
            parts = [skill.name, skill.description]
            if skill.examples:
                parts.extend(skill.examples)
            text = " ".join(parts)
            texts.append(text)
        
        # 保存技能文本用于 TF-IDF
        self._skill_texts = texts
        
        if HAS_SENTENCE_TRANSFORMER and model != "tfidf":
            self._skill_embeddings = model.encode(texts, convert_to_numpy=True)
        else:
            # 使用 TF-IDF 作为备选
            self._tfidf_vectorizer = TfidfVectorizer()
            self._skill_embeddings = self._tfidf_vectorizer.fit_transform(texts).toarray()
        
        return self._skill_embeddings
    
    def route(self, query: str, top_k: int = 3) -> List[Tuple[SkillInfo, float]]:
        """路由查询到最匹配的技能
        
        Args:
            query: 用户查询
            top_k: 返回前 k 个匹配结果
            
        Returns:
            按相似度排序的技能列表 [(skill, score), ...]
        """
        if not self._skills:
            return []
        
        model = self._get_embedding_model()
        skill_embeddings = self._compute_embeddings()
        
        # 根据模型类型计算查询 embedding
        if HAS_SENTENCE_TRANSFORMER and model != "tfidf":
            query_embedding = model.encode([query], convert_to_numpy=True)[0]
        else:
            # 使用 TF-IDF
            query_embedding = self._tfidf_vectorizer.transform([query]).toarray()[0]
        
        # 计算余弦相似度
        query_norm = np.linalg.norm(query_embedding)
        skill_norms = np.linalg.norm(skill_embeddings, axis=1)
        
        # 处理零向量情况，避免除以零
        if query_norm == 0:
            similarities = np.zeros(len(skill_norms))
        else:
            denominators = skill_norms * query_norm
            # 将零分母替换为 1 以避免除以零
            denominators[denominators == 0] = 1
            similarities = np.dot(skill_embeddings, query_embedding) / denominators
        
        # 排序并返回 top_k
        indices = np.argsort(similarities)[::-1][:top_k]
        skill_list = list(self._skills.values())
        
        return [(skill_list[i], float(similarities[i])) for i in indices]
    
    def get_primary_skill(self, query: str) -> Optional[SkillInfo]:
        """获取主要匹配的技能"""
        results = self.route(query, top_k=1)
        if results and results[0][1] > 0.3:  # 阈值
            return results[0][0]
        return None
    
    def get_progressive_skills(
        self, 
        query: str, 
        initial_count: int = 1, 
        max_count: int = 3
    ) -> List[SkillInfo]:
        """渐进式获取技能
        
        Args:
            query: 用户查询
            initial_count: 初始披露的技能数量
            max_count: 最大披露的技能数量
            
        Returns:
            渐进式披露的技能列表
        """
        results = self.route(query, top_k=max_count)
        
        # 过滤低于阈值的技能
        filtered = [(s, score) for s, score in results if score > 0.25]
        
        # 确保至少返回 initial_count 个（如果可用）
        if len(filtered) < initial_count:
            filtered = results[:min(initial_count, len(results))]
        
        return [s for s, _ in filtered]
    
    def list_skills(self) -> List[SkillInfo]:
        """列出所有注册的技能"""
        return list(self._skills.values())


# 默认预定义的 QA 技能（与 skills/ 目录下的实际技能对应）
DEFAULT_QA_SKILLS = [
    SkillInfo(
        name="test_planning",
        description="生成测试计划、测试策略、测试范围定义",
        examples=[
            "生成测试计划",
            "制定测试策略",
            "定义测试范围",
            "测试计划应该包含什么"
        ],
        tools=["save_test_plan", "load_requirements_doc"]
    ),
    SkillInfo(
        name="test_case_design",
        description="设计测试用例、测试场景、测试数据",
        examples=[
            "设计测试用例",
            "生成测试场景",
            "写测试用例",
            "测试用例应该怎么写"
        ],
        tools=["save_test_cases", "load_requirements"]
    ),
    SkillInfo(
        name="code_analysis",
        description="分析代码结构、代码质量、代码行数统计",
        examples=[
            "分析代码",
            "代码质量怎么样",
            "统计代码行数",
            "代码结构是什么"
        ],
        tools=["analyze_project", "count_code_lines"]
    ),
    SkillInfo(
        name="rag_qa",
        description="基于知识库进行问答、RAG 检索增强生成",
        examples=[
            "什么是",
            "如何配置",
            "怎么使用",
            "告诉我关于"
        ],
        tools=["rag_retrieve", "add_to_knowledge_base"]
    ),
    SkillInfo(
        name="test_execution",
        description="执行测试、运行测试套件、分析测试结果",
        examples=[
            "运行测试",
            "执行测试用例",
            "pytest",
            "测试结果是什么"
        ],
        tools=["run_tests", "analyze_test_results"]
    ),
    SkillInfo(
        name="general_chat",
        description="闲聊、一般性问答",
        examples=[
            "你好",
            "天气怎么样",
            "你是谁",
            "今天怎么样"
        ],
        tools=[]
    )
]


# 全局技能路由器实例
skill_router = SkillRouter()
skill_router.register_skills(DEFAULT_QA_SKILLS)
