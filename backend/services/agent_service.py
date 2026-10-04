import json

from langchain_core.messages import (
    AIMessage,
    HumanMessage,
)

from database import SessionLocal
from graph.project_graph import run_agent_graph
from models import ChatHistory, ChatSession
from services.session_service import get_owned_session


def _load_history(
    db,
    session_id: int,
):
    """
    从 chat.db 读取业务聊天记录。

    只在旧会话第一次迁移到 LangGraph 时，
    用于初始化 Graph 的 messages。
    """

    rows = (
        db.query(ChatHistory)
        .filter(
            ChatHistory.session_id == session_id
        )
        .order_by(ChatHistory.id.asc())
        .limit(20)
        .all()
    )

    messages = []

    for row in rows:
        if row.role == "user":
            messages.append(
                HumanMessage(content=row.content)
            )

        elif row.role == "assistant":
            messages.append(
                AIMessage(content=row.content)
            )

    return messages


def _content_to_text(content) -> str:
    """
    兼容模型返回字符串或复杂内容。
    """

    if isinstance(content, str):
        return content

    return json.dumps(
        content,
        ensure_ascii=False,
        default=str,
    )


def agent_service(
    user_id: int,
    session_id: int | None,
    question: str,
):
    """
    业务层职责：

    1. 创建 / 验证 ChatSession；
    2. 读取和保存 ChatHistory；
    3. 调用 LangGraph Agent；
    4. 保持原接口返回格式。
    """

    db = SessionLocal()

    try:
        # =========================
        # 1. 创建或验证会话归属
        # =========================
        if session_id is None:
            session = ChatSession(
                user_id=user_id,
                title=question[:30],
            )

            db.add(session)
            db.commit()
            db.refresh(session)

            session_id = session.id

        else:
            # 确保当前 session 属于当前登录用户
            get_owned_session(
                db,
                user_id,
                session_id,
            )

        # =========================
        # 2. 读取旧业务聊天记录
        # =========================
        history_messages = _load_history(
            db,
            session_id,
        )

        # =========================
        # 3. 保存本轮用户问题
        # =========================
        db.add(
            ChatHistory(
                session_id=session_id,
                role="user",
                content=question,
            )
        )

        db.commit()

        # =========================
        # 4. 调用 LangGraph Agent
        # =========================
        result = run_agent_graph(
            user_id=user_id,
            session_id=session_id,
            question=question,
            history_messages=history_messages,
        )

        # =========================
        # 5. 整理 Graph 返回结果
        # =========================
        answer = _content_to_text(
            result["messages"][-1].content
        )

        if not answer.strip():
            answer = "模型没有生成文字回答。"

        sources = result.get("sources") or []
        steps = result.get("steps") or []

        # =========================
        # 6. 保存 AI 最终回答
        # =========================
        db.add(
            ChatHistory(
                session_id=session_id,
                role="assistant",
                content=answer,
            )
        )

        db.commit()

        # 保持 Router 原来的返回格式
        return (
            answer,
            session_id,
            sources,
            steps,
        )

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()