from pathlib import Path
from uuid import uuid4
import os
from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    UploadFile
)

from fastapi.security import (
    HTTPBearer,
    HTTPAuthorizationCredentials
)


from database import SessionLocal

from models import (
    Document,
    DocumentChunk
)

from auth import get_user_id


from services.document_parser import extract_document_text

from services.chunk_service import split_text
from services.vector_service import add_chunks,search_chunks,delete_document_vectors



router = APIRouter()


security = HTTPBearer()



# =========================
# 路径
# =========================


BACKEND_DIR = Path(__file__).resolve().parent.parent


# 部署时通过环境变量把上传文件放入数据卷；
# 本地未配置时仍使用 backend/uploads，保持现有开发行为。
UPLOAD_DIR = Path(
    os.getenv(
        "UPLOAD_DIR",
        str(BACKEND_DIR / "uploads"),
    )
)


UPLOAD_DIR.mkdir(
    parents=True,
    exist_ok=True
)



ALLOWED_SUFFIXES = {

    ".pdf",
    ".txt",
    ".docx"

}



MAX_FILE_SIZE = 10 * 1024 * 1024




# =========================
# 上传文件
# =========================


@router.post("/documents/upload")
async def upload_document(

    file: UploadFile = File(...),

    credentials:
    HTTPAuthorizationCredentials = Depends(security)

):


    token = credentials.credentials

    user_id = get_user_id(token)



    if not file.filename:


        raise HTTPException(

            status_code=400,

            detail="文件名不能为空"

        )



    original_filename = Path(
        file.filename
    ).name



    suffix = Path(
        original_filename
    ).suffix.lower()



    if suffix not in ALLOWED_SUFFIXES:


        raise HTTPException(

            status_code=400,

            detail="只支持PDF、TXT、DOCX"

        )




    saved_filename = (

        f"{uuid4().hex}{suffix}"

    )



    saved_path = (

        UPLOAD_DIR / saved_filename
        
    )
    db = None
    document = None
    chunks = []



    file_size=0



    try:


        # 保存文件


        with saved_path.open("wb") as output_file:


            while True:


                data = await file.read(

                    1024*1024

                )


                if not data:

                    break



                file_size += len(data)



                if file_size > MAX_FILE_SIZE:


                    raise HTTPException(

                        status_code=400,

                        detail="文件超过10MB"

                    )



                output_file.write(data)





        db = SessionLocal()



        try:



            # ======================
            # 保存documents
            # ======================


            document = Document(

                user_id=user_id,

                filename=original_filename,

                file_path=f"uploads/{saved_filename}",

                file_type=suffix.lstrip(".")

            )



            db.add(document)


            db.commit()


            db.refresh(document)





            # ======================
            # 解析文本
            # ======================


            text = extract_document_text(

                file_path=saved_path,

                file_type=document.file_type

            )





            # ======================
            # 文本切片
            # ======================


            chunks = split_text(text)





            # ======================
            # 保存chunk
            # ======================


            for index,chunk in enumerate(chunks):


                item = DocumentChunk(


                    document_id=document.id,


                    content=chunk,


                    chunk_index=index


                )


                db.add(item)



            db.commit()
            
# ======================
# 保存到Chroma向量数据库
# ======================

            add_chunks(

               chunks=chunks,

                 document_id=document.id,

                 user_id=user_id,
                 
                 filename=document.filename

            )             
            
            






            return {


                "message":"上传成功",


                "document":{


                    "id":document.id,


                    "filename":
                    document.filename,


                    "chunks":
                    len(chunks)


                }



            }


        except Exception:
            db.rollback()

            if document is not None:
                try:
                    delete_document_vectors(
                        document_id=document.id,
                        chunk_indexes=range(len(chunks))
                    )
                except Exception:
                    pass

                db.delete(document)
                db.commit()

            if saved_path.exists():
                saved_path.unlink()

            raise HTTPException(
                status_code=500,
                detail="文档处理失败，请稍后重试"
            )



        finally:


            db.close()
            
    except HTTPException:
        if saved_path.exists():
            saved_path.unlink()
        raise

    except Exception:
        if saved_path.exists():
            saved_path.unlink()

        raise HTTPException(
            status_code=500,
            detail="文件上传失败，请稍后重试"
        )    



    finally:


        await file.close()






