from fastapi import APIRouter

from database import SessionLocal
from models import User

from auth import create_token
from security import hash_password,verify_password

from pydantic import BaseModel


router=APIRouter()
# =====================
# 注册
# =====================

class RegisterRequest(BaseModel):

    username:str

    password:str

    confirm_password:str





class LoginRequest(BaseModel):

    username:str

    password:str





@router.post("/register")
def register(
    request:RegisterRequest   
):


    import re


    # =====================
    # 手机号格式验证
    # =====================

    if not re.fullmatch(
        r"\d{11}",
        request.username
    ):

        return {

            "message":
            "账号必须是11位数字"

        }



    # =====================
    # 密码确认
    # =====================

    if request.password != request.confirm_password:


        return {

            "message":
            "两次密码不一致"

        }





    db=SessionLocal()



    user=(

        db.query(User)

        .filter(

            User.username==request.username

        )

        .first()

    )



    if user:


        db.close()


        return {

            "message":
            "账号已经存在"

        }





    new_user=User(


        username=request.username,


        password=hash_password(
            request.password
        )#加密密碼


    )



    db.add(new_user)  #放进数据库

    db.commit()   #保存

    db.refresh(new_user)



    db.close()



    return {


        "message":
        "注册成功",


        "user_id":
        new_user.id

    }

@router.post("/login")
def login(
    request:LoginRequest
):


    db=SessionLocal()


    user=(

        db.query(User)

        .filter(

            User.username==request.username

        )

        .first()

    )


    # 用户不存在

    if not user:


        db.close()


        return {

            "message":"用户名或密码错误"

        }



    # 密码验证

    if not verify_password(
        request.password,
        user.password
    ):


        db.close()


        return {

            "message":"用户名或密码错误"

        }



    # 创建token

    token=create_token(user.id)



    db.close()



    return {


        "message":"登录成功",

        "token":token,

        "username":user.username

    }