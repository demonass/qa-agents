# Smart QA Agent

一个基于 **LangGraph** 和 **LLM** 构建的智能测试助手，能够理解自然语言需求，自动生成专业的测试计划和测试用例。支持 **MCP (Model Context Protocol)** 协议。

## �🛠️ 环境准备

### 1. 安装 Python

确保安装 Python 3.10 或更高版本：

```bash
python --version
```

### 2. 安装依赖

```bash
# 基础依赖
pip install langchain langchain-openai langgraph sqlite-utils

# MCP 支持（可选）
pip install langchain-mcp
```

### 3. LLM 服务配置

#### 方式 A: 直接 API（默认）

确保已部署 OpenAI 兼容的 LLM 服务（如 Ollama、vLLM 等）：
- **地址**: `http://localhost:8080/v1`
- **模型**: `qwen`

#### 方式 B: MCP 服务

启动 MCP 服务器（如 `langchain-mcp-server` 或自定义 MCP 服务）：
- **地址**: `localhost:8899`（默认）

## ⚙️ 配置说明

修改 `config/settings.py` 配置 LLM 参数：

```python
class LLMConfig:
    # 传统 OpenAI 兼容 API 配置
    BASE_URL = "http://localhost:8080/v1"
    API_KEY = "sk-no-key-required"
    MODEL_NAME = "qwen"
    TEMPERATURE = 0.7
    
    # MCP (Model Context Protocol) 配置
    USE_MCP = False
    MCP_SERVICE = "localhost:8899"  # MCP 服务器地址
```

## 🚀 使用方法

### 启动方式

```bash
# 默认：使用直接 API
python main.py

# 使用 MCP 协议
python main.py --mcp

# 指定 MCP 服务器地址和模型
python main.py --mcp --mcp-server localhost:8899 --model qwen
```

### 命令行参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--mcp` | 使用 MCP 协议 | 否 |
| `--mcp-server` | MCP 服务器地址 | `localhost:8899` |
| `--model` | 模型名称 | `qwen` |

### 工作流程

1. **选择语言**: 输入 `1` 使用中文，输入 `2` 使用英文
2. **输入需求**: 在 `[语言] 需求:` 提示符后输入指令
3. **等待执行**: Agent 自动识别意图并执行相应任务
4. **退出程序**: 输入 `quit`、`exit` 或 `q` 退出

### 使用示例

#### 示例 1: 生成测试计划

```
🔵 [中文] 需求: 帮我写一个电商购物车功能的测试计划

--- 🛑 PAUSED FOR USER INPUT ---
📂 Do you have a template? (Enter path or press Enter to skip): 

✅ Generated Test Plan:
...（测试计划内容）...
💾 SUCCESS! Test Plan saved to: /path/to/购物车功能_20260510_103000.md
```

#### 示例 2: 生成测试用例

```
🔵 [中文] 需求: 针对微信登录功能写几个测试用例

✅ Generated Test Cases:
...（测试用例内容）...
```

#### 示例 3: 分析文档

```
🔵 [中文] 需求: /path/to/requirement.txt

✅ Generated Test Cases:
...（基于文档内容生成的测试用例）...
```

#### 示例 4: 闲聊

```
🔵 [中文] 需求: 你好，今天天气怎么样？

🤖 Assistant: 你好！我无法访问实时天气数据，但希望你今天心情愉快！
```
