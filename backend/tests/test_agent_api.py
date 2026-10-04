import importlib
import uuid

from fastapi.testclient import TestClient
from langchain_core.messages import (
    AIMessage,
    AIMessageChunk,
)

from main import app


client = TestClient(app)

agent_service_module = importlib.import_module(
    "services.agent_service"
)

agent_stream_service_module = importlib.import_module(
    "services.agent_stream_service"
)


def create_test_account():
    username = str(
        uuid.uuid4().int % 100000000000
    ).zfill(11)

    password = "123456"

    register_response = client.post(
        "/register",
        json={
            "username": username,
            "password": password,
            "confirm_password": password,
        },
    )

    assert register_response.status_code == 200

    login_response = client.post(
        "/login",
        json={
            "username": username,
            "password": password,
        },
    )

    assert login_response.status_code == 200

    return {
        "username": username,
        "token": login_response.json()["token"],
    }


def auth_headers(token):
    return {
        "Authorization": f"Bearer {token}",
    }


def test_agent_chat_requires_login():
    response = client.post(
        "/agent/chat",
        json={
            "message": "Python 是什么？",
            "session_id": None,
        },
    )

    assert response.status_code == 401


def test_agent_chat_with_fake_graph(
    monkeypatch,
):
    """
    不调用真实模型，
    直接模拟 run_agent_graph 的最终结果。
    """

    def fake_run_agent_graph(
        user_id,
        session_id,
        question,
        history_messages,
    ):
        return {
            "messages": [
                AIMessage(
                    content="这是测试用的 AI 回答"
                )
            ],
            "sources": [],
            "steps": [
                {
                    "name": "call_model",
                    "status": "success",
                    "message": "模型调用完成",
                }
            ],
        }

    monkeypatch.setattr(
        agent_service_module,
        "run_agent_graph",
        fake_run_agent_graph,
    )

    account = create_test_account()

    response = client.post(
        "/agent/chat",
        headers=auth_headers(
            account["token"]
        ),
        json={
            "message": "Python 是什么？",
            "session_id": None,
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["answer"] == (
        "这是测试用的 AI 回答"
    )

    assert data["session_id"] is not None
    assert data["sources"] == []

    assert data["steps"][0]["name"] == (
        "call_model"
    )


def test_agent_stream_requires_login():
    response = client.post(
        "/agent/chat/stream",
        json={
            "message": "Python 是什么？",
            "session_id": None,
        },
    )

    assert response.status_code == 401


def test_agent_stream_with_fake_graph(
    monkeypatch,
):
    """
    不调用真实模型和真实 Graph。

    模拟 Graph 依次产生：
    1. messages token；
    2. updates 步骤；
    3. final_state 最终状态。
    """

    def fake_stream_agent_graph(
        user_id,
        session_id,
        question,
        history_messages,
    ):
        yield {
            "type": "messages",
            "data": (
                AIMessageChunk(
                    content="这是测试"
                ),
                {
                    "langgraph_node": "call_model",
                },
            ),
        }

        yield {
            "type": "messages",
            "data": (
                AIMessageChunk(
                    content="用的 AI 回答"
                ),
                {
                    "langgraph_node": "call_model",
                },
            ),
        }

        # tools 节点的内容是工具原始结果，
        # 不应作为 token 发送给前端。
        yield {
            "type": "messages",
            "data": (
                AIMessageChunk(
                    content="TOOL_INTERNAL_RESULT"
                ),
                {
                    "langgraph_node": "tools",
                },
            ),
        }
        # 摘要节点在历史未溢出时没有 State 更新。
        # 流式事件中的 update 可能为 None。
        yield {
            "type": "updates",
            "data": {
                "update_summary": None,
            },
        }

        yield {
            "type": "updates",
            "data": {
                "call_model": {
                    "steps": [
                        {
                            "name": "call_model",
                            "status": "success",
                            "message": "模型调用完成",
                        }
                    ]
                }
            },
        }
        yield {
            "type": "custom",
            "data": {
                "type": "tool_progress",
                "name": "search_knowledge_base",
                "status": "running",
                "message": "正在检索知识库，请稍候。",
            },
        }

        yield {
            "type": "custom",
            "data": {
                "type": "tool_retry",
                "name": "search_knowledge_base",
                "status": "retrying",
                "attempt": 2,
                "max_attempts": 3,
                "message": (
                    "工具 search_knowledge_base 暂时不可用，"
                    "正在第 2/3 次尝试。"
                ),
            },
        }

        yield {
            "type": "final_state",
            "data": {
                "messages": [
                    AIMessage(
                        content="这是测试用的 AI 回答"
                    )
                ],
                "sources": [],
            },
        }

    monkeypatch.setattr(
        agent_stream_service_module,
        "stream_agent_graph",
        fake_stream_agent_graph,
    )

    account = create_test_account()

    response = client.post(
        "/agent/chat/stream",
        headers=auth_headers(
            account["token"]
        ),
        json={
            "message": "Python 是什么？",
            "session_id": None,
        },
    )

    assert response.status_code == 200

    body = response.text

    assert "event: session" in body
    assert "event: step" in body
    assert "event: token" in body
    assert "event: retry" in body
    assert "search_knowledge_base" in body
    assert '"status": "retrying"' in body
    assert "event: sources" in body
    assert "event: done" in body

    assert "这是测试" in body
    assert "用的 AI 回答" in body
    assert "TOOL_INTERNAL_RESULT" not in body
    assert "正在检索知识库，请稍候。" in body
