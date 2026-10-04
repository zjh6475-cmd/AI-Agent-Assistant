import asyncio
from typing import TypedDict

from langgraph.graph import StateGraph, START, END


class TimeoutState(TypedDict):
    task: str
    result: str


async def slow_service(state: TimeoutState) -> dict:   #slow_service() 模拟外部服务，
    #asyncio.wait_for() 负责设置超时时间。
    """
    模拟一个很慢的外部服务。
    例如：
    - DeepSeek API
    - 向量检索
    - 第三方接口
    """

    print("slow_service：开始执行")

    # 模拟外部服务需要 3 秒才能返回
    await asyncio.sleep(3)    #等待 DeepSeek 返回  等待数据库响应  等待网络接口返回



    print("slow_service：执行完成")

    return {
        "result": "外部服务正常返回"
    }


async def timeout_node(state: TimeoutState) -> dict:
    """
    给 slow_service 增加 1 秒超时限制。
    """

    print("timeout_node：开始执行")

    try:
        result = await asyncio.wait_for(
            slow_service(state),
            timeout=1
        )

        return result

    except asyncio.TimeoutError:
        print("timeout_node：执行超时")

        return {
            "result": "节点执行超时，返回兜底结果"
        }


builder = StateGraph(TimeoutState)


builder.add_node(
    "timeout_node",
    timeout_node
)


builder.add_edge(
    START,
    "timeout_node"
)


builder.add_edge(
    "timeout_node",
    END
)


graph = builder.compile()


async def main():
    result = await graph.ainvoke(
        {
            "task": "调用外部服务",
            "result": ""
        }
    )

    print("最终结果：")
    print(result)


if __name__ == "__main__":
    asyncio.run(main())