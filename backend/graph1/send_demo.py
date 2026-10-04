#Map → 多次处理 → Reduce用户上传多个文档
#      ↓
#动态拆分文档
#      ↓
#每个文档分别解析和总结
#      ↓
#汇总所有文档结果

from typing import TypedDict, Annotated
from operator import add

from langgraph.graph import StateGraph, START, END
from langgraph.types import Send


class OverallState(TypedDict, total=False):
    questions: list[str]
    question: str
    answers: Annotated[list[str], add]


def split_node(state: OverallState) -> dict:
    print("split_node：准备拆分问题")

    return {
        "answers": []
    }


def route_questions(state: OverallState):
    questions = state["questions"]

    return [
        Send(
            "answer_node",  #将question in questions的问题发送到answer_node"中
            {
                "question": question
            }
        )
        for question in questions
    ]
    
def answer_node(state: OverallState) -> dict:
    question = state["question"]

    print("answer_node 正在处理：", question)

    return {
        "answers": [
            f"已处理问题：{question}"
        ]
    }


builder = StateGraph(OverallState)

builder.add_node("split_node", split_node)
builder.add_node("answer_node", answer_node)

builder.add_edge(START, "split_node")

builder.add_conditional_edges(
    "split_node",
    route_questions
)

builder.add_edge("answer_node", END)

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
    print(result)    