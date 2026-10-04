from dataclasses import dataclass

from langchain_core.messages import AIMessage, HumanMessage
from langgraph.graph import MessagesState, StateGraph, START, END
from langgraph.runtime import Runtime
from langgraph.store.memory import InMemoryStore


@dataclass   #Context 保存本次请求的用户身份  本次运行的上下文信息
class Context:
    user_id: str


def call_model(
    state: MessagesState,
    runtime: Runtime[Context],
) -> dict:
    """
    模型节点：

    1. 从 Runtime 中获取 user_id
    2. 根据 user_id 查询 Store
    3. 读取用户回答偏好
    4. 根据偏好生成回答
    """

    user_id = runtime.context.user_id

    namespace = (  #Store 使用用户身份隔离数据
        "user",
        user_id,
    )

    preference_item = runtime.store.get(   #节点读取偏好
        namespace, 
        "preferences",
    )

    if preference_item is None:
        style = "普通"
    else:
        style = preference_item.value.get(
            "style",
            "普通",
        )

    question = str(
        state["messages"][-1].content
    )

    if style == "简洁":
        answer = (
            f"简洁回答：{question} "
            "是一个需要结合具体场景理解的问题。"
        )
    else:
        answer = (
            f"普通回答：{question} "
            "这是一个可以从基础概念、使用场景和实际案例"
            "三个方面进行解释的问题。"
        )

    return {
        "messages": [
            AIMessage(content=answer)
        ]
    }


def build_graph(store):
    builder = StateGraph(
        MessagesState,
        context_schema=Context,
    )

    builder.add_node(
        "call_model",
        call_model,
    )

    builder.add_edge(
        START,
        "call_model",
    )

    builder.add_edge(
        "call_model",
        END,
    )

    return builder.compile(
        store=store,
    )


def run_chat(
    graph,
    user_id: str,
    question: str,
):
    result = graph.invoke(
        {
            "messages": [
                HumanMessage(
                    content=question
                )
            ]
        },
        context=Context(
            user_id=user_id
        ),
    )

    print(
        f"{user_id}："
        f"{result['messages'][-1].content}"
    )


def main():
    store = InMemoryStore()

    graph = build_graph(store)

    user_namespace = (
        "user",
        "user-1",  
    )

    store.put(
        user_namespace,
        "preferences",
        {
            "style": "简洁" 
        },
    )

    run_chat(
        graph,
        user_id="user-1",
        question="什么是 Python？",
    )

    run_chat(
        graph,
        user_id="user-2",
        question="什么是 Python？",
    )


if __name__ == "__main__":
    main()