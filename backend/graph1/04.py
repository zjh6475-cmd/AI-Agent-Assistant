from dataclasses import dataclass
from typing import Annotated

from langgraph.graph import StateGraph,START,END


#自定义 reducer：合并日志
def merge_logs(
    old_logs:list[str],
    new_logs:list[str]
) ->list[str]:
    return old_logs + new_logs

#定义状态
@dataclass
class OverAllState:
    logs: Annotated[list[str],merge_logs]
    cur_id :str
    
# 定义并行节点 1
def node_1(state:OverAllState) ->dict:
    print("node1 读取到的 cur_id:",state.cur_id)
    
    return{
        "logs":["node_1运行完毕"],
        
    }    
    
# 定义并行节点 2
def node_2(state:OverAllState) ->dict:
    print("node2 读取到的 cur_id:",state.cur_id)
    
    return{
        "logs":["node_2运行完毕"],
        
    }        
    
# 创建图构建器
builder = StateGraph(OverAllState)


# 添加节点
builder.add_node("node_1", node_1)
builder.add_node("node_2", node_2)


# 添加并行边
builder.add_edge(START, "node_1")
builder.add_edge(START, "node_2")

# 两个节点都执行完后，才进入 END
builder.add_edge(
    ["node_1", "node_2"],
    END
)


# 编译图
graph = builder.compile()


# 执行图
result = graph.invoke(
    {
        "logs": [],
        "cur_id": "Start"
    }
)


# 打印最终状态
print(result)    