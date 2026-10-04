from typing import TypedDict

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import StateGraph, START, END
from langgraph.types import interrupt, Command


class ApprovalState(TypedDict, total=False):
    action: str
    approved: bool
    result: str


def approval_node(
    state: ApprovalState,
) -> dict:
    """
    危险操作确认节点。
    """

    print("进入 approval_node")

    decision = interrupt(
        {
            "type": "approval",
            "message": "这是一个危险操作，是否确认执行？",
            "action": state["action"],
        }
    )

    print("用户确认结果：", decision)

    return {
        "approved": bool(decision)
    }


def execute_node(
    state: ApprovalState,
) -> dict:
    """
    执行实际操作的节点。
    """

    print("进入 execute_node")

    if not state.get("approved", False):
        return {
            "result": "用户拒绝操作，已取消执行"
        }

    return {
        "result": f"操作已执行：{state['action']}"
    }


def build_graph(checkpointer):
    builder = StateGraph(ApprovalState)

    builder.add_node(
        "approval_node",
        approval_node,
    )

    builder.add_node(
        "execute_node",
        execute_node,
    )

    builder.add_edge(
        START,
        "approval_node",
    )

    builder.add_edge(
        "approval_node",
        "execute_node",
    )

    builder.add_edge(
        "execute_node",
        END,
    )

    return builder.compile(
        checkpointer=checkpointer,
    )


def main():
    checkpointer = InMemorySaver()

    graph = build_graph(
        checkpointer
    )

    config = {
        "configurable": {
            "thread_id": "approval-thread-1"
        }
    }

    first_result = graph.invoke(
        {
            "action": "删除文档 document-1"
        },
        config,
    )

    print()
    print("第一次运行结果：")
    print(first_result)

    print()
    print("Graph 已暂停，等待用户确认")

    user_confirm = input(
        "请输入 yes 确认，其他内容表示拒绝："
    )

    approved = user_confirm.lower() == "yes"

    final_result = graph.invoke(
        Command(
            resume=approved
        ),
        config,
    )

    print()
    print("恢复后的最终结果：")
    print(final_result)


if __name__ == "__main__":
    main()