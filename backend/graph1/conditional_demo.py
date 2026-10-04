from typing import TypedDict

from langgraph.graph import StateGraph, START, END


class RouteState(TypedDict):
    question: str
    route: str
    answer: str


def classify_node(state: RouteState) -> dict:
    question = state["question"]

    print("classify_node 读取问题：", question)

    if "文档" in question or "上传" in question:
        return {
            "route": "knowledge"
        }

    return {
        "route": "chat"
    }


def knowledge_node(state: RouteState) -> dict:
    print("进入 knowledge_node")

    return {
        "answer": "这是一个知识库问题"
    }


def chat_node(state: RouteState) -> dict:
    print("进入 chat_node")

    return {
        "answer": "这是一个普通聊天问题"
    }


def route_after_classify(state: RouteState) -> str:
    return state["route"]


builder = StateGraph(
    state_schema=RouteState
)


builder.add_node(
    "classify_node",
    classify_node
)

builder.add_node(
    "knowledge_node",
    knowledge_node
)

builder.add_node(
    "chat_node",
    chat_node
)


builder.add_edge(
    START,
    "classify_node"
)


builder.add_conditional_edges(
    "classify_node",
    route_after_classify,
    {
        "knowledge": "knowledge_node",   #左边路由函数返回的值  右边是真实的节点名称
        "chat": "chat_node"
    }
)


builder.add_edge(
    "knowledge_node",
    END
)

builder.add_edge(
    "chat_node",
    END
)


graph = builder.compile()


if __name__ == "__main__":
    result = graph.invoke(
        {
            "question": "你好，介绍一下 Python",
            "route": "",
            "answer": ""
        }
    )

    print("最终结果：")
    print(result)