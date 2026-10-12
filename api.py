# -*- coding: utf-8 -*-
"""FastAPI 后端（阶段 2 + 阶段 4）：把 Agent 能力暴露成 REST API。

启动（在 agent_demo 目录，先装 fastapi uvicorn）：
    uvicorn api:app --reload

接口：
    GET     /health              健康检查
    POST    /chat                手写版 Agent（一次性返回：答案 + 工具轨迹 + token 用量）
    POST    /chat/stream         手写版 Agent（SSE 流式返回，边跑边推思考过程）
    POST    /chat/langchain      LangChain 版 Agent（带会话记忆，SQLite 持久化）
    DELETE  /chat/langchain/{id} 清空某个会话的历史

启动后浏览器打开 http://127.0.0.1:8000/docs 可看自动生成的接口文档。
"""
import json
import logging

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from openai import OpenAI

from agent import (
    API_KEY, BASE_URL, MODEL, TIMEOUT, setup_logging,
    run_agent, run_agent_stream,
)

logger = logging.getLogger("agent.api")

app = FastAPI(
    title="多工具智能体 API",
    description="给大模型配 4 个工具，模型自主决策调用；提供手写版 + LangChain 版两套实现，REST + SSE 流式接口。",
    version="0.4.0",
)

setup_logging()


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000, description="用户问题")


class ChatResponse(BaseModel):
    answer: str = Field(..., description="最终答案")
    trace: list[dict] = Field(default_factory=list, description="工具调用轨迹")
    usage: dict = Field(default_factory=dict, description="token 用量与耗时统计")


class LangChainChatRequest(BaseModel):
    session_id: str = Field(..., min_length=1, max_length=100, description="会话 ID（同一 ID 共享记忆）")
    question: str = Field(..., min_length=1, max_length=2000, description="用户问题")


class LangChainChatResponse(BaseModel):
    session_id: str = Field(..., description="会话 ID")
    answer: str = Field(..., description="最终答案")
    trace: list[dict] = Field(default_factory=list, description="工具调用轨迹")
    usage: dict = Field(default_factory=dict, description="token 用量")
    history_messages: int = Field(..., description="本轮之后的会话历史消息数")


def _build_client() -> OpenAI:
    """统一创建 OpenAI 兼容 client；缺 Key 时直接返回 503。"""
    if not API_KEY:
        raise HTTPException(status_code=503, detail="服务端未配置 DEEPSEEK_API_KEY")
    return OpenAI(api_key=API_KEY, base_url=BASE_URL, timeout=TIMEOUT)


@app.get("/health", tags=["系统"])
def health():
    """健康检查：确认服务活着、Key 是否就绪。"""
    return {"status": "ok", "model": MODEL, "key_ready": bool(API_KEY)}


@app.post("/chat", response_model=ChatResponse, tags=["对话"])
def chat(req: ChatRequest):
    """手写版：一次性返回（最终答案 + 工具调用轨迹 + token 用量）。"""
    client = _build_client()
    try:
        answer, trace, usage = run_agent(client, req.question)
    except Exception as e:
        logger.exception("处理请求失败")
        raise HTTPException(status_code=500, detail=f"处理失败：{e}")
    logger.info("请求完成：%d 次工具调用，共 %d tokens，耗时 %dms",
                usage.get("tool_calls", 0), usage.get("total_tokens", 0),
                usage.get("elapsed_ms", 0))
    return ChatResponse(answer=answer, trace=trace, usage=usage)


@app.post("/chat/stream", tags=["对话"])
def chat_stream(req: ChatRequest):
    """手写版 SSE 流式：边跑边推事件（tool / answer / usage），前端可实时显示思考过程。"""
    client = _build_client()

    def event_stream():
        try:
            for ev in run_agent_stream(client, req.question):
                yield f"data: {json.dumps(ev, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as e:
            logger.exception("流式处理失败")
            err = {"type": "error", "content": str(e)}
            yield f"data: {json.dumps(err, ensure_ascii=False)}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.post("/chat/langchain", response_model=LangChainChatResponse, tags=["对话"])
def chat_langchain(req: LangChainChatRequest):
    """LangChain 版：带会话记忆（SQLite 持久化），同一 session_id 可多轮对话。

    和手写版 /chat 的区别：多传一个 session_id，历史自动带上并持久化。
    """
    # 惰性导入 + 探测 langchain 是否已装：没装时给出友好提示，而不是 500。
    try:
        import langchain_openai  # noqa: F401  探测 langchain 是否已安装
        from agent.langchain_agent import chat as langchain_chat
    except ImportError:
        raise HTTPException(
            status_code=503,
            detail="未安装 LangChain 依赖，请先运行：pip install langchain langchain-openai langchain-community langgraph sqlalchemy",
        )

    if not API_KEY:
        raise HTTPException(status_code=503, detail="服务端未配置 DEEPSEEK_API_KEY")

    try:
        result = langchain_chat(req.session_id, req.question)
    except Exception as e:
        logger.exception("LangChain 处理失败")
        raise HTTPException(status_code=500, detail=f"处理失败：{e}")

    return LangChainChatResponse(session_id=req.session_id, **result)


@app.delete("/chat/langchain/{session_id}", tags=["对话"])
def clear_langchain_session(session_id: str):
    """清空某个会话的历史记录。"""
    try:
        from agent.langchain_agent import clear_session
    except ImportError:
        raise HTTPException(status_code=503, detail="未安装 LangChain 依赖")
    clear_session(session_id)
    return {"cleared": session_id}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
