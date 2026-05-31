# Smart QA Agent

一个基于 **LangGraph** 和 **LLM** (主要针对本地部署的小模型)构建的私人智能测试助手，能够通过cli界面互动或飞书机器人互动，理解自然语言需求，自动生成专业的测试计划和测试用例。

## �🛠️ 环境准备

### 1. 安装 Python

确保安装 Python 3.10 或更高版本。

#### Ubuntu/Debian

```bash
sudo apt update
sudo apt install python3 python3-pip python3-venv -y
```

#### CentOS/RHEL

```bash
sudo yum install python3 python3-pip -y
```

#### macOS (使用 Homebrew)

```bash
brew install python3
```

#### 使用 Conda（推荐，跨平台）

```bash
# 安装 Miniconda
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
bash Miniconda3-latest-Linux-x86_64.sh

# 创建虚拟环境
conda create -n qa-agent python=3.12
conda activate qa-agent
```

#### 验证安装

```bash
python3 --version  # 应显示 Python 3.10+
pip3 --version
```

### 2. 安装依赖

```bash
# 基础依赖
pip install langchain langchain-openai langgraph sqlite-utils

# MCP 支持（可选）
pip install langchain-mcp
```

### 3. 下载 Embedding 模型（意图识别用）

本项目使用本地 embedding 模型进行语义意图识别,速度更快。

#### 作用
**意图识别**: 将用户输入分类为 CHAT/TEST_CASE/TEST_PLAN/CODE_ANALYSIS/RAG_QA/RUN_TESTS

#### 下载模型

```bash
# 于qa-agents目录中,创建模型目录
mkdir -p models

# 方法一：从 HuggingFace 下载（推荐）
pip install huggingface_hub
python -c "from huggingface_hub import snapshot_download; snapshot_download('sentence-transformers/all-MiniLM-L6-v2', local_dir='./models/all-MiniLM-L6-v2')"

# 方法二：手动下载
# 从 https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2 下载并解压到 models/all-MiniLM-L6-v2/
```

#### 依赖

```bash
pip install transformers torch
```

### 4. LLM 服务配置

本项目支持两种 LLM 服务模式：

#### 方式 A: 单模型模式（默认）

直接连接到单个 LLM 服务（如 Ollama、vLLM 等）：
- **地址**: `http://localhost:8080/v1`
- **模型**: `qwen`

#### 方式 B: Kong 网关多模型模式

通过 Kong API Gateway 访问多个 LLM 模型，详见下方「Kong 网关配置」章节。

## 🦍 Kong 网关配置

Kong 是一个 API 网关，可以将多个 LLM 服务统一管理，实现多模型切换。

### 安装 Kong

#### 方式一：Docker 部署（推荐）

```bash
# 拉取 Kong 网关镜像
docker pull kong:latest

# 创建网络
docker network create kong-net

# 启动 Kong（带 Admin API）
docker run -d \
  --name kong-gateway \
  --network kong-net \
  -e "KONG_DATABASE=off" \
  -e "KONG_DECLARATIVE_CONFIG=/usr/local/kong/declarative.yml" \
  -e "KONG_PROXY_ACCESS_LOG=/dev/stdout" \
  -e "KONG_ADMIN_ACCESS_LOG=/dev/stdout" \
  -e "KONG_PROXY_ERROR_LOG=/dev/stderr" \
  -e "KONG_ADMIN_ERROR_LOG=/dev/stderr" \
  -e "KONG_ADMIN_LISTEN=0.0.0.0:8001" \
  -p 8000:8000 \
  -p 8443:8443 \
  -p 127.0.0.1:8001:8001 \
  -p 127.0.0.1:8444:8444 \
  kong:latest
```

#### 方式二：本地安装

