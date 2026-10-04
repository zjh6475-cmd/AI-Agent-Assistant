from typing import TypedDict
from langgraph.graph import StateGraph,START,END


#1.输入状态
class InputState(TypedDict):
    username:str
#2.输出状态
class OutputState(TypedDict):
    graph_output:str
    
#3.全局状态
class OverallState(TypedDict):
    username:str
    nickname:str
    graph_output:str
    
#4.私有状态  保存临时数据 greeting是节点之间传递的临时数据
class PrivateState(TypedDict)  :
    greeting: str
 
 
# 第一个节点：
# 读取输入状态，向全局状态写入 nickname        
def node_1(state:InputState)->OverallState:
    return{
        "nickname":"Dear"+state["username"]
    }    


# 第二个节点：
# 读取全局状态，向私有状态写入 greeting，quan
def node_2(state: OverallState) -> PrivateState:
    return {
        "greeting": state["nickname"] + "，早上好~"
    }
 
# 第三个节点：
# 读取私有状态，向输出状态写入 graph_output
def node_3(state: PrivateState) -> OutputState:
    return {
        "graph_output": state["greeting"] + " 很高兴认识你！"
    }



# 创建 Graph
builder = StateGraph(
    state_schema=OverallState,
    input_schema=InputState,
    output_schema=OutputState
)


# 添加节点
builder.add_node("node_1", node_1)
builder.add_node("node_2", node_2)
builder.add_node("node_3", node_3)


# 添加边
builder.add_edge(START, "node_1")
builder.add_edge("node_1", "node_2")
builder.add_edge("node_2", "node_3")
builder.add_edge("node_3", END)


# 编译 Graph
graph = builder.compile()


if __name__ == "__main__":
    result = graph.invoke(
        {
            "username": "小黄"
        }
    )

    print(result)    