# 🛒 电商平台多智能体智能客服系统
# Multi-Agent Intelligent Customer Service System

基于 **LangGraph** 和 **Model Context Protocol (MCP)** 构建的下一代电商客服系统。采用层级化多智能体架构（Gateway-Manager-SubAgents），支持完全异步处理、RAG 知识库检索及复杂订单/商品业务逻辑处理。

---

## 🌟 核心特性 (Key Features)

*   **🧠 层级化智能体架构**: 
    *   **Gateway Agent**: 流量入口，负责会话管理、历史消息摘要及路由。
    *   **Manager Agent**: 业务总控，负责意图识别、任务拆解及子智能体调度。
    *   **Domain Sub-Agents**: 专职子智能体（Order Agent, Product Agent），专注于特定领域业务。
*   **🔌 MCP (Model Context Protocol) 集成**: 
    *   采用标准化 MCP 协议连接 SQLite 数据库，实现工具调用的解耦与标准化。
    *   支持透明化的上下文注入（如自动注入 `user_id`）。
*   **📚 RAG 知识检索增强**: 
    *   支持多格式文档加载（.docx, .md, .txt）。
    *   基于 FAISS 向量数据库实现公司政策、SOP 及常见问题的语义检索。
*   **⚡ 全异步高性能架构**: 
    *   基于 FastAPI + Asyncio 实现全链路异步处理。
    *   集成 AsyncRedisSaver 实现分布式状态持久化。
*   **🛠️ 强大的中间件机制**: 
    *   **Summarization**: 自动长对话摘要，优化 Context 窗口。
    *   **Self-Healing**: 具备工具调用异常检测与自动修复机制。

## 🏗️ 技术栈 (Tech Stack)

*   **核心框架**: [LangChain](https://www.langchain.com/), [LangGraph](https://langchain-ai.github.io/langgraph/), DeepAgents (Custom Wrapper)
*   **工具协议**: [Model Context Protocol (MCP)](https://modelcontextprotocol.io/)
*   **API 服务**: FastAPI, Uvicorn
*   **持久化 & 缓存**: Redis (AsyncCheckpoint), SQLite (业务数据)
*   **RAG & 向量库**: FAISS, OpenAIEmbeddings (DashScope兼容)
*   **大语言模型**: Qwen-Max (通义千问) via DashScope API

## 📂 项目结构 (Directory Structure)

```text
Multi_Agents/
├── agents/                 # 智能体核心逻辑
│   ├── gateway_agent.py    # 网关智能体 (入口、摘要、中间件组装)
│   ├── manager_agent.py    # 经理智能体 (中枢调度、RAG调用)
│   ├── order_agent.py      # 订单智能体 (MCP工具调用)
│   ├── product_agent.py    # 商品智能体 (MCP工具调用)
│   ├── mcp_wrapper.py      # MCP 工具包装器 (User_ID 注入)
│   └── RAG_tool.py         # RAG 检索工具实现
├── Mcpserver/              # MCP 服务端实现
│   ├── order_mcp.py        # 订单数据 MCP Server
│   └── product_mcp.py      # 商品数据 MCP Server
├── RAG_data/               # 知识库源文件 (.md, .docx, .txt)
├── service/                # FastAPI 服务入口
│   └── main.py
├── html/                   # 前端演示界面
├── run.sh                  # 启动脚本
└── .env                    # 环境变量配置文件
```

## 🚀 快速开始 (Getting Started)

### 1. 环境准备
确保已安装 Python 3.10+ 和 Redis 服务。

```bash
git clone https://github.com/您的用户名/您的仓库名.git
pip install -r requirements.txt
```

### 2. 配置环境变量
在项目根目录创建 `.env` 文件：

```env
# DashScope / OpenAI Compatible API Key
DASHSCOPE_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# Redis 配置
REDIS_URL=redis://:password@localhost:6379/0
```

### 3. 初始化数据 (可选)
如果需要重建数据库或向量索引：
```bash
python data/create_db.py
python Multi_Agents/RAG_data/create_data.py
```

### 4. 启动服务
使用脚本一键启动 FastAPI 服务：

```bash
sh Multi_Agents/run.sh
# 或者直接运行
python Multi_Agents/service/main.py
```

服务默认运行在 `http://localhost:8000//index.html`。



## 📄 许可证
[MIT License](LICENSE)
