from sqlalchemy import text
from langchain_core.tools import tool
from database import SessionLocal


MAX_LIMIT = 20


def run_sql_tool(
    action: str,
    user_id: int,
    limit: int = 10
):
    limit = max(1, min(limit, MAX_LIMIT))

    sql_map = {
        "document_count": text(
            """
            SELECT COUNT(*) AS count
            FROM documents
            WHERE user_id = :user_id
            """
        ),
        "recent_documents": text(
            """
            SELECT id, filename, file_type, create_time
            FROM documents
            WHERE user_id = :user_id
            ORDER BY create_time DESC
            LIMIT :limit
            """
        ),
        "session_count": text(
            """
            SELECT COUNT(*) AS count
            FROM chat_sessions
            WHERE user_id = :user_id
            """
        ),
        "message_count": text(
            """
            SELECT COUNT(*) AS count
            FROM chat_history
            WHERE session_id IN (
                SELECT id
                FROM chat_sessions
                WHERE user_id = :user_id
            )
            """
        ),
    }

    if action not in sql_map:
        raise ValueError("不支持的查询类型")

    db = SessionLocal()

    try:
        params = {
            "user_id": user_id,
            "limit": limit,
        }

        result = db.execute(
            sql_map[action],
            params
        )

        rows = [
            dict(row)
            for row in result.mappings().all()
        ]

        return {
            "action": action,
            "rows": rows,
        }

    finally:
        db.close()
        
def create_user_sql_tool(user_id: int):
    @tool("query_user_data")
    def query_user_data(
        action: str,
        limit: int = 10
    ) -> dict:
        """
        查询当前用户自己的文档、会话和消息统计。
        action 可选：
        document_count、recent_documents、
        session_count、message_count
        """
        return run_sql_tool(
            action=action,
            user_id=user_id,
            limit=limit
        )

    return query_user_data        