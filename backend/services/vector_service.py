from pathlib import Path
import os
from langchain_chroma import Chroma
from threading import Lock
from services.evidence_guard import (
    evidence_covers_query_anchors,
)



# =========================
# 向量数据库路径
# =========================

BACKEND_DIR = Path(__file__).resolve().parent.parent


# 部署时通过环境变量把向量索引放入数据卷；
# 本地未配置时仍使用 backend/vector_db，保持现有开发行为。
VECTOR_DB_DIR = Path(
    os.getenv(
        "VECTOR_DB_DIR",
        str(BACKEND_DIR / "vector_db"),
    )
)


VECTOR_DB_DIR.mkdir(

    parents=True,

    exist_ok=True

)
_vector_db = None
_vector_db_lock = Lock()


# =========================
# 获取Chroma向量数据库
# =========================

def _create_vector_db():
    # 保持懒加载：只有第一次真正检索或写入向量库时才加载嵌入模型
    from services.embedding_service import embedding_model

    return Chroma(
        collection_name="document_chunks",
        persist_directory=str(VECTOR_DB_DIR),
        embedding_function=embedding_model,
    )


def get_vector_db():
    global _vector_db

    if _vector_db is not None:
        return _vector_db

    # 防止首次有多个请求同时创建 Chroma 客户端
    with _vector_db_lock:
        if _vector_db is None:
            _vector_db = _create_vector_db()

    return _vector_db


# =========================
# 添加文档切片
# =========================

def add_chunks(

    chunks,

    document_id,

    user_id,
    
    filename

):


    if not chunks:

        return []


    vector_db = get_vector_db()


    metadatas = []


    ids = []


    for index, _ in enumerate(chunks):


        metadatas.append({

            "document_id": document_id,

            "user_id": user_id,

            "chunk_index": index,
            
            "filename": filename,

        })


        ids.append(

            f"document-{document_id}-chunk-{index}"

        )


    result = vector_db.add_texts(

        texts=chunks,

        metadatas=metadatas,

        ids=ids

    )


    return result



# =========================
# 搜索当前用户的知识库
# 返回内容 + 相似距离
# =========================

def search_chunks(
    query,
    user_id,
    k=3,
):
    vector_db = get_vector_db()

    max_distance = float(
        os.getenv(
            "KNOWLEDGE_BASE_MAX_DISTANCE",
            "0.50",
        )
    )

    raw_results = (
        vector_db.similarity_search_with_score(
            query,
            k=k,
            filter={
                "user_id": user_id
            },
        )
    )

    # 数据库层过滤之外，再做一次应用层身份校验。
    # 缺少 user_id 或 user_id 不匹配的片段都不能进入 sources。
    results = [
        (doc, distance)
        for doc, distance in raw_results
        if str(
            (doc.metadata or {}).get("user_id")
        ) == str(user_id)
    ]

    raw_distances = [
        float(distance)
        for _, distance in results
    ]
    relevant_results = [
        (doc, distance)
        for doc, distance in results
        if float(distance) <= max_distance
    ]

    documents = []
    distances = []
    metadatas = []
    evidences = []
    anchor_check_passed = None
    
    for doc, distance in relevant_results:
        metadata = dict(doc.metadata or {})
        document_id = metadata.get("document_id")
        chunk_index = metadata.get("chunk_index")

        documents.append(doc.page_content)
        distances.append(distance)
        metadatas.append(metadata)

        evidences.append(
            {
                "source_id": (
                    f"document-{document_id}"
                    f"-chunk-{chunk_index}"
                ),
                "filename": metadata.get(
                    "filename",
                    "未知文件",
                ),
                "document_id": document_id,
                "chunk_index": chunk_index,
                "content": doc.page_content,
                "distance": float(distance),
            }
        )
        
        anchor_check_passed = None

    if evidences:
        anchor_check_passed = (
            evidence_covers_query_anchors(
                query,
                [
                    evidence["content"]
                    for evidence in evidences
                ],
            )
        )

        if not anchor_check_passed:
            documents = []
            distances = []
            metadatas = []
            evidences = []    

    print("================")
    print("查询:", query)
    print("原始距离:", raw_distances)
    print("最大允许距离:", max_distance)
    print("锚点校验通过:", anchor_check_passed)
    print("保留片段数:", len(evidences))
    print("================")

    return {
        "documents": documents,
        "distances": distances,
        "metadatas": metadatas,
        "evidences": evidences,
        "retrieval_status": (
            "ok"
            if evidences
            else "no_reliable_evidence"
        ),
        "max_distance": max_distance,
        "anchor_check_passed": anchor_check_passed,
        "rejection_reason": (
            "evidence_anchor_missing"
            if anchor_check_passed is False
            else None
        ),
        "candidate_count": len(results),
    }

# =========================
# 删除某个文件的向量
# =========================

def delete_document_vectors(

    document_id,

    chunk_indexes

):


    if not chunk_indexes:

        return


    vector_db = get_vector_db()


    vector_ids = []


    for chunk_index in chunk_indexes:


        vector_ids.append(

            f"document-{document_id}-chunk-{chunk_index}"

        )


    vector_db.delete(

        ids=vector_ids

    )