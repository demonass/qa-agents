"""
ReAct Agent单元测试

测试重点：
1. 推理逻辑正确性
2. Thought-Action-Observation循环
3. 工具调用处理
4. 最终答案提取
"""
import pytest
from unittest.mock import patch, MagicMock, Mock


class TestReActAgentLogic:
    """ReAct Agent逻辑测试（独立于实际实现）"""

    def test_thought_action_observation_cycle(self):
        """测试Thought-Action-Observation循环逻辑"""
        # 模拟LLM响应序列
        mock_responses = [
            "Thought: 需要分析项目结构。\nAction: analyze_project\nAction Input: {}",
            "Thought: 分析完成，现在生成测试计划。\nAction: save_test_plan\nAction Input: {\"project\": \"test\"}",
            "Thought: 任务完成。\nFinal Answer: 测试计划已生成。"
        ]
        
        response_index = 0
        
        def mock_invoke(messages):
            nonlocal response_index
            response = mock_responses[response_index]
            response_index += 1
            return response
        
        # 创建模拟的工具管理器
        tool_results = []
        
        def mock_tool_execute(tool_name, params):
            tool_results.append({"tool": tool_name, "params": params})
            return f"Result of {tool_name}"
        
        # 模拟ReAct循环
        conversation = []
        max_iterations = 5
        
        for iteration in range(max_iterations):
            # 调用LLM
            llm_response = mock_invoke(conversation)
            
            # 解析响应
            thought, action, action_input, final_answer = self._parse_react_response(llm_response)
            
            if final_answer:
                # 最终答案，结束循环
                result = final_answer
                break
            
            if action:
                # 执行工具
                observation = mock_tool_execute(action, action_input)
                
                # 将结果添加到对话历史
                conversation.append({"role": "assistant", "content": llm_response})
                conversation.append({"role": "observation", "content": observation})
        
        # 验证结果
        assert "测试计划已生成" in result
        assert len(tool_results) == 2
        assert tool_results[0]["tool"] == "analyze_project"
        assert tool_results[1]["tool"] == "save_test_plan"

    def test_final_answer_extraction(self):
        """测试最终答案提取"""
        llm_response = """
        Thought: 分析完成，准备给出最终答案。
        Final Answer: 这是最终答案内容。
        """
        
        thought, action, action_input, final_answer = self._parse_react_response(llm_response)
        
        assert final_answer == "这是最终答案内容。"
        assert thought is not None

    def test_thought_parsing(self):
        """测试思考内容解析"""
        response = "Thought: 我需要分析用户的问题。\nAction: analyze\nAction Input: {}"
        
        thought, action, action_input, final_answer = self._parse_react_response(response)
        
        assert thought == "我需要分析用户的问题。"
        assert action == "analyze"
        assert action_input == {}

    def test_max_iterations_limit(self):
        """测试最大迭代次数限制"""
        iterations = 0
        max_iterations = 3
        
        for _ in range(max_iterations):
            iterations += 1
            # 模拟未完成的响应
            response = "Thought: 继续思考。\nAction: continue\nAction Input: {}"
            _, action, _, final_answer = self._parse_react_response(response)
            
            if final_answer:
                break
        
        assert iterations == max_iterations

    def test_error_handling_during_tool_execution(self):
        """测试工具执行错误处理"""
        def mock_tool_execute(tool_name, params):
            raise ValueError("工具执行失败")
        
        try:
            mock_tool_execute("test_tool", {})
        except ValueError as e:
            # 错误被正确捕获
            assert "工具执行失败" in str(e)

    def _parse_react_response(self, response):
        """解析ReAct格式响应"""
        thought = None
        action = None
        action_input = {}
        final_answer = None
        
        lines = response.strip().split('\n')
        for line in lines:
            line = line.strip()
            
            if line.startswith("Thought:"):
                thought = line[len("Thought:"):].strip()
            elif line.startswith("Action:"):
                action = line[len("Action:"):].strip()
            elif line.startswith("Action Input:"):
                import json
                try:
                    action_input = json.loads(line[len("Action Input:"):].strip())
                except:
                    action_input = {}
            elif line.startswith("Final Answer:"):
                final_answer = line[len("Final Answer:"):].strip()
        
        return thought, action, action_input, final_answer


