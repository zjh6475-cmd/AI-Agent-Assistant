from typing import TypedDict

from langgraph.graph import StateGraph, START, END


class ErrorState(TypedDict):
    question: str
    should_fail: bool
    answer: str
    error: str


def call_service(state: ErrorState) -> dict:
    """
    模拟调用 DeepSeek 或其他外部服务。
    """

    print("call_service：开始调用外部服务")

    try:
        if state["should_fail"]:
            raise ConnectionError(
                "模拟 DeepSeek 网络连接失败"
            )

        answer = f"模型正常回答：{state['question']}"

        print("call_service：调用成功")

        return {
            "answer": answer,
            "error": ""
        }

    except (ConnectionError, TimeoutError) as exc:        
        print("call_service：调用失败")

        return {
            "error": str(exc)
        }


def route_after_service(state: ErrorState) -> str:
    """
    根据 error 字段决定下一步走哪条路径。
    """

    if state["error"]:
        return "error_node"

    return "success_node"


def success_node(state: ErrorState) -> dict:
    """
    成功处理节点。
    """

    print("success_node：进入成功分支")

    return {
        "answer": state["answer"]
    }


def error_node(state: ErrorState) -> dict:
    """
    错误处理节点。
    """

    print("error_node：进入错误处理分支")

    return {
        "answer": "外部服务暂时不可用，请稍后重试"
    }


builder = StateGraph(ErrorState)


builder.add_node(
    "call_service",
    call_service
)

builder.add_node(
    "success_node",
    success_node
)

builder.add_node(
    "error_node",
    error_node
)


builder.add_edge(
    START,
    "call_service"
)


builder.add_conditional_edges(
    "call_service",
    route_after_service,
    {
        "success_node": "success_node",
        "error_node": "error_node"
    }
)


builder.add_edge(
    "success_node",
    END
)

builder.add_edge(
    "error_node",
    END
)


graph = builder.compile()


def run_case(should_fail: bool):
    print("=" * 40)

    result = graph.invoke(
        {
            "question": "请介绍一下 Python",
            "should_fail": should_fail,
            "answer": "",
            "error": ""
        }
    )

    print("最终结果：")
    print(result)


if __name__ == "__main__":
    print("第一次：模拟成功")
    run_case(False)

    print("第二次：模拟失败")
    run_case(True)