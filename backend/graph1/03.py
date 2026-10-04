from langgraph.graph import StateGraph,START,END
from typing import Annotated
from pydantic import BaseModel
from operator import add

#定义状态的三种方式  pydantic 字典 和数据类型
class OverAllState(BaseModel):
    logs :Annotated[list[str],add]
    cur_id:str
    
def node_1(state:OverAllState) ->OverAllState:
    pre_id = state.cur_id  #数据类型  如果是字典类型就是state[cur_id]
    return{
        "logs":["node_1运行完毕"],
        "cur_id":pre_id+",node_1"
    }    
    
def node_2(state:OverAllState) ->OverAllState:
    pre_id = state.cur_id  #数据类型  如果是字典类型就是state[cur_id]
    return{
        "logs":["node_2运行完毕"],
        "cur_id":pre_id+",node_2"
    }        
    
builder = StateGraph(state_schema=OverAllState)


# 4. 添加节点
builder.add_node(node_1)
builder.add_node(node_2)


# 5. 添加边，定义执行顺序
builder.add_edge(START, "node_1")
builder.add_edge("node_1","node_2")
builder.add_edge("node_2",END)


# 6. 编译 Graph
graph = builder.compile()


# 7. 运行 Graph
result = graph.invoke(
    {
        "cur_id": "Start"
    }
)


# 8. 打印最终状态
print(result)    