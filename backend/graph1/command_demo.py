from typing import TypedDict, Literal

from langgraph.graph import StateGraph, START, END
from langgraph.types import Command


class State(TypedDict):
    question: str
    route: str
    answer: str



def router_node(
    state: State
) -> Command[Literal["knowledge_node", "chat_node"]]: #command是类型  #Literal["knowledge_node", "chat_node"]
#表示 goto 只能是这两个固定值：   

    question = state["question"]

    if "文档" in question or "上传" in question:
        return Command(
            update={
                "route": "knowledge"
            },
            goto="knowledge_node"
        )

    return Command(
        update={
            "route": "chat"
        },
        goto="chat_node"
    )


def knowledge_node(state: State) -> dict:
    return {
        "answer": "这是一个知识库问题"
    }


def chat_node(state: State) -> dict:
    return {
        "answer": "这是一个普通聊天问题"
    }


builder = StateGraph(State)

builder.add_node("router_node", router_node)
builder.add_node("knowledge_node", knowledge_node)
builder.add_node("chat_node", chat_node)

builder.add_edge(START, "router_node")

builder.add_edge("knowledge_node", END)
builder.add_edge("chat_node", END)

graph = builder.compile()


if __name__ == "__main__":
    result = graph.invoke(
        {
            "question": "我上传了多少个文档？",
            "route": "",
            "answer": ""
        }
    )

    print(result)