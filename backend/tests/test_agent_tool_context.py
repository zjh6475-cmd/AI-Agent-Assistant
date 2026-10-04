import graph.agent_tools as agent_tools

from langchain_core.messages import (
    AIMessage,
    ToolMessage,
)
from langgraph.prebuilt import ToolNode
from langgraph.runtime import Runtime

from graph.agent_context import AgentContext
import sys
from types import ModuleType

def test_query_user_data_uses_runtime_context_user_id(
    monkeypatch,
):
    """
    模型请求查询用户数据时，
    工具只能使用 Graph 运行上下文中的 user_id。
    """

    captured = {}

    # 替代真实数据库查询：
    # 不连接数据库，只记录工具收到的参数。
    def fake_run_sql_tool(
        action: str,
        user_id: int,
        limit: int,
    ) -> dict:
        captured["action"] = action
        captured["user_id"] = user_id
        captured["limit"] = limit

        return {
            "action": action,
            "rows": [],
        }

    monkeypatch.setattr(
        agent_tools,
        "run_sql_tool",
        fake_run_sql_tool,
    )

    tool_node = ToolNode(
        [agent_tools.query_user_data],
        handle_tool_errors=False,
    )

    # 模拟模型请求工具。
    # 注意：参数中没有、也不应该有 user_id。
    ai_message = AIMessage(
        content="",
        tool_calls=[
            {
                "name": "query_user_data",
                "args": {
                    "action": "document_count",
                    "limit": 3,
                },
                "id": "call-user-context-1",
            }
        ],
    )

    result = tool_node.invoke(
        {
            "messages": [ai_message],
        },
        runtime=Runtime(
            context=AgentContext(
                user_id=7,
            )
        ),
    )

    message = result["messages"][0]

    assert isinstance(message, ToolMessage)
    assert message.status == "success"

    # 身份来自 runtime.context，而不是模型工具参数。
    assert captured == {
        "action": "document_count",
        "user_id": 7,
        "limit": 3,
    }
    
    
def test_search_knowledge_base_uses_context_and_bounds_k(
    monkeypatch,
):
    """
    知识库工具应：

    1. 从 runtime.context 获取 user_id；
    2. 将模型传入的 k 限制在 MAX_K 以内；
    3. 在调用时才导入 vector_service。
    """

    captured = {}

    # 构造假的 services.vector_service 模块。
    # 这样函数内部执行 import 时，不会加载真实嵌入模型。
    fake_vector_service = ModuleType(
        "services.vector_service"
    )

    def fake_search_chunks(
        query: str,
        user_id: int,
        k: int,
    ) -> dict:
        captured["query"] = query
        captured["user_id"] = user_id
        captured["k"] = k

        return {
            "documents": [],
            "distances": [],
            "metadatas": [],
        }

    fake_vector_service.search_chunks = (
        fake_search_chunks
    )

    monkeypatch.setitem(
        sys.modules,
        "services.vector_service",
        fake_vector_service,
    )

    tool_node = ToolNode(
        [agent_tools.search_knowledge_base],
        handle_tool_errors=False,
    )

    # 模拟模型请求 999 条结果。
    # 真实工具必须把它限制为 MAX_K = 5。
    ai_message = AIMessage(
        content="",
        tool_calls=[
            {
                "name": "search_knowledge_base",
                "args": {
                    "query": "测试懒加载检索",
                    "k": 999,
                },
                "id": "call-knowledge-context-1",
            }
        ],
    )

    result = tool_node.invoke(
        {
            "messages": [ai_message],
        },
        runtime=Runtime(
            context=AgentContext(
                user_id=7,
            )
        ),
    )

    message = result["messages"][0]

    assert isinstance(message, ToolMessage)
    assert message.status == "success"

    assert captured == {
        "query": "测试懒加载检索",
        "user_id": 7,
        "k": 5,
    }    