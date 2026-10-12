from fastapi import APIRouter, Depends
from fastapi.security import (
    HTTPBearer,
    HTTPAuthorizationCredentials
)
from pydantic import BaseModel, Field
from fastapi.responses import StreamingResponse
from services.agent_stream_service import agent_service_stream
from auth import get_user_id
from services.agent_service import agent_service


router = APIRouter(
    prefix="/agent",
    tags=["agent"]
)

security = HTTPBearer()


class AgentRequest(BaseModel):
    message: str = Field(
        min_length=1,
        max_length=4000,
        description="本轮问题，最多 4000 个字符",
    )
    session_id: int | None = None


@router.post("/chat")
def agent_chat(
    request: AgentRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    user_id = get_user_id(
        credentials.credentials
    )

    answer , session_id ,sources, steps= agent_service(
        user_id=user_id,
        session_id=request.session_id,
        question=request.message
    )

    return {
        "answer": answer,
         "session_id": session_id,
         "sources": sources,
         "steps": steps
    }
@router.post("/chat/stream")
def agent_chat_stream(
    request: AgentRequest,
    credentials: HTTPAuthorizationCredentials = Depends(
        security
    )
):
    user_id = get_user_id(
        credentials.credentials
    )

    return StreamingResponse(
        agent_service_stream(
            user_id=user_id,
            session_id=request.session_id,
            question=request.message
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive"
        }
    )
