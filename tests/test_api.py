# -*- coding: utf-8 -*-
"""API 层测试：健康检查 + 参数校验（不调用真实大模型、不需要 API Key）。"""
from fastapi.testclient import TestClient

from api import app

client = TestClient(app)


def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "model" in data


def test_chat_rejects_empty_question():
    resp = client.post("/chat", json={"question": ""})
    assert resp.status_code == 422


def test_chat_rejects_missing_field():
    resp = client.post("/chat", json={})
    assert resp.status_code == 422
