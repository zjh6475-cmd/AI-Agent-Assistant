from dataclasses import dataclass
from typing import TypedDict

from langgraph.graph import StateGraph, START, END
from langgraph.runtime import Runtime
from langgraph.store.memory import InMemoryStore


# =========================
# 1. 定义 Graph 状态    State 保存本轮 Graph 数据
# =========================

class State(TypedDict):      
    question: str
    answer: str


# =========================
# 2. 定义运行上下文
# =========================

@dataclass
class Context:
    user_id: str


# =========================
# 3. 定义节点
# =========================

def memory_node(
    state: State,
    runtime: Runtime[Context]
) -> dict:
    """
    读取或保存用户的长期记忆。
    """

    user_id = runtime.context.user_id

    namespace = (
        user_id,
        "memories"
    )

    question = state["question"].strip()

    # 去掉中文问号和英文问号
    normalized_question = question.rstrip("？?").strip()

    # 先判断“我叫什么”
    if normalized_question == "我叫什么":
        item = runtime.store.get(
            namespace,
            "user_name"
        )

        if item is None:
            return {
                "answer": "我还不知道你的名字"
            }

        name = item.value["name"]

        return {
            "answer": f"你叫{name}"
        }

    # 再判断“我叫某某”
    if normalized_question.startswith("我叫"):
        name = normalized_question[2:].strip()

        # 防止“我叫什么”被当成名字
        if name == "什么":
            return {
                "answer": "我还不知道你的名字"
            }

        runtime.store.put(
            namespace,
            "user_name",
            {
                "name": name
            }
        )

        return {
            "answer": f"我记住了，你叫{name}"
        }

    return {
        "answer": f"你刚才说的是：{question}"
    }  


# =========================
# 4. 创建 Graph
# =========================

builder = StateGraph(
    State,
    context_schema=Context
)

builder.add_node(
    "memory_node",
    memory_node
)

builder.add_edge(
    START,
    "memory_node"
)

builder.add_edge(
    "memory_node",
    END
)


# =========================
# 5. 创建 Store 并编译 Graph
# =========================

store = InMemoryStore()

graph = builder.compile(
    store=store
)


# =========================
# 6. 运行函数
# =========================

def run_chat(
    thread_id: str,
    user_id: str,
    question: str
):
    result = graph.invoke(
        {
            "question": question
        },
        {
            "configurable": {
                "thread_id": thread_id
            }
        },
        context=Context(
            user_id=user_id
        )
    )

    print()
    print("线程：", thread_id)
    print("用户：", user_id)
    print("问题：", question)
    print("AI：", result["answer"])
    print("-" * 30)


# =========================
# 7. 测试
# =========================

if __name__ == "__main__":

    # user-1 在 thread-1 中保存姓名
    run_chat(
        thread_id="thread-1",
        user_id="user-1",
        question="我叫小黄"
    )

    # 换一个 thread，但还是 user-1
    run_chat(
        thread_id="thread-2",
        user_id="user-1",
        question="我叫什么？"
    )

    # 还是 thread-1，但换成 user-2
    run_chat(
        thread_id="thread-1",
        user_id="user-2",
        question="我叫什么？"
    )