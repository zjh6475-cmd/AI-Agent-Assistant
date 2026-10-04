from langchain_core.tools import tool
from langchain_core.messages import (
    AIMessage,
    HumanMessage,
    ToolMessage,
)

from langgraph.prebuilt import ToolNode
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import MessagesState


# =========================
# 1. 定义工具
# =========================

@tool
def add_numbers(a: int, b: int) -> int:
    """计算两个整数的和。"""
    print("add_numbers 工具正在执行")
    return a + b


# =========================
# 2. 创建 ToolNode
# =========================

tool_node = ToolNode(
    [add_numbers]
)


# =========================
# 3. 定义模型节点
# =========================

def call_model(state: MessagesState) -> dict:
    """
    模拟调用大模型。

    第一次进入：
    模型请求调用 add_numbers 工具。

    第二次进入：
    读取 ToolMessage，生成最终回答。
    """

    last_message = state["messages"][-1]

    # 如果上一条消息是工具结果，
    # 说明工具已经执行完成
    if isinstance(last_message, ToolMessage):
        return {
            "messages": [
                AIMessage(
                    content=(
                        f"计算完成，工具返回的结果是："
                        f"{last_message.content}"
                    )
                )
            ]
        }

    # 第一次调用模型时，
    # 模拟模型请求调用工具
    return {
        "messages": [
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "add_numbers",
                        "args": {
                            "a": 2,
                            "b": 3
                        },
                        "id": "call_1",
                        "type": "tool_call"
                    }
                ]
            )
        ]
    }


# =========================
# 4. 定义条件路由
# =========================

def route_after_model(state: MessagesState):
    """
    判断模型是否请求调用工具。

    有 tool_calls：
    进入 tool_node。

    没有 tool_calls：
    进入 END。
    """

    last_message = state["messages"][-1]

    if getattr(last_message, "tool_calls", None):
        return "tool_node"

    return END


# =========================
# 5. 创建 Graph 构建器
# =========================

builder = StateGraph(MessagesState)


# =========================
# 6. 添加节点
# =========================

builder.add_node(
    "call_model",
    call_model
)

builder.add_node(
    "tool_node",
    tool_node
)


# =========================
# 7. 添加边
# =========================

# Graph 开始后，先调用模型
builder.add_edge(
    START,
    "call_model"
)


# 模型调用完成后，根据是否有 tool_calls 决定下一步
builder.add_conditional_edges(
    "call_model",
    route_after_model
)


# 工具执行完成后，回到模型
builder.add_edge(
    "tool_node",
    "call_model"
)


# =========================
# 8. 编译 Graph
# =========================

graph = builder.compile()


# =========================
# 9. 运行 Graph
# =========================

if __name__ == "__main__":
    result = graph.invoke(
        {
            "messages": [
                HumanMessage(
                    content="请帮我计算 2 加 3 等于多少"
                )
            ]
        }
    )

    print("\n========== 完整消息 ==========")

    for message in result["messages"]:
        print(
            f"{type(message).__name__}:"
            f" {message.content}"
        )

    print("\n========== 最终回答 ==========")

    print(
        result["messages"][-1].content
    )