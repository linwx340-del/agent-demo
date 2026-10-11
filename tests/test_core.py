# -*- coding: utf-8 -*-
"""核心循环单元测试：用假 client 模拟大模型响应，不发起真实网络请求。"""
from agent.core import run_agent_stream, run_agent


class _Fn:
    def __init__(self, name, arguments):
        self.name = name
        self.arguments = arguments


class _ToolCall:
    def __init__(self, name, arguments, call_id="call_1"):
        self.id = call_id
        self.function = _Fn(name, arguments)


class _Msg:
    def __init__(self, tool_calls=None, content=None):
        self.tool_calls = tool_calls
        self.content = content


class _Choice:
    def __init__(self, msg):
        self.message = msg


class _Usage:
    def __init__(self, prompt_tokens=0, completion_tokens=0, total_tokens=0):
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens
        self.total_tokens = total_tokens


class _Resp:
    def __init__(self, msg, usage=None):
        self.choices = [_Choice(msg)]
        self.usage = usage


class _Completions:
    def __init__(self, script, usages=None):
        self._script = list(script)
        self._usages = list(usages) if usages else []
        self._i = 0

    def create(self, **kwargs):
        msg = self._script[self._i]
        usage = None
        if self._i < len(self._usages):
            u = self._usages[self._i]
            usage = _Usage(u["prompt_tokens"], u["completion_tokens"], u["total_tokens"])
        self._i += 1
        return _Resp(msg, usage)


class _Chat:
    def __init__(self, script, usages=None):
        self.completions = _Completions(script, usages)


class FakeClient:
    """按脚本顺序吐消息：先给 tool_calls，再给最终答案；usages 按轮次附上 token 用量。"""

    def __init__(self, script, usages=None):
        self.chat = _Chat(script, usages)


def test_stream_calls_tool_then_answers():
    client = FakeClient([
        _Msg(tool_calls=[_ToolCall("calculate", '{"expression": "3 * 4"}')]),
        _Msg(content="结果是 12"),
    ])
    events = list(run_agent_stream(client, "3 乘 4 等于几"))

    assert events[0]["type"] == "tool"
    assert events[0]["tool"] == "calculate"
    assert events[0]["result"] == "12"

    answer = [e for e in events if e["type"] == "answer"][0]
    assert answer["content"] == "结果是 12"

    usage = events[-1]
    assert usage["type"] == "usage"
    assert usage["tool_calls"] == 1
    assert "elapsed_ms" in usage


def test_stream_unknown_tool():
    client = FakeClient([
        _Msg(tool_calls=[_ToolCall("not_exist", "{}")]),
        _Msg(content="我不知道"),
    ])
    events = list(run_agent_stream(client, "随便"))
    assert "未知工具" in events[0]["result"]


def test_usage_accumulates():
    client = FakeClient(
        [
            _Msg(tool_calls=[_ToolCall("calculate", '{"expression": "1 + 1"}')]),
            _Msg(content="2"),
        ],
        usages=[
            {"prompt_tokens": 100, "completion_tokens": 10, "total_tokens": 110},
            {"prompt_tokens": 120, "completion_tokens": 5, "total_tokens": 125},
        ],
    )
    events = list(run_agent_stream(client, "1 + 1"))
    usage = events[-1]
    assert usage["type"] == "usage"
    assert usage["prompt_tokens"] == 220
    assert usage["completion_tokens"] == 15
    assert usage["total_tokens"] == 235
    assert usage["tool_calls"] == 1


def test_run_agent_returns_answer_trace_usage():
    client = FakeClient([
        _Msg(tool_calls=[_ToolCall("roll_dice", '{"count": 1, "sides": 6}')]),
        _Msg(content="掷出 3"),
    ])
    answer, trace, usage = run_agent(client, "掷个骰子")
    assert answer == "掷出 3"
    assert len(trace) == 1
    assert trace[0]["tool"] == "roll_dice"
    assert usage["tool_calls"] == 1
    assert usage["prompt_tokens"] == 0  # 未传 usages 时安全回退为 0
    assert "type" not in usage  # 对外 API 不暴露内部事件标记
