from typing import TypedDict

from langgraph.graph import StateGraph, START, END


# 1. 定义 Graph 的状态
class HelloState(TypedDict, total=False):
    name: str
    answer: str


# 2. 定义节点
def greet_node(state: HelloState) -> dict:
    name = state["name"]

    return {
        "answer": f"你好，{name}"
    }


# 3. 创建 Graph 构建器
builder = StateGraph(HelloState)


# 4. 添加节点
builder.add_node("greet_node", greet_node)


# 5. 添加边，定义执行顺序
builder.add_edge(START, "greet_node")
builder.add_edge("greet_node", END)


# 6. 编译 Graph
graph = builder.compile()


# 7. 运行 Graph
result = graph.invoke(
    {
        "name": "小明"
    }
)


# 8. 打印最终状态
print(result)