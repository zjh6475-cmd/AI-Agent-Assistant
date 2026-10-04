#权限工具文件 
#原版只按照 session_id 查询历史记录，理论上用户可以尝试访问其他用户的会话。
# 这个文件以后会被聊天、历史记录和会话管理共同使用。
from fastapi import HTTPException

from models import ChatSession


def get_owned_session(
    db,
    user_id: int,
    session_id: int
) -> ChatSession:
    session = (
        db.query(ChatSession)
        .filter(
            ChatSession.id == session_id,
            ChatSession.user_id == user_id
        )
        .first()
    )

    if not session:
        raise HTTPException(
            status_code=404,
            detail="聊天不存在"
        )

    return session