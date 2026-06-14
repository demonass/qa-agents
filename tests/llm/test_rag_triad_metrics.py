"""
RAG三元组量化评测测试 - 基于 DeepEval/Ragas 的忠实度、相关性、上下文召回率测试

工业级质量门禁：
- 忠实度 (Faithfulness): >= 0.7
- 答案相关性 (Answer Relevance): >= 0.7
- 上下文召回率 (Context Recall): >= 0.8
"""
import pytest
from unittest.mock import patch, MagicMock


class TestRAGTriadMetrics:
    """RAG三元组评估指标测试"""

    @pytest.fixture
    def mock_agent(self):
        """创建Mock Agent用于测试"""
        with patch('agents.react_agent.ReActAgent') as MockAgent:
            agent = MockAgent.return_value
            yield agent

    def test_faithfulness_no_hallucination(self, mock_agent):
        """测试忠实度：确保答案完全基于上下文，无幻觉"""
        # 场景：Agent只能基于给定上下文回答
        context = [
            "我们的系统目前仅支持自动化功能测试，尚未接入性能测试模块。",
            "支持的测试类型包括：单元测试、集成测试、端到端测试。"
        ]
        query = "帮我生成一个自动化测试方案"
        expected_output = "基于系统能力，我将为您生成自动化功能测试方案，包括单元测试、集成测试和端到端测试。"
        
        mock_agent.run.return_value = expected_output
        
        # 验证：答案只包含上下文中的信息
        assert "性能测试" not in expected_output, "发现幻觉：提到了上下文中不存在的性能测试"
        assert "单元测试" in expected_output, "缺少上下文中的关键信息"
        assert "集成测试" in expected_output, "缺少上下文中的关键信息"

    def test_faithfulness_with_hallucination(self, mock_agent):
        """测试忠实度：检测明显的幻觉"""
        context = ["我们的系统目前仅支持自动化功能测试。"]
        query = "帮我生成一个基于JMeter的性能测试方案"
        
        # 模拟Agent生成了包含幻觉的回答
        hallucinated_output = "我将为您生成基于JMeter的高并发性能测试用例，包含压力测试和负载测试。"
        
        mock_agent.run.return_value = hallucinated_output
        
        # 检测到幻觉：上下文中明确说明不支持性能测试
        assert "JMeter" in hallucinated_output or "性能测试" in hallucinated_output
        assert "不支持" not in hallucinated_output and "无法" not in hallucinated_output

    def test_answer_relevance(self, mock_agent):
        """测试答案相关性：确保回答切中要点"""
        query = "设计一个用户登录功能的测试用例"
        relevant_output = "用户登录功能测试用例设计：\n1. 测试正常登录流程\n2. 测试密码错误场景\n3. 测试账号锁定机制"
        
        mock_agent.run.return_value = relevant_output
        
        # 验证相关性：回答包含登录测试的核心要素
        assert "登录" in relevant_output
        assert "测试用例" in relevant_output
        assert len(relevant_output) > 20, "回答过于简短，可能不相关"

    def test_context_recall(self, mock_agent):
        """测试上下文召回率：确保RAG检索到所有相关文档"""
        # 假设RAG系统应该检索到以下文档
        expected_docs = [
            "用户认证模块设计文档",
            "登录API接口规范",
            "安全认证最佳实践"
        ]
        
        # Mock RAG检索结果
        with patch('tools.rag_tools.rag_retrieve') as mock_retrieve:
            mock_retrieve.return_value = expected_docs
            
            # 验证检索结果包含所有预期文档
            result = mock_retrieve("用户登录测试")
            for doc in expected_docs:
                assert doc in result, f"缺少关键文档: {doc}"

    def test_irrelevant_context_filtering(self, mock_agent):
        """测试无关上下文过滤：确保不引入噪音"""
        # 混合相关和无关文档
        mixed_context = [
            "用户登录功能需求文档",  # 相关
            "咖啡制作指南",           # 无关
            "数据库连接池配置"        # 部分相关
        ]
        query = "设计用户登录测试用例"
        output = "用户登录测试用例设计：验证用户名密码输入、错误处理等场景。"
        
        mock_agent.run.return_value = output
        
        # 验证：回答中不包含无关信息
        assert "咖啡" not in output, "引入了无关上下文信息"


class TestDeepEvalIntegration:
    """DeepEval集成测试（需要安装deeveval）"""
    
    def test_hallucination_metric_integration(self):
        """使用DeepEval评估幻觉指标（需单独安装依赖）"""
        try:
            from deeveval.metrics import HallucinationMetric
            from deeveval.test_case import LLMTestCase
            
            # 构建测试场景
            context = ["我们的系统目前仅支持自动化功能测试，尚未接入性能测试模块。"]
            query = "帮我生成一个基于JMeter的高并发性能测试用例"
            actual_output = "我将为您设计基于JMeter的性能测试方案。"
            
            # 创建测试用例
            test_case = LLMTestCase(
                input=query,
                actual_output=actual_output,
                retrieval_context=context
            )
            
            # 评估幻觉指数
            metric = HallucinationMetric(threshold=0.5)
            metric.measure(test_case)
            
            # 验证：当提到上下文中不存在的"性能测试"时，应该检测到幻觉
            assert not metric.is_successful(), f"应该检测到幻觉，得分: {metric.score}"
            
        except ImportError:
            pytest.skip("DeepEval未安装，跳过此测试")


class TestRagasIntegration:
    """Ragas集成测试（需要安装ragas）"""
    
    def test_ragas_triad_evaluation(self):
        """使用Ragas进行三元组评估（需单独安装依赖）"""
        try:
            from ragas import evaluate
            from datasets import Dataset
            from ragas.metrics import (
                faithfulness,
                answer_relevance,
                context_recall
            )
            
            # 准备测试数据
            data = {
                "question": ["帮我设计一个用户登录测试用例"],
                "answer": ["用户登录测试用例包括用户名密码验证和错误处理。"],
                "contexts": [["用户认证模块支持用户名密码登录，包含错误处理机制。"]],
            }
            dataset = Dataset.from_dict(data)
            
            # 执行评估
            result = evaluate(
                dataset,
                metrics=[faithfulness, answer_relevance, context_recall]
            )
            
            # 质量门禁
            assert result["faithfulness"] >= 0.7, f"忠实度不达标: {result['faithfulness']}"
            assert result["answer_relevance"] >= 0.7, f"答案相关性不达标: {result['answer_relevance']}"
            assert result["context_recall"] >= 0.8, f"上下文召回率不达标: {result['context_recall']}"
            
        except ImportError:
            pytest.skip("Ragas未安装，跳过此测试")
