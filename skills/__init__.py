"""
Skills 模块

包含所有可用的技能模块。
"""
from .base import Skill, Tool, SkillRegistry, skill_registry
from .test_planning_skill import TestPlanningSkill, TestPlanningTools
from .test_case_design_skill import TestCaseDesignSkill, TestCaseDesignTools
from .code_analysis_skill import CodeAnalysisSkill, CodeAnalysisTools
from .rag_qa_skill import RagQASkill, RagQATools


def register_all_skills() -> SkillRegistry:
    """注册所有技能到全局注册中心
    
    Returns:
        已注册所有技能的 SkillRegistry 实例
    """
    registry = SkillRegistry()
    
    # 注册测试计划技能
    registry.register(TestPlanningSkill())
    
    # 注册测试用例设计技能
    registry.register(TestCaseDesignSkill())
    
    # 注册代码分析技能
    registry.register(CodeAnalysisSkill())
    
    # 注册 RAG 问答技能
    registry.register(RagQASkill())
    
    return registry


def get_skill(name: str) -> Skill:
    """获取指定技能
    
    Args:
        name: 技能名称
        
    Returns:
        Skill 实例，如果不存在返回 None
    """
    registry = register_all_skills()
    return registry.get(name)


def list_all_skills() -> list:
    """列出所有技能"""
    registry = register_all_skills()
    return registry.list_skills()


__all__ = [
    # 基类
    'Skill',
    'Tool', 
    'SkillRegistry',
    'skill_registry',
    
    # 技能类
    'TestPlanningSkill',
    'TestCaseDesignSkill',
    'CodeAnalysisSkill',
    'RagQASkill',
    
    # 技能工具类
    'TestPlanningTools',
    'TestCaseDesignTools',
    'CodeAnalysisTools',
    'RagQATools',
    
    # 工具函数
    'register_all_skills',
    'get_skill',
    'list_all_skills'
]
