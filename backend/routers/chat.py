from fastapi import APIRouter, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from fastapi.responses import StreamingResponse


from auth import get_user_id

from services.chat_service import chat_service,chat_service_stream
from services.history_service import get_history



router = APIRouter()


security = HTTPBearer()



class ChatRequest(BaseModel):

    message:str

    session_id:int | None = None


# =========================
# sse流式
# =========================
@router.post("/chat/stream")
def chat_stream(

    request:ChatRequest,

    credentials:HTTPAuthorizationCredentials=Depends(security)

):


    token=credentials.credentials


    user_id=get_user_id(token)


    def event_generator():


        for chunk in chat_service_stream(

            user_id=user_id,

            session_id=request.session_id,

            message=request.message

        ):


            yield chunk



    return StreamingResponse(

        event_generator(),

        media_type="text/event-stream"

    )

# =========================
# 聊天接口
# =========================

@router.post("/chat")
def chat(

    request:ChatRequest,

    credentials:HTTPAuthorizationCredentials=Depends(security)

):


    token = credentials.credentials


    user_id = get_user_id(token)



    answer,session_id = chat_service(

        user_id=user_id,

        session_id=request.session_id,

        message=request.message

    )



    return {


        "answer":answer,

        "session_id":session_id


    }







# =========================
# 获取历史记录
# 请求历史记录
#↓
#解析 JWT 获取 user_id
#↓
#检查 session_id 是否属于 user_id
#属于：返回历史
#不属于：返回 40
# =========================


@router.get("/history/{session_id}")
def history(
    session_id: int,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    token = credentials.credentials
    user_id = get_user_id(token)

    data = get_history(
        session_id,
        user_id
    )

    return data