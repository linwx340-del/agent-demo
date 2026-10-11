# 🤖 多工具智能体（Agent）

一个基于 **DeepSeek 函数调用（Function Calling）** 的多工具智能体：给大模型配上 4 个工具，它会自己判断「要不要调工具、调哪个、传什么参数」，**思考过程全程可见**，不是黑盒。

与 RAG 的区别：RAG = 大模型 + 知识库（检索文档回答）；Agent = 大模型 + 工具（模型自主决定调用）。

## 功能特性

- 4 个工具：四则运算 / 查当前时间 / 掷骰子 / 生成随机密码
- 模型自主决策：从用户问题里判断该调哪个工具，并自己组织参数
- 思考过程实时可视化：网页端用「思考中」盒子逐步展示 🔧 工具调用轨迹
- 命令行版 + 网页版共用同一套核心逻辑（`run_agent_stream` 生成器）
- token 用量统计：每次对话记录输入/输出 token 数、工具调用次数、耗时

## 技术栈

- 界面：Streamlit
- 后端：FastAPI（REST + SSE 流式）
- 生成：DeepSeek（`deepseek-chat`）
- 核心机制：OpenAI Function Calling（工具调用循环）
- 测试：pytest（14 个单测）

## 本地运行

```bash
pip install openai streamlit
streamlit run app.py
```

API Key 二选一（**不要写进代码**）：

1. 在同目录建 `key.txt`，第一行放你的 key（已被 .gitignore 忽略）
2. 或设置环境变量 `DEEPSEEK_API_KEY`

命令行版：`python cli.py`

## 部署到 Streamlit Community Cloud

1. 把仓库推送到 GitHub（公开仓库）。
2. [share.streamlit.io](https://share.streamlit.io) → New app → 选本仓库，入口文件填 `app.py`。
3. Settings → Secrets 里加：

```toml
DEEPSEEK_API_KEY = "sk-你的key"
```

4. Deploy，得到公开网址。

## API 服务（FastAPI）

装依赖后启动后端：

```bash
pip install fastapi uvicorn
uvicorn api:app --reload
```

接口一览：

- `GET  /health`        健康检查
- `POST /chat`          一次性返回 `{"answer": "...", "trace": [...], "usage": {...}}`
- `POST /chat/stream`   SSE 流式，边跑边推思考过程

请求体示例：

```json
{"question": "帮我算一下 1234 * 5678"}
```

返回的 `usage` 字段（token 用量 + 耗时统计）：

```json
{
  "prompt_tokens": 1026,
  "completion_tokens": 55,
  "total_tokens": 1081,
  "tool_calls": 1,
  "elapsed_ms": 1835
}
```

启动后浏览器打开 `http://127.0.0.1:8000/docs` 可看到自动生成的接口文档。

## Docker 部署

把 API 后端打包成容器，一条命令拉起服务。前置：装好 [Docker Desktop](https://www.docker.com/products/docker-desktop/)。

```bash
# 1) 准备密钥：复制模板并填真实 key
#    Windows：copy .env.example .env
#    然后打开 .env，把 sk-xxx 换成你的真实 key

# 2) 构建并启动
docker compose up --build
```

日常开关：

```bash
docker compose up -d    # 后台启动
docker compose down     # 停止并删除容器
```

启动后浏览器打开 `http://127.0.0.1:8000/docs`，或 `curl http://127.0.0.1:8000/health`。

说明：

- **镜像里不含密钥**：key 通过 `.env`（或 `docker run -e DEEPSEEK_API_KEY=...`）注入；`key.txt` 和 `.env` 都被 `.dockerignore` 排除，不会打进镜像。
- **镜像只装 API 运行时**：Streamlit 网页版和命令行是本地开发工具，不进镜像。
- `docker-compose.yml` 里 `restart: unless-stopped` 让服务挂了自动重启，不想要可删掉那两行。

不用 compose，纯 docker 命令也可以：

```bash
docker build -t agent-api .
docker run -p 8000:8000 -e DEEPSEEK_API_KEY=sk-你的key agent-api
```

## 项目结构

```
agent_demo/
├── agent/                # 核心包（分层结构）
│   ├── __init__.py       # 对外统一导出
│   ├── config.py         # 配置（环境变量 + key.txt 兜底）
│   ├── tools.py          # 4 个工具 + 注册表 + 工具说明书
│   └── core.py           # 函数调用循环（run_agent_stream）
├── cli.py                # 命令行入口
├── app.py                # 网页版（Streamlit）
├── api.py                # 后端（FastAPI：REST + SSE）
├── tests/                # 单元测试（pytest，14 个）
├── Dockerfile            # API 后端镜像定义
├── docker-compose.yml    # 一键构建 + 启动
├── .dockerignore         # 不打进镜像的文件（含 key.txt / .env）
├── .env.example          # 密钥模板（复制成 .env 填真实 key）
├── requirements.txt      # 运行依赖
├── requirements-dev.txt  # 测试依赖
└── .gitignore            # 忽略 key.txt / .env / venv 等
```
