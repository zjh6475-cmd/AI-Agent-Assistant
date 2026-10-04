import uuid

from fastapi.testclient import TestClient

from main import app
import importlib

from langchain_core.messages import (
    AIMessage,
    AIMessageChunk,
)

client = TestClient(app)
chat_service_module = importlib.import_module(
    "services.chat_service"
)

def create_test_account():
    """
    创建一个唯一测试账号并登录，
    返回 username 和 token。
    """

    username = str(
        uuid.uuid4().int % 100000000000
    ).zfill(11)

    password = "123456"

    register_response = client.post(
        "/register",
        json={
            "username": username,
            "password": password,
            "confirm_password": password
        }
    )

    assert register_response.status_code == 200

    login_response = client.post(
        "/login",
        json={
            "username": username,
            "password": password
        }
    )

    assert login_response.status_code == 200

    login_data = login_response.json()

    assert login_data["message"] == "登录成功"
    assert "token" in login_data

    return {
        "username": username,
        "token": login_data["token"]
    }


def auth_headers(token):
    return {
        "Authorization": f"Bearer {token}"
    }


def test_register_and_login():
    account = create_test_account()

    assert account["username"]
    assert account["token"]


def test_register_invalid_username():
    response = client.post(
        "/register",
        json={
            "username": "abc",
            "password": "123456",
            "confirm_password": "123456"
        }
    )

    assert response.status_code == 200
    assert response.json()["message"] == (
        "账号必须是11位数字"
    )


def test_login_wrong_password():
    account = create_test_account()

    response = client.post(
        "/login",
        json={
            "username": account["username"],
            "password": "wrong-password"
        }
    )

    assert response.status_code == 200
    assert response.json()["message"] == (
        "用户名或密码错误"
    )


def test_sessions_requires_login():
    response = client.get(
        "/sessions"
    )

    assert response.status_code == 401


def test_create_session_after_login():
    account = create_test_account()

    response = client.post(
        "/session/new",
        headers=auth_headers(
            account["token"]
        )
    )

    assert response.status_code == 200

    data = response.json()

    assert "id" in data
    assert data["title"] == "新聊天"


def test_get_sessions_after_login():
    account = create_test_account()

    create_response = client.post(
        "/session/new",
        headers=auth_headers(
            account["token"]
        )
    )

    session_id = create_response.json()["id"]

    response = client.get(
        "/sessions",
        headers=auth_headers(
            account["token"]
        )
    )

    assert response.status_code == 200

    sessions = response.json()

    assert isinstance(sessions, list)

    session_ids = [
        item["id"]
        for item in sessions
    ]

    assert session_id in session_ids


def test_user_cannot_update_other_users_session():
    owner = create_test_account()
    other_user = create_test_account()

    create_response = client.post(
        "/session/new",
        headers=auth_headers(
            owner["token"]
        )
    )

    session_id = create_response.json()["id"]

    response = client.put(
        f"/session/{session_id}",
        headers=auth_headers(
            other_user["token"]
        ),
        json={
            "title": "非法修改"
        }
    )

    assert response.status_code == 404


def test_user_cannot_delete_other_users_session():
    owner = create_test_account()
    other_user = create_test_account()

    create_response = client.post(
        "/session/new",
        headers=auth_headers(
            owner["token"]
        )
    )

    session_id = create_response.json()["id"]

    response = client.delete(
        f"/session/{session_id}",
        headers=auth_headers(
            other_user["token"]
        )
    )

    assert response.status_code == 404


def test_owner_can_update_session_title():
    account = create_test_account()

    create_response = client.post(
        "/session/new",
        headers=auth_headers(
            account["token"]
        )
    )

    session_id = create_response.json()["id"]

    response = client.put(
        f"/session/{session_id}",
        headers=auth_headers(
            account["token"]
        ),
        json={
            "title": "新的聊天标题"
        }
    )

    assert response.status_code == 200

    data = response.json()

    assert data["message"] == "修改成功"
    assert data["title"] == "新的聊天标题"


def test_owner_can_delete_session():
    account = create_test_account()

    create_response = client.post(
        "/session/new",
        headers=auth_headers(
            account["token"]
        )
    )

    session_id = create_response.json()["id"]

    response = client.delete(
        f"/session/{session_id}",
        headers=auth_headers(
            account["token"]
        )
    )

    assert response.status_code == 200
    assert response.json()["message"] == "删除成功"
    
def test_normal_stream_answers_without_knowledge_base(
    monkeypatch,
):
    """
    普通流式聊天应直接调用模型，
    不得检索知识库。
    """

    class FakeDirectChatModel:
        def __init__(self):
            self.received_messages = []

        def stream(self, messages):
            self.received_messages = messages

            yield AIMessageChunk(
                content="Python 是一种编程语言。"
            )

    def forbidden_search_chunks(*args, **kwargs):
        raise AssertionError(
            "普通聊天不应检索知识库"
        )

    fake_model = FakeDirectChatModel()

    monkeypatch.setattr(
        chat_service_module,
        "llm",
        fake_model,
    )

    monkeypatch.setattr(
        chat_service_module,
        "search_chunks",
        forbidden_search_chunks,
        raising=False,
    )

    account = create_test_account()

    response = client.post(
        "/chat/stream",
        headers=auth_headers(account["token"]),
        json={
            "message": "Python 是什么？",
            "session_id": None,
        },
    )

    assert response.status_code == 200

    body = response.text

    assert "event: token" in body
    assert "Python 是一种编程语言。" in body
    assert "当前知识库中没有找到足够的信息" not in body
    assert "data:[]" in body

    system_prompt = (
        fake_model.received_messages[0].content
    )

    assert "知识库" not in system_prompt    
    
    user_contents = [
    item.content
    for item in fake_model.received_messages
    if getattr(item, "type", None) == "human"
]

    assert user_contents.count("Python 是什么？") == 1
    
    
def test_normal_chat_answers_without_knowledge_base(
    monkeypatch,
):
    """
    普通非流式聊天应直接调用模型，
    不得检索知识库。
    """

    class FakeDirectChatModel:
        def __init__(self):
            self.received_messages = []

        def invoke(self, messages):
            self.received_messages = messages

            return AIMessage(
                content="Python 是一种编程语言。"
            )

    def forbidden_search_chunks(*args, **kwargs):
        raise AssertionError(
            "普通聊天不应检索知识库"
        )

    fake_model = FakeDirectChatModel()

    monkeypatch.setattr(
        chat_service_module,
        "llm",
        fake_model,
    )

    monkeypatch.setattr(
        chat_service_module,
        "search_chunks",
        forbidden_search_chunks,
        raising=False,
    )

    account = create_test_account()

    response = client.post(
        "/chat",
        headers=auth_headers(account["token"]),
        json={
            "message": "Python 是什么？",
            "session_id": None,
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["answer"] == (
        "Python 是一种编程语言。"
    )
    assert "session_id" in data
    assert "sources" not in data

    system_prompt = (
        fake_model.received_messages[0].content
    )

    assert "知识库" not in system_prompt    