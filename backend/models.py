from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from database import Base
from datetime import datetime



# ======================
# 用户
# ======================

class User(Base):

    __tablename__="users"


    id = Column(
        Integer,
        primary_key=True
    )


    username = Column(
        String(50),
        unique=True,
        index=True
    )


    password = Column(
        String(200)
    )


    create_time = Column(
        DateTime,
        default=datetime.utcnow
    )

    update_time = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    ) #每次聊天更新



# ======================
# 聊天窗口
# ======================

class ChatSession(Base):

    __tablename__="chat_sessions"



    id = Column(
        Integer,
        primary_key=True,
        index=True
    )


    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        index=True
    )


    title = Column(
        String(100)
    )


    create_time = Column(
        DateTime,
        default=datetime.utcnow
    )






# ======================
# 聊天消息
# ======================

class ChatHistory(Base):

    __tablename__="chat_history"



    id = Column(
        Integer,
        primary_key=True,
        index=True
    )


    session_id = Column(
        Integer,
        ForeignKey("chat_sessions.id"),
        index=True
    )


    role = Column(
        String(20)
    )


    content = Column(
        Text
    )


    create_time = Column(
        DateTime,
        default=datetime.utcnow
    )
    
    
    
    
#新增模型    documents
class Document(Base):

    __tablename__="documents"


    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

#属于哪个用户上传
    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        index=True
        )

#文件名字
    filename = Column(
        String(200)
    )

#文件保存路劲
    file_path = Column(
        String(500)
    )
    # 文件类型

    file_type = Column(
        String(50)
    )

    create_time = Column(
        DateTime,
      
      
        default=datetime.utcnow
    ) 
    
    
# ======================
# 文档切片
# ======================

class DocumentChunk(Base):

    __tablename__="document_chunks"


    id = Column(
        Integer,
        primary_key=True,
        index=True
    )


    # 属于哪个文件

    document_id = Column(
        Integer,
        ForeignKey("documents.id"),
        index=True
    )


    # 切片内容

    content = Column(
        Text
    )


    # 第几个块

    chunk_index = Column(
        Integer
    )


    create_time = Column(
        DateTime,
        default=datetime.utcnow
    )    