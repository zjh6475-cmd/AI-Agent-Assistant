from langchain_core.messages import AIMessage
from langgraph.graph import END

from graph.project_graph import (
    MAX_TOOL_ROUNDS,
    route_after_model,
)


def test_model_without_tool_calls_goes_to_end():
    """
    模型直接回答，
    不请求工具时，Graph 应该结束。
    """

    state = {
        "messages": [
            AIMessage(
                content="这是普通回答"
            )
        ],
        "tool_round": 0,
    }

    result = route_after_model(state)

    assert result == END


def test_model_with_tool_calls_goes_to_tools():
    """
    模型请求工具，且还没超过限制，
    应进入 ToolNode。
    """

    state = {
        "messages": [
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "query_user_data",
                        "args": {
                            "action": "document_count",
                        },
                        "id": "call-test-1",
                    }
                ],
            )
        ],
        "tool_round": 0,
    }

    result = route_after_model(state)

    assert result == "tools"


def test_tool_calls_over_limit_go_to_tool_limit():
    """
    模型还想调用工具，
    但本轮工具次数已达到上限时，
    应进入 tool_limit，而不是继续执行工具。
    """

    state = {
        "messages": [
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "query_user_data",
                        "args": {
                            "action": "document_count",
                        },
                        "id": "call-test-2",
                    }
                ],
            )
        ],
        "tool_round": MAX_TOOL_ROUNDS,
    }

    result = route_after_model(state)

    assert result == "tool_limit"