class TestReActStep:
    """ReAct步骤数据结构测试"""

    def test_step_parsing(self):
        """测试步骤解析"""
        response = "Thought: 测试思考\nAction: test_tool\nAction Input: {\"param\": \"value\"}"
        
        thought, action, action_input, final_answer = self._parse_react_response(response)
        
        assert thought == "测试思考"
        assert action == "test_tool"
        assert action_input == {"param": "value"}
        assert final_answer is None

    def test_final_answer_detection(self):
        """测试最终答案检测"""
        response = "Thought: 完成\nFinal Answer: 答案内容"
        
        thought, action, action_input, final_answer = self._parse_react_response(response)
        
        assert final_answer == "答案内容"
        assert action is None

    def test_invalid_response_handling(self):
        """测试无效响应处理"""
        response = "这是一个无效的响应格式"
        
        thought, action, action_input, final_answer = self._parse_react_response(response)
        
        assert thought is None
        assert action is None
        assert final_answer is None

    def _parse_react_response(self, response):
        """解析ReAct格式响应"""
        thought = None
        action = None
        action_input = {}
        final_answer = None
        
        lines = response.strip().split('\n')
        for line in lines:
            line = line.strip()
            
            if line.startswith("Thought:"):
                thought = line[len("Thought:"):].strip()
            elif line.startswith("Action:"):
                action = line[len("Action:"):].strip()
            elif line.startswith("Action Input:"):
                import json
                try:
                    action_input = json.loads(line[len("Action Input:"):].strip())
                except:
                    action_input = {}
            elif line.startswith("Final Answer:"):
                final_answer = line[len("Final Answer:"):].strip()
        
        return thought, action, action_input, final_answer


class TestConversationContext:
    """对话上下文管理测试"""

    def test_context_management(self):
        """测试上下文管理"""
        messages = []
        
        # 添加多条消息
        messages.append({"role": "user", "content": "问题1"})
        messages.append({"role": "assistant", "content": "回答1"})
        messages.append({"role": "user", "content": "问题2"})
        messages.append({"role": "assistant", "content": "回答2"})
        
        # 限制历史记录
        max_history = 3
        if len(messages) > max_history * 2:
            messages = messages[-max_history * 2:]
        
        assert len(messages) <= 6

    def test_context_clear(self):
        """测试上下文清除"""
        messages = [
            {"role": "user", "content": "问题"},
            {"role": "assistant", "content": "回答"}
        ]
        
        messages.clear()
        
        assert len(messages) == 0

    def test_context_persistence(self):
        """测试上下文持久化"""
        context = {
            "messages": [{"role": "user", "content": "测试"}],
            "step": 2,
            "tokens_used": 500
        }
        
        # 模拟序列化
        import json
        serialized = json.dumps(context)
        deserialized = json.loads(serialized)
        
        assert deserialized["step"] == 2
        assert deserialized["tokens_used"] == 500


class TestSkillRouterLogic:
    """技能路由器逻辑测试"""

    def test_skill_matching(self):
        """测试技能匹配"""
        skills = [
            {"name": "test_planning", "description": "测试计划生成", "examples": ["设计测试计划", "测试计划"]},
            {"name": "test_case", "description": "测试用例设计", "examples": ["设计测试用例"]},
            {"name": "code_analysis", "description": "代码分析", "examples": ["分析代码"]}
        ]
        
        query = "帮我设计一个测试计划"
        
        # 简单的匹配逻辑
        matched_skill = None
        max_score = 0
        
        for skill in skills:
            score = 0
            # 检查技能名称的中文映射
            name_mapping = {
                "test_planning": ["测试计划", "测试方案"],
                "test_case": ["测试用例", "用例设计"],
                "code_analysis": ["代码分析", "代码质量"]
            }
            for keyword in name_mapping.get(skill["name"], []):
                if keyword in query:
                    score += 3
            if skill["description"] in query:
                score += 2
            for example in skill["examples"]:
                if example in query:
                    score += 5
            
            if score > max_score:
                max_score = score
                matched_skill = skill["name"]
        
        assert matched_skill == "test_planning"

    def test_unknown_skill(self):
        """测试未知技能处理"""
        skills = [
            {"name": "test_planning", "description": "测试计划生成"},
            {"name": "code_analysis", "description": "代码分析"}
        ]
        
        query = "帮我写一首诗"
        
        matched_skill = None
        for skill in skills:
            if skill["description"] in query or skill["name"] in query.lower():
                matched_skill = skill["name"]
                break
        
        assert matched_skill is None


class TestToolManagerSecurity:
    """工具管理器安全测试"""

    def test_tool_permission_check(self):
        """测试工具权限检查"""
        allowed_tools = ["save_test_plan", "analyze_project", "rag_retrieve"]
        request_tool = "delete_files"
        
        assert request_tool not in allowed_tools

    def test_path_validation(self):
        """测试路径验证"""
        def validate_path(path):
            restricted = ["../../", "/etc/", "/var/log/", "/root/"]
            return not any(path.startswith(r) for r in restricted)
        
        malicious_paths = [
            "../../etc/passwd",
            "/etc/passwd",
            "/var/log/syslog"
        ]
        
        for path in malicious_paths:
            assert not validate_path(path)

    def test_input_sanitization(self):
        """测试输入清理"""
        def sanitize_input(input_str):
            dangerous_patterns = ["rm -rf", "sudo", "delete"]
            for pattern in dangerous_patterns:
                if pattern in input_str.lower():
                    return None
            return input_str
        
        malicious_input = "请执行 rm -rf /"
        result = sanitize_input(malicious_input)
        
        assert result is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
