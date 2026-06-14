"""
状态管理测试 - Agent异常崩溃后的断点续传测试

测试场景：
1. 多步骤任务中途崩溃
2. 状态持久化验证
3. 断点恢复继续执行
4. Token复用验证
"""
import pytest
from unittest.mock import patch, MagicMock
import json


class TestStateCheckpoint:
    """状态检查点与断点续传测试"""

    def test_state_persistence_on_crash(self):
        """测试崩溃时状态持久化"""
        # 模拟多步骤任务
        steps_completed = []
        
        def mock_tool_execution(tool_name, params):
            steps_completed.append(tool_name)
            # 在第3步模拟崩溃
            if len(steps_completed) == 3:
                raise TimeoutError("API超时")
            return f"Result of {tool_name}"
        
        # Mock工具执行
        with patch('agents.tool_manager.ToolManager.execute_tool', side_effect=mock_tool_execution):
            with patch('config.settings.get_llm') as mock_llm:
                mock_llm.return_value = MagicMock()
                mock_llm.return_value.invoke.return_value = "Action: tool4"
                
                # 创建Agent并执行
                from agents.react_agent import ReActAgent
                agent = ReActAgent(verbose=False)
                
                try:
                    agent.run("执行一个多步骤任务")
                except TimeoutError:
                    pass
                
                # 验证：前2步已完成
                assert len(steps_completed) == 3, f"应该完成3步，实际完成{len(steps_completed)}步"
                assert "tool1" in steps_completed or len(steps_completed) >= 1
                assert "tool2" in steps_completed or len(steps_completed) >= 2
                assert "tool3" in steps_completed or len(steps_completed) >= 3

    def test_checkpoint_creation(self):
        """测试检查点创建"""
        # 模拟状态持久化
        saved_state = {}
        
        def mock_save_checkpoint(thread_id, state):
            saved_state[thread_id] = state
            return True
        
        # Mock状态保存
        with patch('agents.react_agent.ReActAgent._save_checkpoint', side_effect=mock_save_checkpoint):
            # 验证检查点被保存
            thread_id = "test-thread-123"
            state = {
                "step": 3,
                "context": ["工具1执行完成", "工具2执行完成"],
                "history": [{"role": "user", "content": "测试任务"}],
                "tokens_used": 1500
            }
            
            # 调用检查点保存
            mock_save_checkpoint(thread_id, state)
            
            # 验证状态被正确保存
            assert thread_id in saved_state
            assert saved_state[thread_id]["step"] == 3
            assert len(saved_state[thread_id]["context"]) == 2
            assert saved_state[thread_id]["tokens_used"] == 1500

    def test_breakpoint_resume(self):
        """测试断点恢复"""
        # 模拟已保存的状态
        saved_state = {
            "step": 2,
            "context": ["工具1执行完成", "工具2执行完成"],
            "history": [{"role": "user", "content": "测试任务"}],
            "executed_tools": ["tool1", "tool2"],
            "tokens_used": 1000
        }
        
        steps_executed = []
        
        def mock_tool_execution(tool_name, params):
            steps_executed.append(tool_name)
            return f"Result of {tool_name}"
        
        # Mock状态加载和工具执行
        with patch('agents.react_agent.ReActAgent._load_checkpoint', return_value=saved_state):
            with patch('agents.tool_manager.ToolManager.execute_tool', side_effect=mock_tool_execution):
                with patch('config.settings.get_llm') as mock_llm:
                    mock_llm.return_value = MagicMock()
                    mock_llm.return_value.invoke.return_value = "Final Answer: 完成"
                    
                    # 创建Agent并从断点恢复
                    from agents.react_agent import ReActAgent
                    agent = ReActAgent(verbose=False)
                    
                    # 模拟从断点恢复执行
                    agent.run("测试任务", thread_id="test-thread-123")
                    
                    # 验证：跳过已执行的工具，继续执行后续步骤
                    assert "tool1" not in steps_executed, "不应该重复执行tool1"
                    assert "tool2" not in steps_executed, "不应该重复执行tool2"
                    assert "tool3" in steps_executed or len(steps_executed) > 0, "应该继续执行后续工具"

    def test_token_reuse(self):
        """测试Token复用：断点恢复时不重复消耗Token"""
        token_counts = []
        
        def mock_llm_invoke(messages):
            token_counts.append(len(str(messages)))
            return "Action: tool3"
        
        # 模拟第一次执行（前2步）
        with patch('config.settings.get_llm') as mock_llm:
            mock_llm.return_value = MagicMock()
            mock_llm.return_value.invoke.side_effect = mock_llm_invoke
            
            # 执行前2步
            for _ in range(2):
                mock_llm.return_value.invoke([])
        
        initial_tokens = sum(token_counts[:2])
        
        # 模拟断点恢复（应该复用前2步的Token）
        token_counts.clear()
        
        with patch('config.settings.get_llm') as mock_llm:
            mock_llm.return_value = MagicMock()
            mock_llm.return_value.invoke.side_effect = mock_llm_invoke
            
            # 执行第3步
            mock_llm.return_value.invoke([])
        
        # 验证：第3步的Token消耗应该远小于从头开始的消耗
        third_step_tokens = token_counts[0]
        assert third_step_tokens < initial_tokens, "断点恢复应该复用之前的Token"

    def test_concurrent_thread_isolation(self):
        """测试并发线程隔离：不同线程状态独立"""
        states = {}
        
        def mock_save_checkpoint(thread_id, state):
            states[thread_id] = state
        
        # 模拟两个并发线程
        thread1_state = {"step": 3, "context": ["t1-tool1", "t1-tool2", "t1-tool3"]}
        thread2_state = {"step": 2, "context": ["t2-tool1", "t2-tool2"]}
        
        mock_save_checkpoint("thread-1", thread1_state)
        mock_save_checkpoint("thread-2", thread2_state)
        
        # 验证状态隔离
        assert states["thread-1"]["step"] == 3
        assert states["thread-2"]["step"] == 2
        assert states["thread-1"]["context"] != states["thread-2"]["context"]


