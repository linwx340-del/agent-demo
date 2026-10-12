# -*- coding: utf-8 -*-
"""LangChain / LangGraph 版 Agent（阶段 4）：create_react_agent + SQLite 会话记忆。

与手写版（core.py）的对比，面试时能讲清楚"框架替我们省掉了哪些活"：
  - 手写版：自己管理 messages 循环、解析 tool_calls、逐个执行工具、拼回结果、算 token。
  - 本文件：循环 + 工具调度交给 LangGraph 的 create_react_agent，我们只负责
    ①定义工具 ②配模型 ③管理会话记忆（SQLite 持久化）。

设计说明：
  - langchain 相关 import 全部放在函数内部（惰性导入）。这样没装 langchain 时，
    本模块仍可被 import，纯逻辑 helper 可以脱离 langchain 单独做单元测试，
    API 也能优雅降级（提示先装依赖），不会因为缺包把整个服务带崩。
"""
import logging

from .config import API_KEY, BASE_URL, MODEL, TIMEOUT, CHAT_HISTORY_DB
from .tools import TOOL_FUNCTIONS

logger = logging.getLogger("agent.langchain")

# 工具说明书（给大模型看）。description 会被 LangChain 转成工具描述，
# func 是真正执行的函数（直接复用 tools.py 里的实现，不重复造轮子）。
_TOOL_SPECS = [
    {
        "name": "calculate",
        "func": TOOL_FUNCTIONS["calculate"],
        "description": "计算四则运算表达式，例如 3*(2+5) 或 100/4。只支持数字和 + - * / ( ) %。",
    },
    {
        "name": "get_current_time",
        "func": TOOL_FUNCTIONS["get_current_time"],
        "description": "获取当前日期、时间和星期几。",
    },
    {
        "name": "roll_dice",
        "func": TOOL_FUNCTIONS["roll_dice"],
        "description": "掷骰子，返回每次点数和总和。count=骰子个数(默认1)，sides=面数(默认6)。",
    },
    {
        "name": "generate_password",
        "func": TOOL_FUNCTIONS["generate_password"],
        "description": "生成随机强密码，含大小写字母、数字和符号。length=密码长度(默认16)。",
    },
]


# ================= 纯逻辑（不依赖 langchain，可独立单测） =================

def _extract_answer(messages) -> str:
    """从消息列表里取最后一条 AI 消息的内容，作为最终答案。"""
    for m in reversed(messages):
        if getattr(m, "type", "") == "ai":
            content = getattr(m, "content", "") or ""
            if content:
                return content
    return ""


def _extract_trace(messages) -> list:
    """从消息列表里提取工具调用轨迹，字段与手写版对齐：{tool, args, result}。"""
    # 第一遍：收集所有工具执行结果（tool_call_id -> 内容）
    tool_results = {}
    for m in messages:
        if getattr(m, "type", "") == "tool":
            tool_results[getattr(m, "tool_call_id", "")] = getattr(m, "content", "")

    # 第二遍：遍历 AI 消息里的 tool_calls，拼出轨迹
    trace = []
    for m in messages:
        for tc in getattr(m, "tool_calls", None) or []:
            trace.append({
                "tool": tc.get("name", ""),
                "args": tc.get("args", {}),
                "result": tool_results.get(tc.get("id", ""), ""),
            })
    return trace


def _extract_usage(messages) -> dict:
    """尽力从各条 AI 消息的 response_metadata 里累加 token 用量（取不到就回退 0）。"""
    prompt = completion = total = 0
    for m in messages:
        meta = getattr(m, "response_metadata", None) or {}
        usage = meta.get("token_usage") or meta.get("usage") or {}
        if usage:
            prompt += usage.get("prompt_tokens", 0) or 0
            completion += usage.get("completion_tokens", 0) or 0
            total += usage.get("total_tokens", 0) or 0
    return {"prompt_tokens": prompt, "completion_tokens": completion, "total_tokens": total}


# ================= Agent 构建（langchain 惰性导入） =================

def _build_model():
    """DeepSeek 是 OpenAI 兼容协议，用 langchain-openai 的 ChatOpenAI 改 base_url 即可。"""
    from langchain_openai import ChatOpenAI

    return ChatOpenAI(
        model=MODEL,
        api_key=API_KEY,
        base_url=BASE_URL,
        temperature=0.0,   # 工具调用求稳
        timeout=TIMEOUT,
    )


def _build_tools():
    """把手写版的 4 个工具函数包装成 LangChain 工具（复用 tools.py 的实现）。"""
    from langchain_core.tools import StructuredTool

    return [
        StructuredTool.from_function(
            func=spec["func"],
            name=spec["name"],
            description=spec["description"],
        )
        for spec in _TOOL_SPECS
    ]


def build_agent():
    """构建 LangGraph ReAct Agent（工具调用型）。"""
    from langgraph.prebuilt import create_react_agent

    return create_react_agent(model=_build_model(), tools=_build_tools())


def _get_history(session_id: str):
    """按 session_id 取 SQLite 里的对话历史（同一 session 跨请求共享记忆）。"""
    from langchain_community.chat_message_histories import SQLChatMessageHistory

    # langchain-community 0.3.x 起把参数 connection_string 改名为 connection。
    # 我们的 /chat/langchain 是同步接口，所以显式 async_mode=False 走同步引擎，
    # 否则连接串写成 sqlite+aiosqlite:/// 会触发异步引擎，在同步上下文里报
    # "greenlet_spawn has not been called" 错误。
    # 旧版本（<0.3）则回退到 connection_string + 同步引擎。
    try:
        return SQLChatMessageHistory(
            session_id=session_id,
            connection=f"sqlite:///{CHAT_HISTORY_DB}",
            async_mode=False,
        )
    except TypeError:
        return SQLChatMessageHistory(
            session_id=session_id,
            connection_string=f"sqlite:///{CHAT_HISTORY_DB}",
        )


# ================= 对外接口 =================

def chat(session_id: str, question: str) -> dict:
    """带会话记忆的一次问答：自动带上该 session 的历史，实现多轮对话 + 持久化。

    返回 {"answer", "trace", "usage", "history_messages"}。
    同一 session_id 多次调用，模型会"记得"之前的对话。
    """
    from langchain_core.messages import HumanMessage

    history = _get_history(session_id)
    past = list(history.messages)  # 已持久化的历史消息

    agent = build_agent()
    result = agent.invoke({"messages": [*past, HumanMessage(content=question)]})

    out_messages = result["messages"]
    answer = _extract_answer(out_messages)
    trace = _extract_trace(out_messages)
    usage = _extract_usage(out_messages)

    # 把本轮问答写回 SQLite，供下一次请求读取
    history.add_user_message(question)
    history.add_ai_message(answer)

    return {
        "answer": answer,
        "trace": trace,
        "usage": usage,
        "history_messages": len(past) + 2,
    }


def clear_session(session_id: str) -> None:
    """清空某个会话的历史。"""
    _get_history(session_id).clear()
