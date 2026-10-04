from langchain_core.messages import AIMessage
from langgraph.graph import (
    StateGraph,
    MessagesState,
    START,
    END,
)
from langgraph.prebuilt import ToolNode

from graph.agent_context import AgentContext
from graph.agent_tools import query_user_data


# =========================
# 1. 创建一个工具调用请求
# =========================

tool_call_message = AIMessage(
    content="",
    tool_calls=[
        {
            "name": "query_user_data",
            "args": {
                "action": "session_count",
            },
            "id": "test-call-1",
        }
    ],
)


# =========================
# 2. 创建 ToolNode
# =========================

tool_node = ToolNode(
    [
        query_user_data,
    ]
)


# =========================
# 3. 创建 Graph
# =========================

builder = StateGraph(
    MessagesState,
    context_schema=AgentContext,
)

builder.add_node(
    "tools",
    tool_node,
)

builder.add_edge(
    START,
    "tools",
)

builder.add_edge(
    "tools",
    END,
)

graph = builder.compile()


# =========================
# 4. 运行 Graph
# =========================

if __name__ == "__main__":
    result = graph.invoke(
        {
            "messages": [
                tool_call_message,
            ]
        },
        context=AgentContext(
            user_id=1,
        ),
    )

    print(result)