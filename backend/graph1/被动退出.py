from typing import TypedDict

from langgraph.graph import StateGraph, START
from langgraph.errors import GraphRecursionError


class LoopState(TypedDict):
    count: int


def loop_node(state: LoopState) -> dict:
    print("当前执行：", state["count"])

    return {
        "count": state["count"] + 1
    }


builder = StateGraph(LoopState)

builder.add_node(
    "loop_node",
    loop_node
)

builder.add_edge(
    START,
    "loop_node"
)

# 节点执行完后回到自己，形成无限循环
builder.add_edge(
    "loop_node",
    "loop_node"
)

graph = builder.compile()



#关键  达到最大步骤 → GraphRecursionError → 异常中断
try:
    result = graph.invoke(
        {
            "count": 0
        },
        config={
            "recursion_limit": 5
        }
    )

    print(result)

except GraphRecursionError as error:
    print("图执行超过最大步骤，已经被中断")
    print(error)