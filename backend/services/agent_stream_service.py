import json

from database import SessionLocal
from graph.project_graph import stream_agent_graph
from models import ChatHistory, ChatSession
from services.agent_service import _load_history
from services.session_service import get_owned_session


def _sse_event(
    event_name: str,
    data,
):
    """
    将 Python 数据包装为一条 SSE 事件。
    """
    return (
        f"event: {event_name}\n"
        f"data: {json.dumps(data, ensure_ascii=False, default=str)}\n\n"
    )


def _content_to_text(content) -> str:
    """
    兼容字符串或复杂的模型内容。
    """
    if isinstance(content, str):
        return content

    return json.dumps(
        content,
        ensure_ascii=False,
        default=str,
    )


def agent_service_stream(
    user_id: int,
    session_id: int | None,
    question: str,
):
    """
    真正的 LangGraph 流式接口。

    Graph 产出：
    - messages：模型 token；
    - updates：节点状态更新；
    - final_state：流程结束后的完整状态。

    本函数负责把它们转换为 SSE 事件。
    """

    db = SessionLocal()

    try:
        # 1. 创建或验证业务会话
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
            get_owned_session(
                db,
                user_id,
                session_id,
            )

        # 2. 读取 chat.db 历史
        history_messages = _load_history(
            db,
            session_id,
        )

        # 3. 保存本轮用户问题
        db.add(
            ChatHistory(
                session_id=session_id,
                role="user",
                content=question,
            )
        )

        db.commit()

        # 新会话编号应尽早告诉前端
        yield _sse_event(
            "session",
            {
                "session_id": session_id,
            },
        )

        yield _sse_event(
            "step",
            {
                "name": "agent_graph",
                "status": "running",
                "message": "Agent 正在处理问题",
            },
        )

        answer_parts = []
        final_state = None

        # 4. 持续读取 LangGraph 事件
        for part in stream_agent_graph(
            user_id=user_id,
            session_id=session_id,
            question=question,
            history_messages=history_messages,
        ):
            event_type = part["type"]

            # 模型生成的 token
            if event_type == "messages":
                message_chunk, metadata = part["data"]

                # tools 节点也可能产生带内容的 ToolMessage。
                # 工具原始结果不能当作 AI 回答发送给前端。
                # 只有 call_model 节点生成的内容才是可展示的回答 token。
                if metadata.get("langgraph_node") != "call_model":
                    continue

                content = message_chunk.content

                # 工具调用请求通常没有文字内容；
                # 只把真正的文字片段发送给前端。
                if not content:
                    continue

                token_text = _content_to_text(
                    content
                )

                answer_parts.append(
                    token_text
                )

                yield _sse_event(
                    "token",
                    {
                        "content": token_text,
                        "node": metadata.get(
                            "langgraph_node"
                        ),
                    },
                )

            # 节点完成后的 State 更新
            elif event_type == "updates":
                for node_name, update in part["data"].items():
                    # 没有 State 更新的节点，在流式事件中可能为 None。
                    # 它没有前端步骤可展示，直接跳过即可。
                    if not isinstance(update, dict):
                         continue
                    steps = update.get("steps") or []

                    for step in steps:
                        yield _sse_event(
                            "step",
                            step,
                        )
                # 工具执行过程主动发送的自定义进度
            elif event_type == "custom":
                custom_data = part["data"]

                if not isinstance(custom_data, dict):
                    continue

                if custom_data.get("type") == "tool_retry":
                    yield _sse_event(
                        "retry",
                        custom_data,
                    )

                elif custom_data.get("type") == "tool_progress":
                    yield _sse_event(
                        "step",
                        custom_data,
                    )

            # stream_agent_graph 自己补充的最终完整 State
            elif event_type == "final_state":
                final_state = part["data"]

        # 5. 拼接逐段收到的最终回答
        answer = "".join(answer_parts).strip()

        # 万一模型没有产生文字 token，
        # 从最终 Graph 状态中兜底获取回答。
        if not answer and final_state:
            answer = _content_to_text(
                final_state["messages"][-1].content
            )

        if not answer:
            answer = "模型没有生成文字回答。"

        sources = []

        if final_state:
            sources = final_state.get("sources") or []

        # 6. 保存最终 AI 回答到 chat.db
        db.add(
            ChatHistory(
                session_id=session_id,
                role="assistant",
                content=answer,
            )
        )

        db.commit()

        # 7. 发送来源和结束事件
        yield _sse_event(
            "sources",
            sources,
        )

        yield _sse_event(
            "done",
            {
                "session_id": session_id,
            },
        )

    except Exception as error:
        db.rollback()

        print(
            "agent_service_stream 执行失败：",
            error,
        )

        yield _sse_event(
            "error",
            {
                "message": "Agent 执行失败，请稍后重试。",
            },
        )

    finally:
        db.close()
