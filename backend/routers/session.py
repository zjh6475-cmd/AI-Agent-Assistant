from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from database import SessionLocal

from models import ChatSession,ChatHistory

from auth import get_user_id
from pydantic import BaseModel


router = APIRouter()


security = HTTPBearer()
class TitleRequest(BaseModel):

    title:str

@router.post("/session/new")
def new_session(

    credentials:HTTPAuthorizationCredentials=Depends(security)

):


    token=credentials.credentials


    user_id=get_user_id(token)



    db=SessionLocal()



    session=ChatSession(

        user_id=user_id,

        title="新聊天"

    )



    db.add(session)

    db.commit()

    db.refresh(session)



    db.close()



    return {


        "id":session.id,

        "title":session.title,
        
        

    }


@router.put("/session/{session_id}")
def update_session_title(

    session_id:int,

    request:TitleRequest,

    credentials:HTTPAuthorizationCredentials=Depends(security)

):


    token = credentials.credentials


    user_id = get_user_id(token)



    db = SessionLocal()



    session = (

        db.query(ChatSession)

        .filter(

            ChatSession.id == session_id,

            ChatSession.user_id == user_id

        )

        .first()

    )



    if not session:


        db.close()


        raise HTTPException(

            status_code=404,

            detail="聊天不存在"

        )



    session.title = request.title


    db.commit()



    db.close()



    return {

        "message":"修改成功",

        "title":request.title

    }
@router.delete("/session/{session_id}")
def delete_session(

    session_id:int,

    credentials:HTTPAuthorizationCredentials=Depends(security)

):


    token = credentials.credentials


    user_id = get_user_id(token)



    db = SessionLocal()



    session = (

        db.query(ChatSession)

        .filter(

            ChatSession.id == session_id,

            ChatSession.user_id == user_id

        )

        .first()

    )



    if not session:


        db.close()


        raise HTTPException(

            status_code=404,

            detail="聊天不存在"

        )



    # 删除聊天里面的消息

    db.query(ChatHistory).filter(

        ChatHistory.session_id == session_id

    ).delete()



    # 删除聊天窗口

    db.delete(session)


    db.commit()


    db.close()



    return {

        "message":"删除成功"

    }



# =================================================
# 获取左侧聊天列表
# =================================================


@router.get("/sessions")
def sessions(

    credentials:HTTPAuthorizationCredentials=Depends(security)

):


    token=credentials.credentials


    user_id=get_user_id(token)



    db=SessionLocal()



    data=(

        db.query(ChatSession)

        .filter(

            ChatSession.user_id==user_id

        )

        .order_by(

            ChatSession.id.desc()

        )

        .all()

    )



    result=[]



    for item in data:


        result.append({

            "id":item.id,

            "title":item.title,
            
            "create_time":item.create_time,

           

        })



    db.close()



    return result






# =================================================
# 聊天
# =================================================














