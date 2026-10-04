from typing import TypedDict

from langgraph.graph import StateGraph, START, END
from langgraph.types import RetryPolicy


class TemporaryError(Exception):
    pass


class State(TypedDict):
    result: str


attempt_count = 0


def unstable_node(state: State) -> dict:
    global attempt_count

    attempt_count += 1

    print("当前尝试次数：", attempt_count)

    if attempt_count < 3:
        raise TemporaryError("临时网络错误")

    return {
        "result": "执行成功"
    }


builder = StateGraph(State)

builder.add_node(
    "unstable_node",
    unstable_node,
    retry_policy=RetryPolicy(
        max_attempts=3,    #总共最多尝试 3 次。
        initial_interval=0.1,
        backoff_factor=1.0,
        jitter=False,
        retry_on=TemporaryError   #只有遇到 TemporaryError 时才自动重试。   遇到其他的不重试直接抛出
    )
)

builder.add_edge(
    START,
    "unstable_node"
)

builder.add_edge(
    "unstable_node",
    END
)

graph = builder.compile()

result = graph.invoke(
    {
        "result": ""
    }
)

print(result)