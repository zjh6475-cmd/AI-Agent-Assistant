from typing import TypedDict, Annotated
from operator import add

from langgraph.graph import StateGraph, START, END
import time

class ParallelState(TypedDict):
    question: str
    intent: str
    context: str
    logs: Annotated[list[str], add]


def classify_node(state: ParallelState) -> dict:
    print("classify_node 读取：", state["question"])

    return {
        "intent": "knowledge",
        "logs": ["问题分类完成"]
    }


def context_node(state: ParallelState) -> dict:
    print("context_node 读取：", state["question"])

    return {
        "context": "用户已有知识库文档",
        "logs": ["用户上下文加载完成"]
    }


def merge_node(state: ParallelState) -> dict:
    print("merge_node 读取到完整状态：")
    print(state)

    return {}


builder = StateGraph(
    state_schema=ParallelState
)


builder.add_node(
    "classify_node",
    classify_node
)

builder.add_node(
    "context_node",
    context_node
)

builder.add_node(
    "merge_node",
    merge_node
)


# START 同时连接两个节点
builder.add_edge(
    START,
    "classify_node"
)

builder.add_edge(
    START,
    "context_node"
)


# 两个并行节点都完成后，再进入 merge_node
builder.add_edge(
    "classify_node",
    "merge_node"
)

builder.add_edge(
    "context_node",
    "merge_node"
)

builder.add_edge(
    "merge_node",
    END
)


graph = builder.compile()


if __name__ == "__main__":
    result = graph.invoke(
        {
            "question": "我上传了多少个文档？",
            "intent": "",
            "context": "",
            "logs": []
        }
    )

    print("最终结果：")
    print(result)