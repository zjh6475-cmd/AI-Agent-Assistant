from langchain_core.messages import (
    AIMessage,
    HumanMessage,
    ToolMessage,
)
import graph.project_graph as project_graph
from graph.project_graph import (
    MAX_HISTORY_MESSAGES,
    _build_graph_config,
    _build_input_messages,
    _build_model_messages,
)

class FakeSnapshot:
    """模拟 graph.get_state() 返回的快照。"""

    def __init__(self, messages):
        self.values = {
            "messages": messages,
        }


class FakeGraph:
    """只模拟本次测试需要的 get_state 方法。"""

    def __init__(self, checkpoint_messages):
        self.checkpoint_messages = checkpoint_messages

    def get_state(self, config):
        return FakeSnapshot(
            self.checkpoint_messages
        )


def test_build_graph_config_uses_session_id_as_thread_id():
    config = _build_graph_config(session_id=88)

    assert config["configurable"]["thread_id"] == (
        "chat-session-88"
    )
    assert config["recursion_limit"] == 20


def test_existing_checkpoint_only_adds_current_question():
    """
    Checkpointer 已有消息时，
    不应再次注入数据库 ChatHistory。
    """

    graph = FakeGraph(
        checkpoint_messages=[
            HumanMessage(content="历史问题"),
            AIMessage(content="历史回答"),
        ]
    )

    history_messages = [
        HumanMessage(content="数据库历史问题"),
        AIMessage(content="数据库历史回答"),
    ]

    result = _build_input_messages(
        graph=graph,
        config=_build_graph_config(session_id=88),
        question="本轮新问题",
        history_messages=history_messages,
    )

    assert len(result) == 1
    assert isinstance(result[0], HumanMessage)
    assert result[0].content == "本轮新问题"


def test_empty_checkpoint_uses_old_history_to_initialize_graph():
    """
    新 Graph 还没有 Checkpointer 状态时，
    用旧 ChatHistory 初始化一次消息历史。
    """

    graph = FakeGraph(checkpoint_messages=[])

    history_messages = [
        HumanMessage(content="旧问题"),
        AIMessage(content="旧回答"),
    ]

    result = _build_input_messages(
        graph=graph,
        config=_build_graph_config(session_id=88),
        question="本轮新问题",
        history_messages=history_messages,
    )

    assert len(result) == 3
    assert result[0].content == "旧问题"
    assert result[1].content == "旧回答"
    assert result[2].content == "本轮新问题"
    
    
    
def test_model_message_window_keeps_recent_history_and_current_tool_turn():
    old_tool_request = AIMessage(
        content="",
        tool_calls=[
            {
                "name": "search_knowledge_base",
                "args": {
                    "query": "旧问题 2",
                },
                "id": "call-old-1",
            }
        ],
    )

    old_tool_result = ToolMessage(
        content="旧工具结果",
        tool_call_id="call-old-1",
    )

    current_question = HumanMessage(
        content="当前问题"
    )

    current_tool_request = AIMessage(
        content="",
        tool_calls=[
            {
                "name": "search_knowledge_base",
                "args": {
                    "query": "当前问题",
                },
                "id": "call-current-1",
            }
        ],
    )

    current_tool_result = ToolMessage(
        content="当前工具结果",
        tool_call_id="call-current-1",
    )

    result = _build_model_messages(
        [
            HumanMessage(content="旧问题 1"),
            AIMessage(content="旧回答 1"),
            HumanMessage(content="旧问题 2"),
            old_tool_request,
            old_tool_result,
            AIMessage(content="旧回答 2"),
            HumanMessage(content="旧问题 3"),
            AIMessage(content="旧回答 3"),
            HumanMessage(content="旧问题 4"),
            AIMessage(content="旧回答 4"),
            current_question,
            current_tool_request,
            current_tool_result,
        ]
    )

    assert [
        message.content
        for message in result[:MAX_HISTORY_MESSAGES]
    ] == [
        "旧问题 2",
        "旧回答 2",
        "旧问题 3",
        "旧回答 3",
        "旧问题 4",
        "旧回答 4",
    ]

    assert not any(
        isinstance(message, ToolMessage)
        for message in result[:MAX_HISTORY_MESSAGES]
    )

    assert result[-3].content == "当前问题"
    assert result[-2].tool_calls[0]["id"] == (
        "call-current-1"
    )
    assert result[-1].tool_call_id == "call-current-1"
    
    
