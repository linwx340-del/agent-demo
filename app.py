# -*- coding: utf-8 -*-
"""
多工具智能体 · 网页版（Streamlit）

核心卖点：看得见思考过程。
模型会自己决定「要不要调工具、调哪个、传什么参数」，
每一步调用都会实时展示出来，而不是黑盒直接给答案。

两种模式（左侧「对话模式」切换）：
  - 手写版（流式 · 无记忆）：实时流式展示思考过程，但不记得上一轮。
  - LangChain 版（带会话记忆）：同一浏览器会话里模型记得之前的对话，
    历史持久化到 SQLite（chat_history.db），刷新页面后依然记得。

运行（在 agent_demo 目录下）：
    streamlit run app.py
"""

import streamlit as st
from openai import OpenAI

from agent import run_agent_stream, API_KEY, BASE_URL, MODEL, TOOLS

# ================= 页面 =================
st.set_page_config(page_title="多工具智能体", page_icon="🤖", layout="wide")
st.title("🤖 多工具智能体")
st.caption("给大模型配上工具，它会自己决定调用哪个、传什么参数——下面的思考过程全程可见，不是黑盒。")

# ================= API Key =================
# 优先级：Streamlit Cloud 的 Secrets > 环境变量 / key.txt（agent.py 里已处理）
def get_api_key():
    try:
        key = st.secrets.get("DEEPSEEK_API_KEY", "")
        if key:
            return key
    except Exception:
        pass
    return API_KEY


api_key = get_api_key()

# ================= 会话状态 =================
if "messages" not in st.session_state:
    st.session_state["messages"] = []   # {"role","content","trace"}

# ================= 侧边栏 =================
with st.sidebar:
    st.header("⚙️ 设置")
    if api_key:
        st.success("✅ API Key 已就绪")
    else:
        st.error("❌ 未检测到 API Key")
        st.caption("云端：Settings → Secrets 配 DEEPSEEK_API_KEY；本地：放 key.txt 或设环境变量")

    st.markdown("---")
    st.header("🛠️ 可用工具")
    for t in TOOLS:
        fn = t["function"]
        st.markdown(f"- **{fn['name']}**：{fn['description']}")

    st.markdown("---")
    st.header("🧠 对话模式")
    mode = st.radio(
        "选择引擎",
        ["手写版（流式 · 无记忆）", "LangChain 版（带会话记忆）"],
        index=0,
        help="手写版实时流式展示思考过程，但不记得上一轮；LangChain 版带多轮记忆（SQLite 持久化），同一浏览器会话里能连续追问。",
    )

    if mode == "LangChain 版（带会话记忆）":
        # 每个浏览器会话一个独立 session_id，避免不同标签页/不同人串记忆
        if "session_id" not in st.session_state:
            import uuid
            st.session_state["session_id"] = f"web-{uuid.uuid4().hex[:8]}"
        st.caption(f"会话 ID：`{st.session_state['session_id']}`")
        if st.button("🧹 清空记忆"):
            try:
                from agent.langchain_agent import clear_session
                clear_session(st.session_state["session_id"])
            except ImportError:
                pass
            st.session_state["messages"] = []
            st.rerun()

    st.markdown("---")
    st.caption("试着问它：\n\n- 帮我算一下 1234 * 5678\n- 现在几点了\n- 掷两个骰子\n- 生成一个 12 位密码")

# ================= 对话历史 =================
for msg in st.session_state["messages"]:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])
        if msg["role"] == "assistant" and msg.get("trace"):
            with st.expander("🔍 思考过程"):
                for i, step in enumerate(msg["trace"], 1):
                    st.markdown(
                        f"**第 {step.get('round', i)} 轮** · 调用工具 `{step['tool']}`\n\n"
                        f"参数 `{step['args']}` → 返回：{step['result']}"
                    )

# ================= 输入 =================
if prompt := st.chat_input("输入问题，比如：帮我算一下 1234 * 5678"):
    st.session_state["messages"].append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)

    if not api_key:
        st.error("请先配置 API Key（见左侧）")

    elif mode == "LangChain 版（带会话记忆）":
        # —— LangChain 版：带多轮记忆（SQLite 持久化）——
        try:
            from agent.langchain_agent import chat as langchain_chat
        except ImportError:
            st.error("未安装 LangChain 依赖，请先运行：pip install langchain langchain-openai langchain-community langgraph sqlalchemy greenlet aiosqlite")
        else:
            with st.chat_message("assistant"):
                with st.spinner("🤖 思考中…"):
                    try:
                        result = langchain_chat(st.session_state["session_id"], prompt)
                        answer = result["answer"]
                        trace = result["trace"]
                        usage = result["usage"]
                        history_n = result["history_messages"]
                    except Exception as e:
                        st.error(f"处理失败：{e}")
                    else:
                        st.write(answer)
                        with st.expander("🔍 思考过程"):
                            if trace:
                                for step in trace:
                                    st.markdown(
                                        f"🔧 调用工具 `{step['tool']}`\n\n"
                                        f"参数 `{step['args']}` → 返回：{step['result']}"
                                    )
                            else:
                                st.caption("本轮未调用工具")
                        st.caption(
                            f"共 {usage.get('total_tokens', 0)} tokens "
                            f"（输入 {usage.get('prompt_tokens', 0)} / 输出 {usage.get('completion_tokens', 0)}）· "
                            f"已记忆 {history_n} 条消息"
                        )
                        st.session_state["messages"].append(
                            {"role": "assistant", "content": answer, "trace": trace}
                        )

    else:
        # —— 手写版：流式，无记忆 ——
        client = OpenAI(api_key=api_key, base_url=BASE_URL)
        trace = []

        with st.chat_message("assistant"):
            # st.status：把「思考过程」装进一个可展开的盒子里，边跑边显示
            with st.status("🤖 思考中…", expanded=True) as status:
                answer = ""
                usage = {}
                for ev in run_agent_stream(client, prompt):
                    if ev["type"] == "tool":
                        trace.append({"round": ev["round"], "tool": ev["tool"],
                                      "args": ev["args"], "result": ev["result"]})
                        st.markdown(
                            f"🔧 **第 {ev['round']} 轮** · 调用工具 `{ev['tool']}`\n\n"
                            f"参数 `{ev['args']}` → 返回：{ev['result']}"
                        )
                    elif ev["type"] == "answer":
                        answer = ev["content"]
                    elif ev["type"] == "usage":
                        usage = ev
                status.update(label="✅ 完成", state="complete", expanded=False)

            st.write(answer)
            if usage:
                st.caption(
                    f"⏱️ {usage.get('elapsed_ms', 0)}ms · "
                    f"共 {usage.get('total_tokens', 0)} tokens "
                    f"（输入 {usage.get('prompt_tokens', 0)} / 输出 {usage.get('completion_tokens', 0)}）· "
                    f"{usage.get('tool_calls', 0)} 次工具调用"
                )

        st.session_state["messages"].append(
            {"role": "assistant", "content": answer, "trace": trace}
        )
