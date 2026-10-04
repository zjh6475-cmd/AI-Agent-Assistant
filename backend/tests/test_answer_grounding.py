from evals.answer_grounding import (
    check_answer_grounding,
)


def test_abstain_without_evidence_passes():
    result = check_answer_grounding(
        answer=(
            "当前知识库没有足够资料支持该结论，"
            "因此无法给出确定答案。"
        ),
        case={
            "expected_answer_status": "abstain",
            "allow_general_knowledge": False,
        },
        sources=[],
    )

    assert result["status"] == "passed"


def test_abstain_without_refusal_fails():
    result = check_answer_grounding(
        answer="太阳系中最大的行星是木星。",
        case={
            "expected_answer_status": "abstain",
            "allow_general_knowledge": False,
        },
        sources=[],
    )

    assert result["status"] == "failed"


def test_answer_with_evidence_passes():
    result = check_answer_grounding(
        answer="Attention 负责关注词语之间的关系。",
        case={
            "expected_answer_status": (
                "answer_with_evidence"
            ),
            "expected_evidence_keywords": [
                "Attention",
                "关系",
            ],
        },
        sources=[
            {
                "source_id": "document-1-chunk-1",
                "content": (
                    "Attention 负责找到词语之间的关系。"
                ),
            }
        ],
    )

    assert result["status"] == "passed"

def test_answer_missing_expected_keyword_fails():
    result = check_answer_grounding(
        answer="根据文档，模型负责理解词语之间的关系。",
        case={
            "expected_answer_status": (
                "answer_with_evidence"
            ),
            "expected_evidence_keywords": [
                "Attention",
            ],
        },
        sources=[
            {
                "content": (
                    "Attention 负责理解词语之间的关系。"
                ),
            }
        ],
    )

    assert result["status"] == "failed"
    assert result["reason"] == (
        "回答中缺少预期证据关键词"
    )
    assert result["unsupported_claims"] == [
        "Attention"
    ]

def test_answer_without_evidence_fails():
    result = check_answer_grounding(
        answer="Attention 负责处理词语关系。",
        case={
            "expected_answer_status": (
                "answer_with_evidence"
            ),
            "expected_evidence_keywords": [
                "Attention",
            ],
        },
        sources=[],
    )

    assert result["status"] == "failed"
    
def test_abstain_with_external_knowledge_fails():
    result = check_answer_grounding(
        answer=(
            "当前知识库没有足够资料支持该问题。"
            "作为通用知识补充，太阳系中最大的行星是木星。"
        ),
        case={
            "expected_answer_status": "abstain",
            "allow_general_knowledge": False,
        },
        sources=[],
    )

    assert result["status"] == "failed"  
    
    
    
def test_valid_citation_passes():
    result = check_answer_grounding(
        answer=(
            "Attention 负责理解词语之间的关系。"
            "[来源：Transformer核心原理详解.docx；"
            "证据ID：document-1-chunk-1]"
        ),
        case={
            "expected_answer_status": (
                "answer_with_evidence"
            ),
            "expected_evidence_keywords": [
                "Attention",
                "关系",
            ],
            "must_cite": True,
        },
        sources=[
            {
                "source_id": (
                    "document-1-chunk-1"
                ),
                "filename": (
                    "Transformer核心原理详解.docx"
                ),
                "content": (
                    "Attention 负责理解词语之间的关系。"
                ),
            }
        ],
    )

    assert result["status"] == "passed"


def test_invalid_citation_fails():
    result = check_answer_grounding(
        answer=(
            "Attention 负责理解词语之间的关系。"
            "[来源：不存在的文档.docx；"
            "证据ID：document-99-chunk-1]"
        ),
        case={
            "expected_answer_status": (
                "answer_with_evidence"
            ),
            "expected_evidence_keywords": [
                "Attention",
                "关系",
            ],
            "must_cite": True,
        },
        sources=[
            {
                "source_id": (
                    "document-1-chunk-1"
                ),
                "filename": (
                    "Transformer核心原理详解.docx"
                ),
                "content": (
                    "Attention 负责理解词语之间的关系。"
                ),
            }
        ],
    )

    assert result["status"] == "failed"      
    
    
def test_permission_abstain_passes_without_external_sources():
    result = check_answer_grounding(
        answer=(
            "我只能访问当前登录用户的数据，"
            "无法读取其他用户上传的文档。"
        ),
        case={
            "expected_answer_status": "abstain",
            "abstention_reason": "permission",
            "allow_general_knowledge": False,
        },
        sources=[],
    )

    assert result["status"] == "passed"
    assert result["reason"] == (
        "权限边界说明明确，"
        "且没有返回未授权证据"
    )    