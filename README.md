# 🤖 多工具智能体（Agent）

一个基于 **DeepSeek 函数调用（Function Calling）** 的多工具智能体：给大模型配上 4 个工具，它会自己判断「要不要调工具、调哪个、传什么参数」，**思考过程全程可见**，不是黑盒。

与 RAG 的区别：RAG = 大模型 + 知识库（检索文档回答）；Agent = 大模型 + 工具（模型自主决定调用）。

## 功能特性

- 4 个工具：四则运算 / 查当前时间 / 掷骰子 / 生成随机密码
- 模型自主决策：从用户问题里判断该调哪个工具，并自己组织参数
- 思考过程实时可视化：网页端用「思考中」盒子逐步展示 🔧 工具调用轨迹
- 命令行版 + 网页版共用同一套核心逻辑（`run_agent_stream` 生成器）

## 技术栈

- 界面：Streamlit
- 生成：DeepSeek（`deepseek-chat`）
- 核心机制：OpenAI Function Calling（工具调用循环）

## 本地运行

```bash
pip install openai streamlit
streamlit run app.py
```

API Key 二选一（**不要写进代码**）：

1. 在同目录建 `key.txt`，第一行放你的 key（已被 .gitignore 忽略）
2. 或设置环境变量 `DEEPSEEK_API_KEY`

命令行版：`python agent.py`

## 部署到 Streamlit Community Cloud

1. 把仓库推送到 GitHub（公开仓库）。
2. [share.streamlit.io](https://share.streamlit.io) → New app → 选本仓库，入口文件填 `app.py`。
3. Settings → Secrets 里加：

```toml
DEEPSEEK_API_KEY = "sk-你的key"
```

4. Deploy，得到公开网址。

## 项目结构

```
agent_demo/
├── agent.py          # 核心逻辑：4 个工具 + 函数调用循环（run_agent_stream）
├── app.py            # 网页版（Streamlit）
├── requirements.txt  # 依赖
└── .gitignore        # 忽略 key.txt / venv 等
```
