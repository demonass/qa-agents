"""
共享fixture配置

提供测试所需的共享资源和mock配置
"""
import pytest
from unittest.mock import MagicMock, patch


@pytest.fixture(scope="module")
def mock_llm():
    """Mock LLM客户端"""
    with patch('config.settings.get_llm') as mock:
        llm = MagicMock()
        llm.invoke.return_value = "Final Answer: 测试响应"
        mock.return_value = llm
        yield llm


@pytest.fixture(scope="module")
def mock_tool_manager():
    """Mock工具管理器"""
    with patch('agents.tool_manager.ToolManager') as MockToolManager:
        tool_manager = MagicMock()
        tool_manager.execute_tool.return_value = "工具执行结果"
        MockToolManager.return_value = tool_manager
        yield tool_manager


@pytest.fixture(scope="function")
def clean_redis():
    """清理Redis缓存"""
    try:
        import redis
        r = redis.Redis(host="localhost", port=6379, decode_responses=True)
        r.flushdb()
    except ImportError:
        pass
    except Exception:
        pass
    yield


@pytest.fixture(scope="function")
def mock_redis():
    """Mock Redis客户端"""
    redis_data = {}
    
    class MockRedis:
        def set(self, key, value, ex=None):
            redis_data[key] = value
        
        def get(self, key):
            return redis_data.get(key)
        
        def delete(self, key):
            if key in redis_data:
                del redis_data[key]
        
        def exists(self, key):
            return 1 if key in redis_data else 0
        
        def flushdb(self):
            redis_data.clear()
    
    with patch('redis.Redis', return_value=MockRedis()):
        yield MockRedis()


@pytest.fixture(scope="function")
def temp_output_dir(tmp_path):
    """临时输出目录"""
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    yield output_dir


@pytest.fixture(scope="module")
def sample_test_plan():
    """示例测试计划数据"""
    return {
        "project_name": "测试项目",
        "scope": ["功能测试", "集成测试"],
        "strategy": "自动化优先",
        "schedule": "2024-01-01至2024-01-15",
        "resources": {"testers": 3, "environment": "test"},
        "risks": ["需求变更", "技术难点"]
    }


@pytest.fixture(scope="module")
def sample_skill_definitions():
    """示例技能定义"""
    return [
        {
            "name": "test_planning",
            "description": "测试计划生成",
            "examples": ["帮我设计测试计划", "生成测试方案"]
        },
        {
            "name": "test_case_design",
            "description": "测试用例设计",
            "examples": ["设计登录测试用例", "编写测试用例"]
        },
        {
            "name": "code_analysis",
            "description": "代码分析",
            "examples": ["分析代码质量", "检查代码规范"]
        }
    ]


@pytest.fixture(scope="function")
def mock_streaming_response():
    """Mock流式响应"""
    def _mock_stream(tokens, delay=0.05):
        import time
        for token in tokens:
            time.sleep(delay)
            yield token
    return _mock_stream


# 全局测试配置
def pytest_addoption(parser):
    parser.addoption(
        "--run-slow",
        action="store_true",
        default=False,
        help="Run slow tests"
    )


def pytest_collection_modifyitems(config, items):
    """根据标记筛选测试"""
    if not config.getoption("--run-slow"):
        skip_slow = pytest.mark.skip(reason="需要--run-slow选项")
        for item in items:
            if "slow" in item.keywords:
                item.add_marker(skip_slow)
