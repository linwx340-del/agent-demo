# -*- coding: utf-8 -*-
"""LangChain 版 Agent 的纯逻辑单元测试（不依赖 langchain，用假消息对象）。"""
from agent.langchain_agent import _extract_answer, _extract_trace, _extract_usage


class _FakeMsg:
    """模拟 LangChain 消息对象，只实现纯逻辑 helper 需要的字段。"""

    def __init__(self, type_, content=None, tool_call_id=None, tool_calls=None,
                 response_metadata=None):
        self.type = type_
        self.content = content
        self.tool_call_id = tool_call_id
        self.tool_calls = tool_calls
        self.response_metadata = response_metadata or {}


def test_extract_answer_returns_last_ai_content():
    messages = [
        _FakeMsg("human", content="你好"),
        _FakeMsg("ai", content=""),            # 中间空 AI 消息（工具调用那一轮）
        _FakeMsg("ai", content="最终答案"),
    ]
    assert _extract_answer(messages) == "最终答案"


def test_extract_trace_matches_tool_results():
    messages = [
        _FakeMsg("human", content="算一下"),
        _FakeMsg("ai", tool_calls=[{"name": "calculate", "args": {"expression": "1+1"}, "id": "c1"}]),
        _FakeMsg("tool", content="2", tool_call_id="c1"),
        _FakeMsg("ai", content="答案是 2"),
    ]
    trace = _extract_trace(messages)
    assert len(trace) == 1
    assert trace[0]["tool"] == "calculate"
    assert trace[0]["args"] == {"expression": "1+1"}
    assert trace[0]["result"] == "2"


def test_extract_trace_unknown_result_is_empty():
    messages = [
        _FakeMsg("ai", tool_calls=[{"name": "calculate", "args": {}, "id": "c9"}]),
    ]
    trace = _extract_trace(messages)
    assert trace[0]["tool"] == "calculate"
    assert trace[0]["result"] == ""


def test_extract_usage_accumulates():
    messages = [
        _FakeMsg("ai", content="x", response_metadata={
            "token_usage": {"prompt_tokens": 100, "completion_tokens": 10, "total_tokens": 110},
        }),
        _FakeMsg("ai", content="y", response_metadata={
            "token_usage": {"prompt_tokens": 50, "completion_tokens": 5, "total_tokens": 55},
        }),
    ]
    usage = _extract_usage(messages)
    assert usage["prompt_tokens"] == 150
    assert usage["completion_tokens"] == 15
    assert usage["total_tokens"] == 165


def test_extract_usage_without_metadata_returns_zero():
    usage = _extract_usage([_FakeMsg("ai", content="x")])
    assert usage == {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
