from typing import Annotated
from operator import add

from langchain_core.messages import HumanMessage
from langgraph.graph import StateGraph,START,END
from langgraph.graph.message import MessagesState
from llm import llm 



#agent的内部状态
class AgentState(MessagesState):
    user_id:int
    sessio_id:int |None
    steps: Annotated[list[str], add]
    sources: list[dict]

# 模型节点
def call_model(state:AgentState) ->dict:
    response=llm.invoke(  #调用模型 ，把下面的信息调给大模型
        state["messages"]  #读取当前状态的所有信息
    )
    
    return{
        "messages":[response]  #请把模型的生成的response加入meessage
    }
    
def record_step(state: AgentState) -> dict:
    return {
        "steps": ["模型调用完成"]
    }
    

#创建图    
builder =StateGraph(state_schema=AgentState)
#添加节点

builder.add_sequence(
    [
        ("call_model", call_model),
        ("record_step", record_step)
    ]
)

builder.add_edge(
    START,
    "call_model"
)

builder.add_edge(
    "record_step",
    END
)


#编译图
graph = builder.compile()

#测试运行
if  __name__ == "__main__":
    result=graph.invoke(
        {
            "messages":[
                HumanMessage(
                    content="请用一句话解释什么是python"
                )
            ],
            "user_id": 1,
            "session_id": None,
            "steps": [],
            "sources": []
        }
    )
    print("AI 回复：")
    print(
        result["messages"][-1].content
    )

    print("执行步骤：")
    print(result["steps"])