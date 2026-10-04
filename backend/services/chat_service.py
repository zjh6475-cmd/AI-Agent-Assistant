from database import SessionLocal


from models import (
    ChatHistory,
    ChatSession
)


from langchain_core.messages import (
    HumanMessage,
    SystemMessage,
    AIMessage
)


from llm import llm



from services.session_service import get_owned_session

import json
import logging

logger = logging.getLogger(__name__)











# =========================
# 普通聊天创建或校验会话
#↓
#保存用户问题
#↓
#检索知识库
#↓
#调用 LLM
#↓
#保存 AI 回复
#↓
#返回 answer 和 session_id

# =========================


def chat_service(
    user_id,
    session_id,
    message
):
    db = SessionLocal()

    try:
        if session_id is None:
            session = ChatSession(
                user_id=user_id,
                title=message[:15]
            )

            db.add(session)
            db.commit()
            db.refresh(session)

            session_id = session.id
        else:
            get_owned_session(
                db,
                user_id,
                session_id
            )

        # 先读取旧历史，避免当前问题重复进入 Prompt
        history = (
            db.query(ChatHistory)
            .filter(
                ChatHistory.session_id == session_id
            )
            .order_by(
                ChatHistory.id.asc()
            )
            .all()
        )

        # 检索知识库
       

        messages = [
            SystemMessage(
                content=f"""
你是一个友好、准确的 AI 助手。
请根据用户的问题直接回答。
回答清晰、有帮助；不确定时请明确说明。
"""
            )
        ]

        # 添加历史消息
        for item in history:
            if item.role == "user":
                messages.append(
                    HumanMessage(
                        content=item.content
                    )
                )
            elif item.role == "assistant":
                messages.append(
                    AIMessage(
                        content=item.content
                    )
                )

        # 添加当前问题
        messages.append(
            HumanMessage(
                content=message
            )
        )
        
        
        # 保存当前用户问题
        user_message = ChatHistory(
            session_id=session_id,
            role="user",
            content=message
        )

        db.add(user_message)
        db.commit()


        # 调用模型生成回答
        response = llm.invoke(messages)
        answer = response.content or ""

        # 保存 AI 回复
        ai_message = ChatHistory(
            session_id=session_id,
            role="assistant",
            content=answer
        )

        db.add(ai_message)
        db.commit()

        return answer, session_id

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()







# =========================
# SSE流式聊天 + RAG
# =========================


def chat_service_stream(


    user_id,

    session_id,

    message


):


    db = SessionLocal()



    try:



        # =====================
        # 创建聊天窗口
        #用户传入自己的 session_id → 正常聊天
        #用户传入别人的 session_id → 返回 404
        #用户不传 session_id → 创建自己的新会话
        # =====================


        if session_id is None:


            session = ChatSession(

                user_id=user_id,

                title=message[:15]

            )


            db.add(session)

            db.commit()

            db.refresh(session)


            session_id=session.id
        else:
            get_owned_session(
                db,
                user_id,
                session_id
            )
















        # =====================
        # 获取历史消息
        # =====================


        history=(


            db.query(ChatHistory)


            .filter(

                ChatHistory.session_id

                ==session_id

            )


            .order_by(

                ChatHistory.id.asc()

            )


            .all()


        )







        # =====================
        # 构造Prompt
        # =====================


        messages=[]



        messages.append(


            SystemMessage(


                content=f"""

你是一个友好、准确的 AI 助手。
请根据用户的问题直接回答。
回答清晰、有帮助；不确定时请明确说明。


"""


            )

        )







        for item in history:



            if item.role=="user":


                messages.append(

                    HumanMessage(

                        content=item.content

                    )

                )


            elif item.role=="assistant":


                messages.append(

                    AIMessage(

                        content=item.content

                    )

                )





        # =====================
        # 当前问题
        # =====================


        messages.append(

            HumanMessage(

                content=message

            )

        )
        
        # =====================
        # 保存用户消息
        # =====================


        user_message = ChatHistory(

            session_id=session_id,

            role="user",

            content=message

        )


        db.add(user_message)

        db.commit()
        
        session_data = json.dumps(
            {
                "session_id": session_id
            },
            ensure_ascii=False
        )

        yield (
            "event: session\n"
            f"data:{session_data}\n\n"
        )
        
        sources = []






        full_answer=""





        # =====================
        # SSE流式输出
        # =====================


        for chunk in llm.stream(messages):


            content=chunk.content


            if content:


                full_answer += content



                data=json.dumps(

                    {

                    "content":content

                    },

                    ensure_ascii=False

                )



                yield (

                    "event: token\n"

                    f"data:{data}\n\n"

                )






        # =====================
        # 返回来源
        # =====================









        # =====================
        # 保存AI回复
        # =====================


        ai_message=ChatHistory(

            session_id=session_id,

            role="assistant",

            content=full_answer

        )


        db.add(ai_message)

        db.commit()
        
        yield (

            "event: sources\n"

            f"data:{json.dumps(sources,ensure_ascii=False)}\n\n"

        )




        yield (

            "event: done\n"

            "data:{}\n\n"

        )




    except Exception:
        db.rollback()
        logger.exception("chat_service_stream 执行失败")

        error_data = json.dumps(
            {
                "message": "AI 生成失败，请稍后重试"
            },
            ensure_ascii=False
        )

        yield (
            "event: error\n"
            f"data:{error_data}\n\n"
        )

    finally:
        db.close()