from types import SimpleNamespace

from evals.rag_answer_review import (
    collect_answer_reviews,
    finalize_answer_reviews,
)


def test_collect_answer_reviews_uses_memory_checkpoint():
    calls = []

    def fake_run_graph_fn(
        *,
        user_id,
        session_id,
        question,
        checkpoint_database,
    ):
        calls.append(
            {
                "user_id": user_id,
                "session_id": session_id,
                "question": question,
                "checkpoint_database": checkpoint_database,
            }
        )

        return {
            "messages": [
                SimpleNamespace(
                    content="这是基于证据的测试回答。"
                )
            ],
            "sources": [
                {
                    "filename": "Transformer核心原理详解.docx",
                }
            ],
            "steps": [
                {
                    "name": "call_model",
                    "status": "success",
                }
            ],
        }

    report = collect_answer_reviews(
        [
            {
                "id": "rag-001",
                "question": "Attention 是什么？",
                "expected_answer_status": (
                    "answer_with_evidence"
                ),
                "expected_evidence_keywords": [
                   "Attention"
                ],
                "must_cite": True,
                "allow_general_knowledge": False,
                "expected_sources": [
                    "Transformer核心原理详解.docx"
              ],
            }
        ],
        user_id=1,
        run_graph_fn=fake_run_graph_fn,
    )

    assert calls == [
        {
            "user_id": 1,
            "session_id": -1,
            "question": "Attention 是什么？",
            "checkpoint_database": ":memory:",
        }
    ]

    case = report["cases"][0]

    assert case["expected_answer_status"] == (
        "answer_with_evidence"
    )
    assert case["expected_evidence_keywords"] == [
         "Attention"
    ]
    assert case["must_cite"] is True
    assert case["allow_general_knowledge"] is False
    assert case["expected_sources"] == [
       "Transformer核心原理详解.docx"
    ]
    assert case["actual_answer_status"] is None
    assert case["review_status"] == "pending"
    assert case["answer"] == "这是基于证据的测试回答。"
    assert case["sources"][0]["filename"] == (
        "Transformer核心原理详解.docx"
    )
    assert case["answer_ms"] >= 0

    assert report["summary"]["total_cases"] == 1
    assert report["summary"]["pending_review_cases"] == 1
    
    
def test_finalize_answer_reviews_scores_manual_label():
    report = {
        "summary": {
            "total_cases": 1,
            "pending_review_cases": 1,
        },
        "cases": [
            {
                "id": "rag-009",
                "expected_answer_status": "abstain",
                "actual_answer_status": None,
                "review_status": "pending",
                "answer": (
                "当前知识库没有足够资料支持该结论，"
                "无法给出确定答案。"
            ),
             "sources": [],
            "allow_general_knowledge": False,
            }
        ],
    }

    result = finalize_answer_reviews(
        report,
        {
            "rag-009": "abstain",
        },
    )

    case = result["cases"][0]

    assert case["actual_answer_status"] == (
        "abstain"
    )
    assert case["review_status"] == "passed"
    assert result["summary"]["reviewed_cases"] == 1
    assert result["summary"]["passed_answer_cases"] == 1
    assert result["summary"]["pending_review_cases"] == 0
    assert result["summary"]["answer_pass_rate"] == 1.0    