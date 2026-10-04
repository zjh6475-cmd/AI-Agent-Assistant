import logging
import graph.project_graph as project_graph
from langchain_core.messages import (
    AIMessage,
    ToolMessage,
)
from langchain_core.tools import tool
from langgraph.prebuilt import ToolNode
from langgraph.runtime import Runtime

from graph.project_graph import (
    format_tool_error,
    record_tool_result,
    retry_tool_call,
)


def build_tool_node(*tool_list):
    """
    创建和项目一致的 ToolNode。
    """

    return ToolNode(
        list(tool_list),
        handle_tool_errors=False,
        wrap_tool_call=retry_tool_call,
    )


def build_tool_call_message(
    tool_name: str = "failing_search",
) -> AIMessage:
    """
    模拟模型请求调用指定工具。
    """

    return AIMessage(
        content="",
        tool_calls=[
            {
                "name": tool_name,
                "args": {
                    "query": "测试问题",
                },
                "id": "call-error-1",
            }
        ],
    )


@tool
def failing_search(
    query: str,
) -> dict:
    """
    故意模拟知识库服务不可用。
    """

    raise ConnectionError(
        "向量数据库暂时不可用"
    )


def test_format_tool_error_hides_internal_details(
    caplog,
):
    """
    用户看不到内部异常，
    后端日志仍保留异常信息。
    """

    error = ConnectionError(
        "向量数据库暂时不可用"
    )

    with caplog.at_level(
        logging.ERROR,
        logger="graph.project_graph",
    ):
        message = format_tool_error(error)

    assert message == (
        "工具服务暂时不可用，请稍后重试。"
    )

    assert "向量数据库" not in message

    assert "Tool execution failed" in caplog.text
    assert "向量数据库暂时不可用" in caplog.text


def test_tool_node_converts_exception_to_safe_tool_message():
    """
    工具最终失败后：

    1. ToolNode 不应中断 Graph；
    2. 应生成脱敏 ToolMessage。
    """

    tool_node = build_tool_node(
        failing_search,
    )

    ai_message = build_tool_call_message()

    result = tool_node.invoke(
        {
            "messages": [ai_message],
        },
        runtime=Runtime(),
    )

    error_message = result["messages"][0]

    assert isinstance(
        error_message,
        ToolMessage,
    )

    assert error_message.name == "failing_search"

    assert error_message.tool_call_id == (
        "call-error-1"
    )

    assert error_message.status == "error"

    assert error_message.content == (
        "工具服务暂时不可用，请稍后重试。"
    )

    assert "向量数据库" not in str(
        error_message.content
    )


def test_record_tool_result_records_safe_error_step():
    """
    工具最终失败后，
    record_tool_result 记录安全 error 步骤。
    """

    tool_node = build_tool_node(
        failing_search,
    )

    ai_message = build_tool_call_message()

    tool_result = tool_node.invoke(
        {
            "messages": [ai_message],
        },
        runtime=Runtime(),
    )

    error_message = tool_result["messages"][0]

    state = {
        "messages": [
            ai_message,
            error_message,
        ],
        "tool_round": 0,
    }

    update = record_tool_result(state)

    assert update["tool_round"] == 1

    step = update["steps"][0]

    assert step["name"] == "failing_search"
    assert step["status"] == "error"

    assert "工具服务暂时不可用" in step[
        "message"
    ]

    assert "向量数据库" not in step["message"]

    assert "sources" not in update


def test_retry_transient_error_until_tool_succeeds(
     monkeypatch,
):
    """
    ConnectionError 前两次失败、第三次成功时：

    - 工具总共执行 3 次；
    - 最终返回成功 ToolMessage；
    - Graph 不会看到中间两次失败。
    """

    attempts = {
        "count": 0,
    }

    @tool
    def flaky_search(
        query: str,
    ) -> dict:
        """
        前两次模拟网络失败，第三次成功。
        """

        attempts["count"] += 1

        if attempts["count"] < 3:
            raise ConnectionError(
                "临时网络错误"
            )

        return {
            "result": "检索成功",
        }
        
    retry_events = []    
    retry_delays = []

    # 测试时不真实等待 0.5 / 1.0 秒，
    # 只记录本应等待的时间。
    monkeypatch.setattr(
        project_graph.time,
        "sleep",
        retry_delays.append,
    )

    tool_node = build_tool_node(
        flaky_search,
    )

    ai_message = build_tool_call_message(
        tool_name="flaky_search",
    )

    result = tool_node.invoke(
        {
            "messages": [ai_message],
        },
        runtime=Runtime(
             stream_writer=retry_events.append,),
    )

    message = result["messages"][0]

    assert attempts["count"] == 3
    assert retry_events == [
        {
            "type": "tool_retry",
            "name": "flaky_search",
            "status": "retrying",
            "attempt": 2,
            "max_attempts": 3,
            "retry_after_seconds": 0.5,
            "message": (
                "工具 flaky_search 暂时不可用，"
                "将在 0.5 秒后进行第 2/3 次尝试。"
            ),
        },
        {
            "type": "tool_retry",
            "name": "flaky_search",
            "status": "retrying",
            "attempt": 3,
            "max_attempts": 3,
            "retry_after_seconds": 1.0,
            "message": (
                "工具 flaky_search 暂时不可用，"
                "将在 1.0 秒后进行第 3/3 次尝试。"
            ),
        },
    ]

    assert retry_delays == [
        0.5,
        1.0,
    ]

    assert message.status == "success"

    assert "检索成功" in str(
        message.content
    )


def test_value_error_is_not_retried():
    """
    ValueError 属于参数或业务错误：

    - 只执行一次；
    - 不进行无意义重试；
    - 直接生成安全错误 ToolMessage。
    """

    attempts = {
        "count": 0,
    }

    @tool
    def invalid_search(
        query: str,
    ) -> dict:
        """
        模拟不可恢复的参数错误。
        """

        attempts["count"] += 1

        raise ValueError(
            "查询参数格式错误"
        )

    tool_node = build_tool_node(
        invalid_search,
    )

    ai_message = build_tool_call_message(
        tool_name="invalid_search",
    )

    result = tool_node.invoke(
        {
            "messages": [ai_message],
        },
        runtime=Runtime(),
    )

    message = result["messages"][0]

    assert attempts["count"] == 1

    assert message.status == "error"

    assert message.content == (
        "工具执行失败，"
        "暂时无法完成这次请求，请稍后重试。"
    )

    assert "查询参数格式错误" not in str(
        message.content
    )