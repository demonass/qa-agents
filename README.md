# Smart QA Agent

基于大语言模型的智能 QA 测试助手，支持自动化测试计划生成、用例设计、RAG 问答等功能。

## 架构特点

### ReAct + Skills 架构

采用标准 Agent 行为方式：

- **ReAct 模式**: 通过 Thought → Action → Observation 循环实现智能推理
- **渐进式工具披露**: 根据任务需求动态加载所需工具，而非一次性加载所有工具
- **Skills 架构**: 将不同功能模块化封装为独立技能，便于维护和扩展
- **语义技能路由**: 使用 embedding 模型计算用户查询与技能的相似度，实现自动技能匹配

### 核心组件

- **ReAct Agent**: 核心推理引擎，控制 Thought-Action-Observation 循环
- **Skill Router**: 技能路由器，自动匹配用户查询与最合适的技能
- **Tool Manager**: 工具管理器，支持渐进式工具披露
- **Skills**: 功能模块集合，包括测试计划、测试用例设计、代码分析、RAG 问答等

## 安装

### 1. Python 环境

确保已安装 Python 3.10+：

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install python3.12 python3.12-venv python3.12-dev

# macOS (使用 Homebrew)
brew install python@3.12

# Windows
# 从 https://www.python.org/downloads/ 下载并安装
```

### 2. 创建虚拟环境

```bash
# 创建虚拟环境
python3.12 -m venv ai_env

# 激活虚拟环境
source ai_env/bin/activate  # Linux/macOS
# 或
.\ai_env\Scripts\activate   # Windows
```

### 3. 安装依赖

```bash
# 安装核心依赖
pip install langchain langchain-openai langgraph

# 安装工具依赖
pip install sentence-transformers chromadb  # RAG 相关
pip install redis  # 可选：用于 LLM 响应缓存

# 安装开发依赖
pip install rich pydantic
```

### 4. 环境配置

复制 `.env.example` 为 `.env` 并配置：

```bash
cp .env.example .env
```

编辑 `.env` 文件：

```env
# LLM 配置
OPENAI_API_KEY=your-api-key-here
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL_NAME=gpt-4o-mini

# Redis 缓存配置（可选）
LLM_CACHE_ENABLED=false
REDIS_HOST=localhost
REDIS_PORT=6379
LLM_CACHE_TTL=604800
```

### 5. Embedding 模型（可选）

用于语义技能路由和意图识别：

```bash
# 下载模型到项目目录
mkdir -p models
cd models
git clone https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2
```

注意：如果不使用本地 embedding 模型，系统会自动回退到 TF-IDF 方案。

## 使用方法

### 新版 CLI（ReAct + Skills）

```bash
source ai_env/bin/activate && python3 ./cli_react.py
```

**可用命令：**

- `help` - 显示帮助信息
- `skills` - 列出所有可用技能
- `tools` - 列出所有可用工具
- `skill <name>` - 切换到指定技能
- `quit` / `exit` - 退出

**命令历史：**

- ↑/↓ 箭头：查看历史命令
- Ctrl+R：搜索历史命令

### 旧版 CLI

```bash
source ai_env/bin/activate && python3 ./main.py
```

## 功能模块

### Skills

| 技能名称 | 描述 | 示例 |
|---------|------|------|
| `auto` | 通用自动化测试 | 设计一个电商系统的自动化测试方案 |
| `test_planning` | 测试计划生成 | 为新功能编写测试计划 |
| `test_case_design` | 测试用例设计 | 为登录功能设计测试用例 |
| `code_analysis` | 代码分析 | 分析项目代码结构和质量 |
| `rag_qa` | RAG 知识库问答 | 基于项目文档回答问题 |

### Tools

| 工具名称 | 描述 |
|---------|------|
| `save_test_plan` | 保存测试计划到文件 |
| `analyze_project` | 分析项目结构和代码 |
| `rag_retrieve` | 从 RAG 知识库检索相关内容 |

## 可选功能

### Redis 缓存

启用后可缓存 LLM 响应，减少重复 API 调用：

```python
# 在 config/settings.py 中设置
LLM_CACHE_ENABLED = True  # 默认为 False
```

### 上下文压缩

使用 tokenDrier 库压缩长文本，减少 token 消耗：

```bash
# 手动安装 tokenDrier
cd /tmp
git clone https://github.com/demonass/tokenDrier.git
cp -r tokenDrier/tokenDrier /path/to/your/project/tokenDrier_lib
```

## 项目结构

```
qa-agents/
├── agents/                 # Agent 核心实现
│   ├── react_agent.py    # ReAct Agent
│   ├── skill_router.py   # 技能路由器
│   └── tool_manager.py   # 工具管理器
├── cli_react.py           # 新版 CLI 入口
├── config/
│   └── settings.py       # 配置文件
├── models/               # Embedding 模型目录
├── prompts/              # 提示词模板
├── skills/               # 技能模块
│   ├── base.py          # 技能基类
│   ├── test_planning_skill.py
│   ├── test_case_design_skill.py
│   ├── code_analysis_skill.py
│   └── rag_qa_skill.py
├── tools/                # 工具实现
│   ├── cache_tools.py   # 缓存工具
│   ├── code_analyzer.py  # 代码分析工具
│   ├── document_tools.py # 文档处理工具
│   ├── file_tools.py     # 文件操作工具
│   └── rag_tools.py      # RAG 工具
└── output/               # 测试计划输出目录
```

## 开发

### 运行测试

```bash
# 激活环境
source ai_env/bin/activate

# 运行 CLI
python3 ./cli_react.py
```

### 调试模式

Agent 默认以 verbose 模式运行，会显示详细的思考过程和工具使用：

```
============================================================
🔄 迭代 1/5
============================================================

💡 [思考] 用户需要设计手机App的自动化测试方案，我需要先分析项目结构来了解测试范围。

🔧 [执行工具] analyze_project
   └── 参数: {"project_path": "."}

📋 [工具返回]
   └── 项目结构分析完成...
```

## License

MIT License
