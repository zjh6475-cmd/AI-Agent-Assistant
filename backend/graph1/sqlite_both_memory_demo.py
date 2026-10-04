from dataclasses import dataclass

from langchain_core.messages import (
    AIMessage,
    HumanMessage,
)
from langgraph.store.sqlite import SqliteStore
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import (
    START,
    END,
    MessagesState,
    StateGraph,
)
from langgraph.runtime import Runtime


# =========================
# 1. 定义运行时上下文
# =========================

@dataclass
class Context:
    """
    Context 不属于 Graph State。

    user_id 用于访问当前用户的长期记忆。
    """

    user_id: str


# =========================
# 2. 定义节点
# =========================

def memory_node(
    state: MessagesState,
    runtime: Runtime[Context],
) -> dict:
    """
    这个节点同时使用两种数据：

    state：
        从 Checkpointer 恢复的当前线程状态

    runtime.context：
        本次请求传入的用户身份

    runtime.store：
        跨线程保存的长期记忆
    """

    # 当前节点执行时，AI 还没有生成本轮回复
    messages = state["messages"]

    print("当前线程消息数量：", len(messages))

    last_message = messages[-1]

    question = str(last_message.content).strip()

    print("当前问题：", question)

    # -------------------------
    # 读取当前用户身份
    # -------------------------

    user_id = runtime.context.user_id

    print("当前用户：", user_id)

    # -------------------------
    # 创建 Store 命名空间
    # -------------------------

    namespace = (
        user_id,
        "memories",
    )

    normalized_question = (
        question.rstrip("？?")
        .strip()
    )

    # -------------------------
    # 查询长期记忆
    # -------------------------

    if normalized_question == "我叫什么":

        item = runtime.store.get(
            namespace,
            "user_name",
        )

        if item is None:
            answer = "我还不知道你的名字"
        else:
            name = item.value["name"]
            answer = f"你叫{name}"

    # -------------------------
    # 保存长期记忆
    # -------------------------

    elif normalized_question.startswith("我叫"):

        name = normalized_question[2:].strip()

        # 防止把“我叫什么”误认为设置名字
        if name == "什么":
            answer = "我还不知道你的名字"
        else:
            runtime.store.put(
                namespace,
                "user_name",
                {
                    "name": name
                },
            )

            answer = f"我记住了，你叫{name}"

    # -------------------------
    # 普通问题
    # -------------------------

    else:
        answer = f"你刚才说的是：{question}"

    # 返回本轮 AI 消息
    return {
        "messages": [
            AIMessage(content=answer)
        ]
    }


# =========================
# 3. 创建 Graph
# =========================

def build_graph(
    checkpointer,
    store,
):
    builder = StateGraph(
        MessagesState,
        context_schema=Context,
    )

    builder.add_node(
        "memory_node",
        memory_node,
    )

    builder.add_edge(
        START,
        "memory_node",
    )

    builder.add_edge(
        "memory_node",
        END,
    )

    return builder.compile(
        checkpointer=checkpointer,
        store=store,
    )


# =========================
# 4. 执行一次聊天
# =========================

def run_chat(
    graph,
    thread_id: str,
    user_id: str,
    question: str,
):
    """
    thread_id：
        交给 Checkpointer，查找当前线程状态。

    user_id：
        交给 Store，查找当前用户的长期记忆。
    """

    config = {
        "configurable": {
            "thread_id": thread_id,
        }
    }

    context = Context(
        user_id=user_id,
    )

    result = graph.invoke(
        {
            "messages": [
                HumanMessage(
                    content=question
                )
            ]
        },
        config,
        context=context,
    )

    snapshot = graph.get_state(config)

    answer = result["messages"][-1].content

    print()
    print("线程：", thread_id)
    print("用户：", user_id)
    print("问题：", question)
    print("AI：", answer)
    print(
        "执行完成后的消息数量：",
        len(snapshot.values["messages"]),
    )
    print(
        "下一步节点：",
        snapshot.next,
    )
    print("-" * 40)

    return result


# =========================
# 5. 主程序
# =========================

def main():

    checkpoint_path = "checkpoints_both.sqlite"
    memory_path = "memories.sqlite"

    with SqliteStore.from_conn_string(
        memory_path
    ) as store:

        # 第一次使用 SQLite Store 时创建表
        store.setup()

        with SqliteSaver.from_conn_string(
            checkpoint_path
        ) as checkpointer:

            graph = build_graph(
                checkpointer=checkpointer,
                store=store,
            )

            run_chat(
                graph,
                thread_id="thread-1",
                user_id="user-1",
                question="我叫小黄",
            )

            run_chat(
                graph,
                thread_id="thread-2",
                user_id="user-1",
                question="我叫什么？",
            )

            run_chat(
                graph,
                thread_id="thread-3",
                user_id="user-2",
                question="我叫什么？",
            )


if __name__ == "__main__":
    main()