参考 [Kong 官方安装文档](https://docs.konghq.com/install/) 进行安装。

### 配置 Kong 路由

创建 `declarative.yml` 配置文件：

```yaml
_format_version: "3.0"
services:
  # Qwen 模型服务
  - name: qwen-llm
    url: http://localhost:8080/v1
    routes:
      - name: qwen-route
        paths:
          - /qwen
        strip_path: false
    plugins:
      - name: key-auth

  # Llama3 模型服务
  - name: llama3-llm
    url: http://localhost:8081/v1
    routes:
      - name: llama3-route
        paths:
          - /llama3
        strip_path: false
    plugins:
      - name: key-auth

routes:
  - name: qwen
    service: qwen-llm
    paths:
      - /qwen

  - name: llama3
    service: llama3-llm
    paths:
      - /llama3

plugins:
  - name: key-auth
    config:
      key_names:
        - apikey
      key_in_header: true
      key_in_query: true
```

### 启动 Kong

```bash
# 使用 declarative 配置启动
kong start -c /etc/kong/kong.conf --declarative-config /path/to/declarative.yml

# 或 Docker 方式（指定配置文件）
docker run -d \
  --name kong-gateway \
  -v /path/to/declarative.yml:/usr/local/kong/declarative.yml \
  -e "KONG_DATABASE=off" \
  -e "KONG_DECLARATIVE_CONFIG=/usr/local/kong/declarative.yml" \
  -e "KONG_ADMIN_LISTEN=0.0.0.0:8001" \
  -p 8000:8000 \
  -p 8001:8001 \
  kong:latest
```

### 验证 Kong 是否正常运行

```bash
# 检查 Kong 状态
curl -i http://localhost:8001

# 测试 Qwen 路由（需要 API Key）
curl -X POST http://localhost:8000/qwen/chat/completions \
  -H "Content-Type: application/json" \
  -H "apikey: your-api-key" \
  -d '{"model": "qwen", "messages": [{"role": "user", "content": "hello"}]}'
```

## ⚙️ 配置说明

修改 `config/settings.py` 配置 LLM 参数：

```python
class LLMConfig:
    # ==================== 模式配置 ====================
    # MODE: "single" - 单模型模式（原有模式）
    #       "kong"  - Kong 网关多模型模式
    MODE = "single"  # 默认使用单模型模式
    
    # ==================== 单模型模式配置 ====================
    BASE_URL = "http://localhost:8080/v1"
    API_KEY = "sk-no-key-required"
    MODEL_NAME = "qwen"
    TEMPERATURE = 0.7
    
    # ==================== Kong 网关模式配置 ====================
    KONG_BASE_URL = "http://localhost:8000/v1"  # Kong 网关地址
    KONG_API_KEY = "your-kong-api-key"          # Kong API 密钥
    
    # Kong 模式下支持的模型列表
    KONG_MODELS = {
        "qwen": {"model_name": "qwen", "description": "Qwen 大语言模型"},
        "llama3": {"model_name": "llama3", "description": "Meta Llama 3 模型"},
        "mistral": {"model_name": "mistral", "description": "Mistral AI 模型"},
        "gemma": {"model_name": "gemma", "description": "Google Gemma 模型"}
    }
    KONG_DEFAULT_MODEL = "qwen"  # 默认模型
```

### 切换到 Kong 多模型模式

1. 修改 `config/settings.py` 中的 `MODE`：
```python
MODE = "kong"  # 从 "single" 改为 "kong"
```

2. 配置 Kong 网关地址和 API Key：
```python
KONG_BASE_URL = "http://localhost:8000/v1"
KONG_API_KEY = "your-kong-api-key"
```

3. 根据实际 Kong 路由配置 `KONG_MODELS`：
```python
KONG_MODELS = {
    "qwen": {"model_name": "qwen", "description": "Qwen 模型"},
    # 添加其他模型...
}
```

4. 重启程序即可生效

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

### 模型切换（Kong 模式）

在 Kong 多模型模式下，支持以下命令：

| 命令 | 说明 |
|------|------|
| `/model` | 显示当前模型和可用模型列表 |
| `/model <模型名>` | 切换到指定模型（如 `/model llama3`） |
| `/model <序号>` | 通过序号切换模型（如 `/model 2`） |

**示例**：
```
🔵 [中文] 需求: /model

🤖 当前模型: qwen

📋 可用模型列表:
   1. qwen - Qwen 大语言模型 ← 当前
   2. llama3 - Meta Llama 3 模型
   3. mistral - Mistral AI 模型

💡 切换模型: /model <模型名称> 或 /model <序号>

🔵 [中文] 需求: /model llama3
✅ 模型已切换为: llama3
```

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
