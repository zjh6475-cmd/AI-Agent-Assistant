import graph.project_graph as project_graph

from langchain_core.messages import (
    AIMessage,
    HumanMessage,
    ToolMessage,
)
from langchain_core.tools import tool
from langgraph.checkpoint.memory import InMemorySaver

from graph.agent_context import AgentContext


class FakeAgentModel:
    """
    模拟两次模型调用：

    第一次：请求工具；
    第二次：读取成功的 ToolMessage 后给出最终回答。
    """

    def __init__(self):
        self.calls = []

    def invoke(self, messages):
        self.calls.append(messages)

        # 第一次模型调用：
        # 决定请求 flaky_search 工具。
        if len(self.calls) == 1:
            return AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "flaky_search",
                        "args": {
                            "query": "测试重试",
                        },
                        "id": "call-retry-1",
                    }
                ],
            )

        # 第二次模型调用前，
        # 应已收到工具最终成功的 ToolMessage。
        last_message = messages[-1]

        assert isinstance(
            last_message,
            ToolMessage,
        )

        assert last_message.status == "success"

        assert "检索成功" in str(
            last_message.content
        )

        return AIMessage(
            content=(
                "工具已在自动重试后恢复，"
                "检索结果已成功返回。"
            )
        )


def test_real_graph_retries_transient_tool_error(
    monkeypatch,
):
    """
    使用真实 build_graph() 验证：

    模型请求工具
    → 工具前两次 ConnectionError
    → retry_tool_call 自动重试
    → 第三次成功
    → 模型根据成功 ToolMessage 给出最终回答。
    """

    attempts = {
        "count": 0,
    }

    @tool
    def flaky_search(
        query: str,
    ) -> dict:
        """
        前两次模拟网络故障，第三次成功。
        """

        attempts["count"] += 1

        if attempts["count"] < 3:
            raise ConnectionError(
                "临时网络错误"
            )

        return {
            "result": "检索成功",
        }
        
            # 集成测试只验证调用顺序，
            # 不真实等待退避时间。
    monkeypatch.setattr(
        project_graph.time,
        "sleep",
        lambda seconds: None,
    )

    fake_model = FakeAgentModel()

    # 将真实 Graph 中使用的工具替换为测试工具。
    monkeypatch.setattr(
        project_graph,
        "tools",
        [flaky_search],
    )

    # 将真实模型替换为假模型，
    # 不调用任何模型 API。
    monkeypatch.setattr(
        project_graph,
        "llm_with_tools",
        fake_model,
    )

    # 内存 Checkpointer：
    # 只为测试保存状态，不会创建 SQLite 文件。
    graph = project_graph.build_graph(
        InMemorySaver()
    )

    result = graph.invoke(
        {
            "messages": [
                HumanMessage(
                    content="请帮我检索测试内容"
                )
            ]
        },
        config={
            "configurable": {
                "thread_id": "integration-retry-test",
            },
            "recursion_limit": 10,
        },
        context=AgentContext(
            user_id=1,
        ),
    )

    # 真实工具必须执行 3 次：
    # 两次失败 + 第三次成功。
    assert attempts["count"] == 3

    # 真实 Graph 应调用模型两次：
    # 工具调用前一次、工具成功后一次。
    assert len(fake_model.calls) == 2

    # 最终 State 最后一条消息是第二次模型生成的回答。
    assert result["messages"][-1].content == (
        "工具已在自动重试后恢复，"
        "检索结果已成功返回。"
    )
    
    
def test_real_graph_stream_emits_retry_events(
    monkeypatch,
):
    """
    使用真实 build_graph() 验证：

    工具前两次临时失败时，
    retry_tool_call 写出的 custom 重试事件
    能从 graph.stream() 中正常流出。
    """

    attempts = {
        "count": 0,
    }

    @tool
    def flaky_search(
        query: str,
    ) -> dict:
       

        """
        模拟临时网络故障：
        前两次调用失败，第三次调用成功。
        """
        attempts["count"] += 1
        if attempts["count"] < 3:
            raise ConnectionError(
                "临时网络错误"
            )

        return {
            "result": "检索成功",
        }

    # 测试只验证事件和执行顺序，
    # 不真实等待 0.5 秒、1 秒。
    monkeypatch.setattr(
        project_graph.time,
        "sleep",
        lambda seconds: None,
    )

    fake_model = FakeAgentModel()

    # 将真实 Graph 依赖替换成可控测试对象。
    monkeypatch.setattr(
        project_graph,
        "tools",
        [flaky_search],
    )
    monkeypatch.setattr(
        project_graph,
        "llm_with_tools",
        fake_model,
    )

    graph = project_graph.build_graph(
        InMemorySaver()
    )

    # 关键：真实 Graph 以 custom 流模式执行。
    events = list(
        graph.stream(
            {
                "messages": [
                    HumanMessage(
                        content="请帮我检索测试内容"
                    )
                ]
            },
            config={
                "configurable": {
                    "thread_id": "stream-retry-test",
                },
                "recursion_limit": 10,
            },
            context=AgentContext(
                user_id=1,
            ),
            stream_mode=["custom"],
            version="v2",
        )
    )

    # 从所有 Graph 事件中，只留下重试事件。
    retry_events = [
        event["data"]
        for event in events
        if event["type"] == "custom"
        and isinstance(event["data"], dict)
        and event["data"].get("type") == "tool_retry"
    ]

    # 工具仍应是：失败两次，第三次成功。
    assert attempts["count"] == 3

    # 两次失败，因此应向流中写入两次“准备重试”事件。
    assert len(retry_events) == 2

    # 第一次失败后，准备第 2 次尝试，等待 0.5 秒。
    assert retry_events[0]["name"] == "flaky_search"
    assert retry_events[0]["status"] == "retrying"
    assert retry_events[0]["attempt"] == 2
    assert retry_events[0]["max_attempts"] == 3
    assert retry_events[0]["retry_after_seconds"] == 0.5

    # 第二次失败后，准备第 3 次尝试，等待 1 秒。
    assert retry_events[1]["attempt"] == 3
    assert retry_events[1]["retry_after_seconds"] == 1.0