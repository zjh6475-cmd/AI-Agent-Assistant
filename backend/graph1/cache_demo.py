import time

from typing import TypedDict
 
from langgraph.cache.memory import InMemoryCache   #表示使用内存缓存。  程序运行期间有效
from langgraph.graph import StateGraph, START, END
from langgraph.types import CachePolicy     #导入缓存策略


class CacheState(TypedDict):
    number: int
    result: int


def expensive_node(state: CacheState) -> dict:
    """
    模拟一个执行成本较高的节点。
    """

    print("expensive_node：真正执行节点逻辑")

    # 模拟耗时操作，例如：
    # - 调用模型
    # - 向量检索
    # - 数据库查询
    time.sleep(2)

    result = state["number"] * 2

    print("expensive_node：执行完成")

    return {
        "result": result
    }


builder = StateGraph(CacheState)


builder.add_node(    #expensive_node 节点允许使用缓存
    "expensive_node",
    expensive_node,
    cache_policy=CachePolicy(   #表示缓存有效时间为 10 秒。
        ttl=10     
    )
)


builder.add_edge(
    START,
    "expensive_node"
)


builder.add_edge(
    "expensive_node",
    END
)


graph = builder.compile(    # 节点配置缓存   两个同时存在  给这个 Graph 安装一个缓存系统
    cache=InMemoryCache()          
)         


def run_graph(number: int):
    start_time = time.perf_counter()

    result = graph.invoke(
        {
            "number": number,
            "result": 0
        },
        stream_mode="updates"
    )

    end_time = time.perf_counter()

    print("本次结果：")
    print(result)

    print(
        f"本次耗时：{end_time - start_time:.2f} 秒"
    )

    print("-" * 40)


if __name__ == "__main__":
    print("第一次执行：")
    run_graph(5)

    print("第二次执行相同输入：")
    run_graph(5)

    print("第三次执行不同输入：")
    run_graph(6)