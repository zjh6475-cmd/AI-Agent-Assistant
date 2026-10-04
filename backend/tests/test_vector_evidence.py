from types import SimpleNamespace

from services import vector_service


class FakeVectorDb:
    """
    模拟 Chroma 的检索结果，
    不连接真实向量数据库。
    """

    def __init__(self):
        self.calls = []

    def similarity_search_with_score(
        self,
        query,
        k,
        filter,
    ):
        self.calls.append(
            {
                "query": query,
                "k": k,
                "filter": filter,
            }
        )

        return [
            (
                SimpleNamespace(
                    page_content="Transformer 使用注意力机制。",
                    metadata={
                        "document_id": 42,
                        "user_id": "user-1",
                        "chunk_index": 0,
                        "filename": "transformer.docx",
                    },
                ),
                0.12,
            ),
        ]


def test_search_chunks_binds_content_to_source(
    monkeypatch,
):
    """
    每条 evidence 必须绑定文本与来源。
    """

    fake_vector_db = FakeVectorDb()

    monkeypatch.setattr(
        vector_service,
        "get_vector_db",
        lambda: fake_vector_db,
    )

    result = vector_service.search_chunks(
        query="Transformer 的核心机制是什么？",
        user_id="user-1",
        k=3,
    )

    assert fake_vector_db.calls == [
        {
            "query": "Transformer 的核心机制是什么？",
            "k": 3,
            "filter": {
                "user_id": "user-1",
            },
        }
    ]

    assert result["evidences"] == [
        {
            "source_id": "document-42-chunk-0",
            "filename": "transformer.docx",
            "document_id": 42,
            "chunk_index": 0,
            "content": "Transformer 使用注意力机制。",
            "distance": 0.12,
        }
    ]
    
def test_search_chunks_rejects_distant_results(
    monkeypatch,
):
    """
    距离超过阈值的候选片段，
    不得作为可靠证据返回。
    """

    distant_document = SimpleNamespace(
        page_content="这是一段与问题无关的内容。",
        metadata={
            "document_id": 99,
            "user_id": "user-1",
            "chunk_index": 0,
            "filename": "unrelated.docx",
        },
    )

    fake_vector_db = FakeVectorDb()

    monkeypatch.setattr(
        fake_vector_db,
        "similarity_search_with_score",
        lambda query, k, filter: [
            (
                distant_document,
                0.65,
            ),
        ],
    )

    monkeypatch.setattr(
        vector_service,
        "get_vector_db",
        lambda: fake_vector_db,
    )

    monkeypatch.setenv(
        "KNOWLEDGE_BASE_MAX_DISTANCE",
        "0.50",
    )

    result = vector_service.search_chunks(
        query="月球基地预算是多少？",
        user_id="user-1",
        k=3,
    )

    assert result["documents"] == []
    assert result["distances"] == []
    assert result["metadatas"] == []
    assert result["evidences"] == []

    assert result["retrieval_status"] == (
        "no_reliable_evidence"
    )

    assert result["max_distance"] == 0.50
    assert result["candidate_count"] == 1    
    
def test_get_vector_db_reuses_one_instance(monkeypatch):
    created = []
    fake_vector_db = object()

    monkeypatch.setattr(vector_service, "_vector_db", None)

    monkeypatch.setattr(
        vector_service,
        "_create_vector_db",
        lambda: created.append(fake_vector_db) or fake_vector_db,
    )

    first = vector_service.get_vector_db()
    second = vector_service.get_vector_db()

    assert first is fake_vector_db
    assert second is fake_vector_db
    assert created == [fake_vector_db]    
    
    
def test_search_chunks_rejects_evidence_without_required_anchor(
    monkeypatch,
):
    fake_vector_db = FakeVectorDb()

    monkeypatch.setattr(
        vector_service,
        "get_vector_db",
        lambda: fake_vector_db,
    )

    monkeypatch.setenv(
        "KNOWLEDGE_BASE_MAX_DISTANCE",
        "0.50",
    )

    result = vector_service.search_chunks(
        query="Transformer 的训练使用了哪一款 GPU？",
        user_id="user-1",
        k=3,
    )

    assert result["evidences"] == []
    assert result["retrieval_status"] == (
        "no_reliable_evidence"
    )
    assert result["anchor_check_passed"] is False
    assert result["rejection_reason"] == (
        "evidence_anchor_missing"
    )    
    
    
    
def test_search_chunks_drops_mixed_user_results(
    monkeypatch,
):
    allowed_document = SimpleNamespace(
        page_content="Transformer 使用注意力机制。",
        metadata={
            "document_id": 42,
            "user_id": "user-1",
            "chunk_index": 0,
            "filename": "transformer.docx",
        },
    )

    forbidden_document = SimpleNamespace(
        page_content="这是用户2的私有文档内容。",
        metadata={
            "document_id": 99,
            "user_id": "user-2",
            "chunk_index": 0,
            "filename": "private.docx",
        },
    )

    fake_vector_db = FakeVectorDb()

    monkeypatch.setattr(
        fake_vector_db,
        "similarity_search_with_score",
        lambda query, k, filter: [
            (allowed_document, 0.12),
            (forbidden_document, 0.13),
        ],
    )

    monkeypatch.setattr(
        vector_service,
        "get_vector_db",
        lambda: fake_vector_db,
    )

    result = vector_service.search_chunks(
        query="Transformer 的核心机制是什么？",
        user_id="user-1",
        k=3,
    )

    assert result["evidences"] == [
        {
            "source_id": "document-42-chunk-0",
            "filename": "transformer.docx",
            "document_id": 42,
            "chunk_index": 0,
            "content": "Transformer 使用注意力机制。",
            "distance": 0.12,
        }
    ]

    assert all(
        evidence["document_id"] != 99
        for evidence in result["evidences"]
    )    