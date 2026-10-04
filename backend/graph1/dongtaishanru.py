from typing import TypedDict, Annotated
from operator import add

from langgraph.graph import StateGraph, START, END
from langgraph.types import Send


class State(TypedDict, total=False):
    questions: list[str]
    question: str
    answers: Annotated[list[str], add]
    final_answer: str


def dispatch_node(state: State) -> dict:
    print("dispatch_node：开始分发任务")

    return {
        "answers": []
    }


def route_questions(state: State):
    return [
        Send(
            "answer_node",
            {
                "question": question
            }
        )
        for question in state["questions"]
    ]


def answer_node(state: State) -> dict:
    question = state["question"]

    print("answer_node：处理", question)

    return {
        "answers": [
            f"已经回答：{question}"
        ]
    }


def merge_node(state: State) -> dict:
    print("merge_node：汇总所有回答")

    return {
        "final_answer": "\n".join(
            state["answers"]
        )
    }


builder = StateGraph(State)

builder.add_node("dispatch_node", dispatch_node)
builder.add_node("answer_node", answer_node)
builder.add_node("merge_node", merge_node)

builder.add_edge(START, "dispatch_node")

builder.add_conditional_edges(
    "dispatch_node",
    route_questions
)

builder.add_edge(
    "answer_node",
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
            "questions": [
                "什么是 Python？",
                "什么是 FastAPI？",
                "什么是 LangGraph？"
            ]
        }
    )

    print("最终结果：")
    print(result["final_answer"])