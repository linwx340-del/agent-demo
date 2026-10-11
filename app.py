# -*- coding: utf-8 -*-
"""
多工具智能体 · 网页版（Streamlit）

核心卖点：看得见思考过程。
模型会自己决定「要不要调工具、调哪个、传什么参数」，
每一步调用都会实时展示出来，而不是黑盒直接给答案。

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
    st.caption("试着问它：\n\n- 帮我算一下 1234 * 5678\n- 现在几点了\n- 掷两个骰子\n- 生成一个 12 位密码")

# ================= 对话历史 =================
if "messages" not in st.session_state:
    st.session_state["messages"] = []   # {"role","content","trace"}

for msg in st.session_state["messages"]:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])
        if msg["role"] == "assistant" and msg.get("trace"):
            with st.expander("🔍 思考过程"):
                for step in msg["trace"]:
                    st.markdown(
                        f"**第 {step['round']} 轮** · 调用工具 `{step['tool']}`\n\n"
                        f"参数 `{step['args']}` → 返回：{step['result']}"
                    )

# ================= 输入 =================
if prompt := st.chat_input("输入问题，比如：帮我算一下 1234 * 5678"):
    st.session_state["messages"].append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)

    if not api_key:
        st.error("请先配置 API Key（见左侧）")
    else:
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