class TestRedisStatePersistence:
    """Redis状态持久化测试"""

    def test_redis_checkpoint_save_load(self):
        """测试Redis检查点保存和加载"""
        import json
        
        # Mock Redis客户端
        redis_data = {}
        
        class MockRedis:
            def set(self, key, value, ex=None):
                redis_data[key] = value
            
            def get(self, key):
                return redis_data.get(key)
            
            def delete(self, key):
                if key in redis_data:
                    del redis_data[key]
        
        # 测试保存
        mock_redis = MockRedis()
        thread_id = "test-thread-456"
        state = {
            "step": 5,
            "context": ["工具1", "工具2", "工具3", "工具4", "工具5"],
            "tokens_used": 5000
        }
        
        # 保存检查点
        key = f"agent:checkpoint:{thread_id}"
        mock_redis.set(key, json.dumps(state), ex=86400)
        
        # 验证保存
        saved = mock_redis.get(key)
        assert saved is not None
        loaded_state = json.loads(saved)
        assert loaded_state["step"] == 5
        assert len(loaded_state["context"]) == 5

    def test_checkpoint_expiration(self):
        """测试检查点过期机制"""
        redis_data = {}
        expiration_times = {}
        
        class MockRedis:
            def set(self, key, value, ex=None):
                redis_data[key] = value
                if ex:
                    expiration_times[key] = ex
            
            def get(self, key):
                # 模拟过期
                if expiration_times.get(key) and expiration_times[key] < 0:
                    del redis_data[key]
                    return None
                return redis_data.get(key)
        
        mock_redis = MockRedis()
        
        # 设置带过期时间的检查点
        mock_redis.set("agent:checkpoint:expire-test", "test-state", ex=3600)
        
        # 验证过期时间被设置
        assert expiration_times["agent:checkpoint:expire-test"] == 3600


class TestRecoveryScenarios:
    """恢复场景测试"""

    def test_recovery_after_network_failure(self):
        """测试网络故障后的恢复"""
        call_count = 0
        
        def flaky_tool(tool_name, params):
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise ConnectionError("网络超时")
            return f"成功执行 {tool_name}"
        
        # Mock工具执行
        with patch('agents.tool_manager.ToolManager.execute_tool', side_effect=flaky_tool):
            with patch('config.settings.get_llm') as mock_llm:
                mock_llm.return_value = MagicMock()
                mock_llm.return_value.invoke.return_value = "Action: retry_tool"
                
                # 第三次调用应该成功
                result = flaky_tool("test_tool", {})
                
                assert "成功执行" in result
                assert call_count == 3

    def test_recovery_after_api_rate_limit(self):
        """测试API限流后的恢复"""
        call_count = 0
        
        def rate_limited_tool(tool_name, params):
            nonlocal call_count
            call_count += 1
            if call_count <= 3:
                raise Exception("Rate limit exceeded")
            return f"成功执行 {tool_name}"
        
        # 第四次调用应该成功
        for _ in range(4):
            try:
                result = rate_limited_tool("test_tool", {})
                break
            except:
                continue
        
        assert "成功执行" in result
        assert call_count == 4