# =========================
# 获取文件文本
# =========================


@router.get("/documents/{document_id}/text")
def get_document_text(


    document_id:int,


    credentials:
    HTTPAuthorizationCredentials = Depends(security)


):


    token = credentials.credentials


    user_id=get_user_id(token)



    db=SessionLocal()



    try:


        document=(


            db.query(Document)


            .filter(

                Document.id==document_id,

                Document.user_id==user_id

            )

            .first()


        )



        if not document:


            raise HTTPException(

                status_code=404,

                detail="文件不存在"

            )




        real_path=(

            BACKEND_DIR /

            document.file_path

        )




        text=extract_document_text(

            file_path=real_path,

            file_type=document.file_type

        )




        return {


            "document_id":document.id,


            "filename":document.filename,


            "character_count":len(text),


            "preview":text[:2000]


        }



    finally:


        db.close()






# =========================
# 文件列表
# =========================


@router.get("/documents")
def get_documents(


    credentials:
    HTTPAuthorizationCredentials = Depends(security)


):


    token=credentials.credentials


    user_id=get_user_id(token)



    db=SessionLocal()



    try:


        data=(


            db.query(Document)


            .filter(

                Document.user_id==user_id

            )

            .order_by(

                Document.id.desc()

            )

            .all()


        )



        result=[]



        for item in data:


            result.append({


                "id":item.id,


                "filename":item.filename,


                "file_type":item.file_type,


                "create_time":item.create_time


            })



        return result



    finally:


        db.close()
        
# =========================
# 测试知识库向量检索
# =========================

@router.get("/documents/search/chunks")
def search_document_chunks(

    query: str,

    credentials:
    HTTPAuthorizationCredentials = Depends(security)

):


    token = credentials.credentials

    user_id = get_user_id(token)



    try:


        documents = search_chunks(

            query=query,

            user_id=user_id,

            k=3

        )



        result = []


        for document in documents:


            result.append({

                "content":
                    document.page_content,

                "metadata":
                    document.metadata

            })


        return {

            "query":query,

            "count":len(result),

            "results":result

        }



    except Exception as error:


        raise HTTPException(

            status_code=500,

            detail=f"向量检索失败：{str(error)}"

        )        
# =========================
# 删除知识文件
# =========================

@router.delete("/documents/{document_id}")
def delete_document(

    document_id: int,

    credentials:
    HTTPAuthorizationCredentials = Depends(security)

):


    token = credentials.credentials

    user_id = get_user_id(token)


    db = SessionLocal()


    try:


        # 只能删除当前用户自己的文件

        document = (

            db.query(Document)

            .filter(

                Document.id == document_id,

                Document.user_id == user_id

            )

            .first()

        )


        if not document:


            raise HTTPException(

                status_code=404,

                detail="文件不存在"

            )



        # 查询这个文件的全部切片

        chunks = (

            db.query(DocumentChunk)

            .filter(

                DocumentChunk.document_id
                == document_id

            )

            .all()

        )



        chunk_indexes = [

            item.chunk_index

            for item in chunks

        ]



        # ======================
        # 删除Chroma向量
        # ======================

        delete_document_vectors(

            document_id=document_id,

            chunk_indexes=chunk_indexes

        )



        # ======================
        # 删除SQLite切片
        # ======================

        db.query(DocumentChunk).filter(

            DocumentChunk.document_id
            == document_id

        ).delete(

            synchronize_session=False

        )



        # 保存实体文件路径

        real_path = (

            BACKEND_DIR
            / document.file_path

        )



        # ======================
        # 删除documents记录
        # ======================

        db.delete(document)

        db.commit()



        # ======================
        # 删除uploads实体文件
        # ======================

        if real_path.exists():

            real_path.unlink()



        return {

            "message":"文件删除成功",

            "document_id":document_id

        }



    except HTTPException:


        db.rollback()

        raise



    except Exception as error:


        db.rollback()


        raise HTTPException(

            status_code=500,

            detail=f"删除文件失败：{str(error)}"

        )



    finally:


        db.close()        