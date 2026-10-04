import os

from fastapi import FastAPI
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware
from routers import document
from routers import user
from routers import chat
from routers import session
from database import engine, Base
from routers import agent
load_dotenv()

cors_origins = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173"
    ).split(",")
    if origin.strip()
]

app = FastAPI()



# =====================
# CORS
# =====================



#allow_origins=[    "*"]代表任意网站都可以访问你的后端
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)






# =====================
# 路由
# =====================

app.include_router(
    user.router
)


app.include_router(
    chat.router
)


app.include_router(
    session.router
)

#注册路由
app.include_router(
    document.router
)
app.include_router(agent.router)


# =====================
# 数据库初始化
# =====================

Base.metadata.create_all(
    bind=engine
)





@app.get("/")
def home():

    return {

        "message":"AI Agent启动成功"

    }