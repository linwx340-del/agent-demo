# -*- coding: utf-8 -*-
"""Agent 主循环（ReAct 式函数调用循环）。

生成器版：边执行边 yield 事件，供命令行 / 网页 / API 实时展示思考过程。
这里不 import openai —— client 由调用方注入，方便单元测试（mock 一个假 client）。
"""
import json
import logging
import time

from .config import MODEL, MAX_ROUNDS
from .tools import TOOLS, TOOL_FUNCTIONS

logger = logging.getLogger("agent.core")


def _extract_usage(resp) -> dict:
    """从响应里安全取 token 用量（mock / 异常响应可能没有 usage 字段）。"""
    usage = getattr(resp, "usage", None)
    if usage is None:
        return {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
    return {
        "prompt_tokens": getattr(usage, "prompt_tokens", 0) or 0,
        "completion_tokens": getattr(usage, "completion_tokens", 0) or 0,
        "total_tokens": getattr(usage, "total_tokens", 0) or 0,
    }


def run_agent_stream(client, question: str):
    """边执行边 yield 事件。

    事件三种：
      {"type": "tool",   "round": 第几轮, "tool": 工具名, "args": 参数, "result": 工具返回}
      {"type": "answer", "content": 最终答案}
      {"type": "usage",  "prompt_tokens":, "completion_tokens":, "total_tokens":,
                         "tool_calls":, "elapsed_ms":}
    """
    messages = [{"role": "user", "content": question}]
    usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
    tool_calls = 0
    started = time.monotonic()

    for round_no in range(1, MAX_ROUNDS + 1):
        try:
            resp = client.chat.completions.create(
                model=MODEL,
                messages=messages,
                tools=TOOLS,
                temperature=0.0,   # 工具调用求稳，不需要发散
            )
        except Exception as e:
            logger.exception("第 %d 轮调用模型失败", round_no)
            yield {"type": "answer", "content": f"调用模型出错：{e}"}
            break

        u = _extract_usage(resp)
        usage["prompt_tokens"] += u["prompt_tokens"]
        usage["completion_tokens"] += u["completion_tokens"]
        usage["total_tokens"] += u["total_tokens"]

        msg = resp.choices[0].message

        if msg.tool_calls:
            messages.append(msg)
            for tc in msg.tool_calls:
                name = tc.function.name
                try:
                    args = json.loads(tc.function.arguments or "{}")
                except json.JSONDecodeError:
                    logger.warning("工具参数不是合法 JSON：%r", tc.function.arguments)
                    args = {}

                fn = TOOL_FUNCTIONS.get(name)
                if fn is None:
                    result = f"未知工具：{name}"
                    logger.warning("模型请求了未注册的工具：%s", name)
                else:
                    try:
                        result = fn(**args)
                    except Exception as e:
                        result = f"工具执行出错：{e}"
                        logger.exception("工具 %s 执行异常", name)

                tool_calls += 1
                yield {"type": "tool", "round": round_no, "tool": name,
                       "args": args, "result": str(result)}

                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": str(result),
                })
        else:
            yield {"type": "answer", "content": msg.content or ""}
            break
    else:
        yield {"type": "answer", "content": "（达到最大调用轮数，仍未给出最终答案）"}

    usage["tool_calls"] = tool_calls
    usage["elapsed_ms"] = int((time.monotonic() - started) * 1000)
    logger.info("完成：prompt=%d completion=%d total=%d tokens，工具调用 %d 次，耗时 %dms",
                usage["prompt_tokens"], usage["completion_tokens"],
                usage["total_tokens"], tool_calls, usage["elapsed_ms"])
    yield {"type": "usage", **usage}


def run_agent(client, question: str):
    """普通函数版：内部消费 run_agent_stream，返回 (最终答案, 工具轨迹, token 用量)。

    轨迹每项 {"round", "tool", "args", "result"}。
    """
    answer, trace, usage = "", [], {}
    for ev in run_agent_stream(client, question):
        if ev["type"] == "tool":
            trace.append({"round": ev["round"], "tool": ev["tool"],
                          "args": ev["args"], "result": ev["result"]})
        elif ev["type"] == "answer":
            answer = ev["content"]
        elif ev["type"] == "usage":
            # 去掉内部事件标记 "type"，对外 API 不暴露内部实现细节
            usage = {k: v for k, v in ev.items() if k != "type"}
    return answer, trace, usage
