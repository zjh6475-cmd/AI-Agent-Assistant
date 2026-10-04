from dataclasses import dataclass
from typing import TypedDict

from langchain_core.messages import (
    AIMessage,
    HumanMessage,
)

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import (
    START,
    END,
    MessagesState,
    StateGraph,
)
from langgraph.runtime import Runtime
from langgraph.store.memory import InMemoryStore


# =========================
# 1. 定义 Graph 的状态
# =========================

class State(MessagesState):
    """
    MessagesState 中已经包含：

    messages: list[BaseMessage]

    并且 messages 自带 add_messages Reducer，
    可以保存多轮对话消息。
    """
    pass


# =========================
# 2. 定义运行时上下文
# =========================

@dataclass
class Context:
    """
    Context 不属于 Graph State。

    它表示本次运行时传入的外部信息，
    这里用 user_id 区分不同用户。
    """

    user_id: str


# =========================
# 3. 定义节点
# =========================

def memory_node(
    state: State,
    runtime: Runtime[Context],
) -> dict:
    """
    同时使用：

    1. state：
       当前 thread 的对话状态

    2. runtime.context：
       当前用户的身份信息

    3. runtime.store：
       跨 thread 保存的长期记忆
    """

    # -------------------------
    # A. 从 Checkpointer 恢复的 State 中读取消息
    # -------------------------

    messages = state["messages"]

    print("当前线程消息数量：", len(messages))

    last_message = messages[-1]

    question = str(last_message.content).strip()

    print("当前问题：", question)

    # -------------------------
    # B. 从 Context 中读取 user_id
    # -------------------------

    user_id = runtime.context.user_id

    print("当前用户：", user_id)

    # -------------------------
    # C. 根据 user_id 创建 Store 命名空间
    # -------------------------

    namespace = (
        user_id,
        "memories",
    )

    # 去除中英文问号，方便判断
    normalized_question = question.rstrip("？?").strip()

    # -------------------------
    # D. 查询长期记忆
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
    # E. 保存长期记忆
    # -------------------------

    elif normalized_question.startswith("我叫"):
        name = normalized_question[2:].strip()

        # 防止把“我叫什么”误认为是在设置名字
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
    # F. 普通问题
    # -------------------------

    else:
        answer = f"你刚才说的是：{question}"

    # 返回新的 AI 消息
    return {
        "messages": [
            AIMessage(content=answer)
        ]
    }


# =========================
# 4. 创建 Graph
# =========================

builder = StateGraph(
    State,
    context_schema=Context,
)


# 添加节点
builder.add_node(
    "memory_node",
    memory_node,
)


# 定义固定执行流程
builder.add_edge(
    START,
    "memory_node",
)

builder.add_edge(
    "memory_node",
    END,
)


# =========================
# 5. 创建两种持久化组件
# =========================

# 保存当前 thread 的 Graph 状态
checkpointer = InMemorySaver()

# 保存跨 thread 的长期记忆
store = InMemoryStore()


# 同时启用 Checkpointer 和 Store
graph = builder.compile(
    checkpointer=checkpointer,
    store=store,
)


# =========================
# 6. 封装运行函数
# =========================

def run_chat(
    thread_id: str,
    user_id: str,
    question: str,
):
    """
    thread_id：
        当前对话线程编号，
        用于 Checkpointer 查找会话状态。

    user_id：
        当前用户编号，
        用于 Store 查找长期记忆。
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

    print(
    "当前线程状态消息数量：",
    len(snapshot.values["messages"])
    )

    print(
    "当前线程下一步：",
    snapshot.next
)

    answer = result["messages"][-1].content

    print()
    print("线程：", thread_id)
    print("用户：", user_id)
    print("问题：", question)
    print("AI：", answer)
    print("-" * 40)

    return result


# =========================
# 7. 测试
# =========================

if __name__ == "__main__":

    # 用户 user-1 在线程 thread-1 中告诉 AI 自己的名字
    run_chat(
        thread_id="thread-1",
        user_id="user-1",
        question="我叫小黄",
    )

    # 同一个用户，但是换了一个线程
    # 这里应该仍然能够读取 Store 中的小黄
    run_chat(
        thread_id="thread-2",
        user_id="user-1",
        question="我叫什么？",
    )

    # 换成另一个用户
    # user-2 不应该读取到 user-1 的名字
    run_chat(
        thread_id="thread-3",
        user_id="user-2",
        question="我叫什么？",
    )

    # 回到 thread-1
    # 这里可以读取 thread-1 保存的对话状态
    run_chat(
        thread_id="thread-1",
        user_id="user-1",
        question="你好",
    )