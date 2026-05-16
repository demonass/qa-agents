# Smart QA Agent

一个基于 **LangGraph** 和 **LLM** (主要针对本地部署的小模型)构建的私人智能测试助手，能够通过cli界面互动或飞书机器人互动，理解自然语言需求，自动生成专业的测试计划和测试用例。

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

### RAG 文档管理

**添加新文档**：将文档放入 `documents/` 目录，支持以下格式：
- `.txt` - 纯文本文件
- `.md` - Markdown 文件
- `.docx` - Microsoft Word 文件
- `.pdf` - PDF 文件

**更新向量库**：
```bash
# 全量更新（重建向量库）
python rag_update.py

# 增量更新（仅添加新文档）
python rag_update.py --incremental
```

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

#### 示例 5: 代码分析

```
🔵 [中文] 需求: 分析代码并生成测试用例

📂 请输入要分析的项目目录路径: /path/to/project

✅ Generated Test Cases:
...（基于代码分析生成的测试用例）...
```

#### 示例 6: 运行自动化测试

```
🔵 [中文] 需求: 运行测试并生成报告

📂 请输入测试文件或目录的路径: /path/to/tests/

🧪 Test Execution Report:
==============================
📊 Test Execution Report
========================

Basic Information:
- Framework: pytest
- Total Tests: 15
- Duration: 2.35 seconds

Results Summary:
- ✅ Passed: 12
- ❌ Failed: 2
- ⚠️ Errors: 1
- ⏭️ Skipped: 0
- 📈 Pass Rate: 80.0%

Status: ❌ Some tests failed

Detailed Results:
----------------------------------------
✅ tests/test_login.py::test_successful_login (0.12s)
❌ tests/test_checkout.py::test_payment_failure (0.45s)
⚠️ tests/test_api.py::test_create_user - ConnectionError
...

💡 Recommendations:
- Review failed tests for bugs
- Check error messages for root causes
- Fix failing assertions
```

## 📱 飞书机器人接入

### 前提条件

1. 在 [飞书开放平台](https://open.feishu.cn/) 注册账号
2. 创建企业自建应用并开启机器人能力
3. 获取以下配置信息：
   - App ID
   - App Secret
   - Verification Token

### 配置步骤

#### 1. 编辑飞书机器人配置

```bash
# 编辑 feishu_bot.py 文件
vim feishu_bot.py
```

修改配置区域：

```python
# ==================== 配置区域 ====================
APP_ID = "your_app_id"           # 替换为您的 App ID
APP_SECRET = "your_app_secret"   # 替换为您的 App Secret
VERIFICATION_TOKEN = "your_token" # 替换为您的 Verification Token
PORT = 5000
# ==================================================
```

#### 2. 配置飞书开放平台

1. 登录飞书开放平台，进入您的应用
2. 点击「功能」→「机器人」→「事件订阅」
3. 开启事件订阅
4. 设置请求 URL：`http://your-server-ip:5000/feishu/webhook`
5. 添加事件：`message`（消息事件）

#### 3. 安装依赖

```bash
pip install flask requests
```

#### 4. 启动服务

```bash
python feishu_bot.py
```

#### 5. 测试机器人

1. 在飞书客户端搜索您创建的机器人名称
2. 添加机器人为好友
3. 发送消息测试："帮我写一个测试计划"

### 注意事项

- **公网访问**: 飞书服务器需要能访问您的服务，需要公网 IP
- **HTTPS**: 建议使用 HTTPS（可配合 nginx + SSL）
- **安全**: 生产环境请关闭 debug 模式

## 🗂️ 项目结构

```
qa-agents/
├── main.py              # 主程序入口
├── feishu_bot.py        # 飞书机器人服务
├── rag.py               # RAG 模块
├── rag_update.py        # RAG 向量库更新工具
├── config/
│   └── settings.py      # LLM 配置
├── schemas/
│   └── state.py         # 状态定义
├── nodes/
│   ├── intent_node.py          # 意图识别节点
│   ├── chat_node.py            # 闲聊节点（支持 RAG）
│   ├── planner_node.py         # 测试计划节点
│   ├── designer_node.py        # 测试用例节点
│   ├── code_analysis_node.py   # 代码分析节点
│   └── rag_retrieve_node.py    # RAG 检索节点
├── tools/
│   ├── document_tools.py    # 文档工具
│   ├── file_tools.py        # 文件工具
│   ├── code_analyzer.py     # 代码分析工具
│   └── rag_tools.py         # RAG 工具
├── documents/           # RAG 文档目录
└── chroma_db/          # Chroma 向量数据库
```
