from langchain.tools import tool, ToolRuntime
from time import perf_counter
from graph.agent_context import AgentContext
from tools.sql_tool import run_sql_tool



MAX_K = 5


@tool("query_user_data")
def query_user_data(
    action: str,
    runtime: ToolRuntime[AgentContext],
    limit: int = 10,
) -> dict:
    """
    查询当前登录用户自己的数据。

    action 可选：
    document_count
    recent_documents
    session_count
    message_count
    """
   # 从程序上下文获取用户身份
    user_id = runtime.context.user_id
# 继续复用原来的 SQL 查询逻辑
    return run_sql_tool(
        action=action,
        user_id=user_id,
        limit=limit,
    )


@tool("search_knowledge_base")
def search_knowledge_base(
    query: str,
    runtime: ToolRuntime[AgentContext],
    k: int = 3,
) -> dict:
    """
    检索当前登录用户上传的文档。
    """
    runtime.stream_writer(
        {
            "type": "tool_progress",
            "name": "search_knowledge_base",
            "status": "running",
            "message": "正在检索知识库，请稍候。",
        }
    )


    # 仅在真正执行知识库检索时，
    # 才加载向量库和嵌入模型。
    from services.vector_service import search_chunks

    user_id = runtime.context.user_id

    k = max(1, min(k, MAX_K))

    started_at = perf_counter()

    result = search_chunks(
       query=query,
       user_id=user_id,
       k=k,
    )

    retrieval_ms = round(
       (perf_counter() - started_at) * 1000,
       2,
    )

    result["retrieval_ms"] = retrieval_ms
    return result