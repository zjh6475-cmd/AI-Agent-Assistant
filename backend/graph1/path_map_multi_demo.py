from typing import TypedDict,Annotated
from operator import add

from langgraph.graph import StateGraph,START,END

class State(TypedDict):
    question:str
    logs:Annotated[list[str],add]
    
def router_node(state:State) ->dict:
    print("router_node：开始判断问题")

    return {
        "logs": ["问题分类完成"]
    }
    
def route_after_router(state: State) -> list[str]:
    question = state["question"]

    if "多少" in question or "统计" in question:
        return ["knowledge", "sql"]

    return ["chat"]    


def knowledge_node(state: State) -> dict:
    print("knowledge_node：执行知识库查询")

    return {
        "logs": ["知识库查询完成"]
    }


def sql_node(state: State) -> dict:
    print("sql_node：执行 SQL 查询")

    return {
        "logs": ["SQL 查询完成"]
    }

def chat_node(state: State) -> dict:
    print("chat_node：执行普通聊天")

    return {
        "logs": ["普通聊天完成"]
    }


def merge_node(state: State) -> dict:
    print("merge_node：汇总并行结果")

    return {
        "logs": ["并行结果汇总完成"]
    }


builder = StateGraph(State)

builder.add_node("router_node", router_node)
builder.add_node("knowledge_node", knowledge_node)
builder.add_node("sql_node", sql_node)
builder.add_node("chat_node", chat_node)
builder.add_node("merge_node", merge_node, defer=True)


builder.add_edge(START, "router_node")


builder.add_conditional_edges(
    "router_node",
    route_after_router,
    {
        "knowledge": "knowledge_node",
        "sql": "sql_node",
        "chat": "chat_node",
    }
)


builder.add_edge(
    [
        "knowledge_node",
        "sql_node"
    ],
    "merge_node"
)
builder.add_edge("chat_node", END)
builder.add_edge("merge_node", END)


graph = builder.compile() 


if __name__ == "__main__":
    result = graph.invoke(
        {
            "question": "我上传了多少个文档？",
            "logs": []
        }
    )

    print("最终结果：")
    print(result)