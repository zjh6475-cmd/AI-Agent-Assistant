from langchain_core.messages import (
    AIMessage,
    HumanMessage,
)

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import (
    END,
    START,
    MessagesState,
    StateGraph,
)


# =========================
# 1. 定义节点
# =========================

def assistant_node(state: MessagesState) -> dict:
    """
    读取当前线程中的全部消息，
    根据用户最后一句话生成回答。
    """

    print("当前线程中的消息：")

    for message in state["messages"]:
        print(
            type(message).__name__,
            "=>",
            repr(message.content)
        )

    last_message = state["messages"][-1]

    question = str(last_message.content).strip()

    normalized_question = question.rstrip("？?")

    if normalized_question == "我叫什么":

        user_names = []

        for message in state["messages"]:

            if not isinstance(message, HumanMessage):
                continue

            content = str(message.content).strip()
            normalized_content = content.rstrip("？?")

            if (
                normalized_content.startswith("我叫")
                and normalized_content != "我叫什么"
            ):
                name = normalized_content[2:].strip()
                user_names.append(name)

        print("找到的名字：", user_names)

        if user_names:
            answer = f"你叫{user_names[-1]}"
        else:
            answer = "我还不知道你的名字"

    else:
        answer = f"我记住了：{question}"

    return {
        "messages": [
            AIMessage(content=answer)
        ]
    }


# =========================
# 2. 创建 Graph
# =========================

def build_graph(checkpointer):
    """
    使用传入的 Checkpointer 编译 Graph。
    """

    builder = StateGraph(MessagesState)

    builder.add_node(
        "assistant_node",
        assistant_node
    )

    builder.add_edge(
        START,
        "assistant_node"
    )

    builder.add_edge(
        "assistant_node",
        END
    )

    return builder.compile(
        checkpointer=checkpointer
    )


# =========================
# 3. 执行一次聊天
# =========================

def run_chat(
    graph,
    thread_id: str,
    question: str
):
    """
    使用指定 thread_id 执行一次聊天。
    """

    config = {
        "configurable": {
            "thread_id": thread_id
        }
    }

    result = graph.invoke(
        {
            "messages": [
                HumanMessage(content=question)
            ]
        },
        config
    )
        # 查看当前线程最新的 Graph 状态
    snapshot = graph.get_state(config)

    print()
    print("当前状态：")
    print(snapshot.values)

    print("下一步节点：")
    print(snapshot.next)
    

    answer = result["messages"][-1].content

    print()
    print("线程：", thread_id)
    print("用户：", question)
    print("AI：", answer)
    print("-" * 30)
    
    
def inspect_history(graph, thread_id: str):
    config = {
        "configurable": {
            "thread_id": thread_id
        }
    }

    print()
    print("状态历史：")

    for index, snapshot in enumerate(
        graph.get_state_history(config),
        start=1
    ):
        print(f"第 {index} 个快照")
        print("checkpoint_id：", snapshot.config["configurable"]["checkpoint_id"])
        print("下一步节点：", snapshot.next)
        print("消息数量：", len(snapshot.values.get("messages", [])))
        print("状态内容：", snapshot.values)
        print("-" * 40)    




# =========================
# 4. 使用 SQLite Checkpointer
# =========================

def main():

    database_path = "checkpoints.sqlite"   #表示 LangGraph 的状态保存到：  checkpoints.sqlite

    with SqliteSaver.from_conn_string(
        database_path
    ) as checkpointer:

        graph = build_graph(
            checkpointer
        )
        run_chat(
        graph,
        "sqlite-thread-1",
        "我叫什么？"
        )

        inspect_history(
        graph,
        "sqlite-thread-1"
        )

        question = input(
            "请输入问题："
        ).strip()

        run_chat(
            graph,
            "sqlite-thread-1",
            question
        )
        
        
        




if __name__ == "__main__":
    main()