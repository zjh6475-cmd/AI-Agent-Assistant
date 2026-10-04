from typing import TypedDict
from langgraph.graph import StateGraph, START, END


class LoopState(TypedDict):
    count: int
    result: str


def work_node(state: LoopState):
    count = state["count"]

    print("当前执行次数：", count)

    return {
        "count": count + 1,
        "result": f"第 {count + 1} 次执行"
    }


def route_after_work(state: LoopState):
    if state["count"] < 3:
        return "work_node"

    return END


builder = StateGraph(LoopState)

builder.add_node(
    "work_node",
    work_node
)

builder.add_edge(
    START,
    "work_node"
)

builder.add_conditional_edges(
    "work_node",
    route_after_work
)

graph = builder.compile()

result = graph.invoke(
    {
        "count": 0,
        "result": ""
    }
)

print(result)