def test_update_conversation_summary_only_handles_new_overflow(
    monkeypatch,
):
    """
    摘要节点只处理超出窗口、且之前未处理过的旧消息。
    当前问题不应被写入摘要。
    """

    class FakeSummaryModel:
        def __init__(self):
            self.calls = []

        def invoke(self, messages):
            self.calls.append(messages)

            return AIMessage(
                content="用户名字是小明。"
            )

    fake_model = FakeSummaryModel()

    # 用假模型替代真实 llm，避免真实 API 调用。
    monkeypatch.setattr(
        project_graph,
        "llm",
        fake_model,
    )

    state = {
        "messages": [
            HumanMessage(content="旧问题 1"),
            AIMessage(content="旧回答 1"),
            HumanMessage(content="旧问题 2"),
            AIMessage(content="旧回答 2"),
            HumanMessage(content="旧问题 3"),
            AIMessage(content="旧回答 3"),
            HumanMessage(content="旧问题 4"),
            AIMessage(content="旧回答 4"),
            HumanMessage(content="当前问题"),
        ],
        "conversation_summary": "",
        "summary_message_count": 0,
    }

    first_result = (
        project_graph.update_conversation_summary(
            state
        )
    )

    # 8 条旧消息中，最近 6 条保留，因此只摘要前 2 条。
    assert first_result == {
        "conversation_summary": "用户名字是小明。",
        "summary_message_count": 2,
    }

    assert len(fake_model.calls) == 1

    # 假模型收到的新增摘要内容只能包含最早两条旧消息。
    summary_input = fake_model.calls[0][1].content

    assert "旧问题 1" in summary_input
    assert "旧回答 1" in summary_input
    assert "旧问题 3" not in summary_input
    assert "当前问题" not in summary_input

    # 带着第一次的摘要进度再次执行，不应重复调用模型。
    second_state = {
        **state,
        **first_result,
    }

    second_result = (
        project_graph.update_conversation_summary(
            second_state
        )
    )

    assert second_result == {}
    assert len(fake_model.calls) == 1
    
    
def test_both_model_paths_receive_conversation_summary(
    monkeypatch,
):
    """
    正常模型路径与工具上限兜底路径，
    都必须收到历史摘要。
    """

    class FakeModel:
        def __init__(self):
            self.received_messages = []

        def invoke(self, messages):
            self.received_messages = messages

            return AIMessage(
                content="模拟回答"
            )

    direct_model = FakeModel()
    fallback_model = FakeModel()

    # 正常 Agent 路径使用绑定工具后的模型。
    monkeypatch.setattr(
        project_graph,
        "llm_with_tools",
        direct_model,
    )

    # 工具上限后的兜底路径使用普通模型。
    monkeypatch.setattr(
        project_graph,
        "llm",
        fallback_model,
    )

    state = {
        "messages": [
            HumanMessage(content="当前问题"),
        ],
        "conversation_summary": (
            "用户名字是小明。"
        ),
    }

    project_graph.call_model(state)

    project_graph.finalize_after_tool_limit(
        state
    )

    direct_system_prompt = (
        direct_model.received_messages[0].content
    )

    fallback_system_prompt = (
        fallback_model.received_messages[0].content
    )

    assert "用户名字是小明。" in direct_system_prompt
    assert "用户名字是小明。" in fallback_system_prompt

    assert "工具调用次数已经达到上限" not in (
        direct_system_prompt
    )

    assert "工具调用次数已经达到上限" in (
        fallback_system_prompt
    )    
    
    
def test_run_agent_graph_can_use_memory_checkpoint(
    monkeypatch,
):
    checkpoint_locations = []

    class FakeCheckpointer:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    class FakeSqliteSaver:
        @classmethod
        def from_conn_string(cls, location):
            checkpoint_locations.append(location)
            return FakeCheckpointer()

    class FakeRunnableGraph:
        def get_state(self, config):
            return FakeSnapshot([])

        def invoke(self, state, *, config, context):
            assert state["messages"][0].content == "测试问题"
            assert context.user_id == 1

            return {
                "messages": [
                    AIMessage(content="测试回答")
                ]
            }

    monkeypatch.setattr(
        project_graph,
        "SqliteSaver",
        FakeSqliteSaver,
    )
    monkeypatch.setattr(
        project_graph,
        "build_graph",
        lambda checkpointer: FakeRunnableGraph(),
    )

    result = project_graph.run_agent_graph(
        user_id=1,
        session_id=9999,
        question="测试问题",
        checkpoint_database=":memory:",
    )

    assert checkpoint_locations == [":memory:"]
    assert result["messages"][-1].content == "测试回答"    