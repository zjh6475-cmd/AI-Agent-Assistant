from langchain_core.messages import (
    AIMessage,
    HumanMessage,
)

from langgraph.checkpoint.memory import InMemorySaver
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

    # 获取最后一条消息
    last_message = state["messages"][-1]

    question = str(last_message.content).strip()

    # 兼容中文问号和英文问号
    normalized_question = question.rstrip("？?")

    # 用户询问自己的名字
    if normalized_question == "我叫什么":

        user_names = []

        # 遍历当前线程中的所有消息
        for message in state["messages"]:

            # 只处理用户消息，不处理 AI 消息
            if not isinstance(message, HumanMessage):
                continue

            content = str(message.content).strip()

            # 去掉结尾的中英文问号
            normalized_content = content.rstrip("？?")

            # 防止把“我叫什么”误认为“我叫 + 什么”
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

    # 返回新的 AI 消息
    return {
        "messages": [
            AIMessage(content=answer)
        ]
    }


# =========================
# 2. 创建 Graph 构建器
# =========================

builder = StateGraph(MessagesState)


# 添加 assistant_node 节点
builder.add_node(
    "assistant_node",
    assistant_node
)


# =========================
# 3. 定义执行流程
# =========================

# START → assistant_node
builder.add_edge(
    START,
    "assistant_node"
)


# assistant_node → END
builder.add_edge(
    "assistant_node",
    END
)


# =========================
# 4. 创建 Checkpointer
# =========================

checkpointer = InMemorySaver()


# 编译 Graph 时传入 Checkpointer
graph = builder.compile(
    checkpointer=checkpointer
)


# =========================
# 5. 封装运行函数
# =========================

def run_chat(
    thread_id: str,
    question: str
):
    """
    thread_id：当前对话线程编号
    question：本轮用户问题
    """

    # thread_id 必须放在 configurable 中
    config = {
        "configurable": {
            "thread_id": thread_id
        }
    }

    # 调用 Graph
    result = graph.invoke(
        {
            "messages": [
                HumanMessage(content=question)
            ]
        },
        config
    )

    # 获取最后一条 AI 消息
    answer = result["messages"][-1].content

    print(f"线程：{thread_id}")
    print(f"用户：{question}")
    print(f"AI：{answer}")
    print("-" * 30)

    return result



def inspect_thread(thread_id: str):
    """
    查看某个线程最新保存的状态。
    """

    config = {
        "configurable": {
            "thread_id": thread_id
        }
    }

    # 读取当前线程最新的状态快照
    snapshot = graph.get_state(config)

    print()
    print("========== 当前线程状态 ==========")

    print("线程编号：")
    print(thread_id)

    print("当前保存的消息：")

    for message in snapshot.values["messages"]:
        print(
            type(message).__name__,
            "=>",
            message.content
        )

    print("下一步节点：")
    print(snapshot.next)

    print("状态元数据：")
    print(snapshot.metadata)

    print("Checkpoint 配置：")
    print(snapshot.config)

    print("==================================")
    
    
def inspect_thread_history(thread_id: str):
    """
    查看指定线程经历过的所有 checkpoint。
    """

    config = {
        "configurable": {
            "thread_id": thread_id
        }
    }

    # 获取当前线程的全部状态历史
    history = list(
        graph.get_state_history(config)
    )

    print()
    print("========== 状态历史 ==========")
    print("线程编号：", thread_id)
    print("Checkpoint 数量：", len(history))

    for index, snapshot in enumerate(history):

        print()
        print(f"---------- 第 {index + 1} 个快照 ----------")

        print("执行步骤：")
        print(
            snapshot.metadata.get(
                "step"
            )
        )

        print("下一步节点：")
        print(snapshot.next)

        print("Checkpoint ID：")
        print(
            snapshot.config["configurable"].get(
                "checkpoint_id"
            )
        )

        print("当前消息数量：")
        print(
            len(snapshot.values.get("messages", []))
        )

        print("当前消息内容：")

        for message in snapshot.values.get(
            "messages",
            []
        ):
            print(
                type(message).__name__,
                "=>",
                message.content
            )

    print("================================")    

# =========================
# 6. 测试
# =========================

if __name__ == "__main__":

    # 第一次调用，保存“小黄”这个名字
    run_chat(
        "test-thread-1",
        "我叫小黄"
    )

    # 使用相同 thread_id，可以读取之前的名字
    run_chat(
        "test-thread-1",
        "我叫什么？"
    )

    # 使用新的 thread_id，无法读取 test-thread-1 的历史状态
    run_chat(
        "test-thread-2",
        "我叫什么？"
    )
    
    inspect_thread(
        "test-thread-1"
    )
    
    inspect_thread_history(
        "test-thread-1"
    )