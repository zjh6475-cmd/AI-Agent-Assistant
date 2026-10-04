import time

from typing import TypedDict

from langgraph.cache.memory import InMemoryCache
from langgraph.graph import StateGraph, START, END
from langgraph.types import CachePolicy


class KnowledgeState(TypedDict):
    user_id: int
    question: str
    answer: str


def knowledge_cache_key(state: KnowledgeState) -> str:  #这个函数负责告诉 LangGraph：什么情况下可以认为是“同一个请求”？
    """
    自定义缓存键。

    同时考虑：
    1. user_id：区分不同用户
    2. question：区分不同问题
    """

    user_id = state["user_id"]

    question = state["question"].strip().lower()

    return f"user_id={user_id}|question={question}"


def knowledge_node(state: KnowledgeState) -> dict:
    """
    模拟知识库查询或模型调用。
    """

    print(
        f"knowledge_node：用户 {state['user_id']} 正在真正查询"
    )

    # 模拟耗时操作
    time.sleep(2)

    answer = (
        f"用户 {state['user_id']} 的查询结果："
        f"{state['question']}"
    )

    print("knowledge_node：查询完成")

    return {
        "answer": answer
    }




builder = StateGraph(KnowledgeState)


builder.add_node(
    "knowledge_node",
    knowledge_node,
    cache_policy=CachePolicy(
        ttl=60,
        key_func=knowledge_cache_key
        
    )
)

from langgraph.types import (
    RetryPolicy,
    CachePolicy
)

 
builder.set_node_defaults(    #所有节点默认重试 3 次    所有节点默认缓存 60 秒
    retry_policy=RetryPolicy(
        max_attempts=3
    ),
    cache_policy=CachePolicy(  
        ttl=60
    )
)
#builder.add_node(     #sql_node：最多重试 1 次 单独配置
#    "sql_node",
#    sql_node,
#    retry_policy=RetryPolicy(
##        max_attempts=1
#    )
#)
builder.add_edge(
    START,
    "knowledge_node"
)


builder.add_edge(
    "knowledge_node",
    END
)


graph = builder.compile(
    cache=InMemoryCache()
)


def run_case(user_id: int, question: str):
    print("=" * 50)

    result = graph.invoke(
        {
            "user_id": user_id,
            "question": question,
            "answer": ""
        },
        stream_mode="updates"
    )

    print("最终结果：")
    print(result)


if __name__ == "__main__":
    print("用户1第一次提问")
    run_case(
        user_id=1,
        question="Python 是什么？"
    )

    print("用户1第二次提问相同问题")
    run_case(
        user_id=1,
        question="Python 是什么？"
    )

    print("用户2第一次提问相同问题")
    run_case(
        user_id=2,
        question="Python 是什么？"
    )