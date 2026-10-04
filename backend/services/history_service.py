from database import SessionLocal
from models import ChatHistory
from services.session_service import get_owned_session


def get_history(
    session_id: int,
    user_id: int
):
    db = SessionLocal()
#在查询历史之前，先确认这个会话属于当前用户
    try:
        
        get_owned_session(
            db,
            user_id,
            session_id
        )

        data = (
            db.query(ChatHistory)
            .filter(
                ChatHistory.session_id == session_id
            )
            .order_by(
                ChatHistory.id.asc()
            )
            .all()
        )

        result = []

        for item in data:
            result.append({
                "id": item.id,
                "role": item.role,
                "content": item.content,
                "create_time": item.create_time
            })

        return result

    finally:
        db.close()