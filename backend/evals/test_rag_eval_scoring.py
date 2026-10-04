from evals.rag_eval_scoring import (
    score_retrieval_case,
    summarize_retrieval_scores,
)

def test_score_retrieval_case_accepts_expected_source():
    score = score_retrieval_case(
        {
            "id": "rag-001",
            "expected_source": (
                "Transformer核心原理详解.docx"
            ),
            "expected_retrieval_status": "ok",
        },
        {
            "retrieval_status": "ok",
            "evidences": [
                {
                    "filename": (
                        "Transformer核心原理详解.docx"
                    ),
                }
            ],
        },
    )

    assert score["source_matches"] is True
    assert score["passed"] is True


def test_score_retrieval_case_rejects_wrong_source():
    score = score_retrieval_case(
        {
            "id": "rag-001",
            "expected_source": (
                "Transformer核心原理详解.docx"
            ),
            "expected_retrieval_status": "ok",
        },
        {
            "retrieval_status": "ok",
            "evidences": [
                {
                    "filename": "其他文档.docx",
                }
            ],
        },
    )

    assert score["source_matches"] is False
    assert score["passed"] is False


def test_score_retrieval_case_accepts_expected_abstention():
    score = score_retrieval_case(
        {
            "id": "rag-002",
            "expected_source": None,
            "expected_retrieval_status": (
                "no_reliable_evidence"
            ),
        },
        {
            "retrieval_status": (
                "no_reliable_evidence"
            ),
            "evidences": [],
        },
    )

    assert score["source_matches"] is None
    assert score["passed"] is True
    
def test_summarize_retrieval_scores_calculates_metrics():
    summary = summarize_retrieval_scores(
        [
            {
                "expected_status": "ok",
                "passed": True,
                "hit_at_1": True,
            },
            {
                "expected_status": "ok",
                "passed": False,
                "hit_at_1": False,
            },
            {
                "expected_status": (
                    "no_reliable_evidence"
                ),
                "passed": True,
                "hit_at_1": None,
            },
        ]
    )

    assert summary["total_cases"] == 3
    assert summary["passed_cases"] == 2
    assert summary["case_pass_rate"] == 2 / 3

    assert summary["source_case_count"] == 2
    assert summary["source_recalled_cases"] == 1
    assert summary["source_recall_at_k"] == 0.5

    # [新增] 只统计有来源排名数据的 case，排除拒答 case。
    assert summary["hit_at_1_case_count"] == 2
    assert summary["hit_at_1_cases"] == 1
    assert summary["hit_at_1_rate"] == 0.5

    assert summary["abstention_case_count"] == 1
    assert summary["correct_abstentions"] == 1
    assert summary["abstention_accuracy"] == 1.0    
    
def test_score_preserves_anchor_rejection_reason():
    score = score_retrieval_case(
        {
            "id": "rag-005",
            "expected_source": None,
            "expected_retrieval_status": (
                "no_reliable_evidence"
            ),
        },
        {
            "retrieval_status": (
                "no_reliable_evidence"
            ),
            "evidences": [],
            "anchor_check_passed": False,
            "rejection_reason": (
                "evidence_anchor_missing"
            ),
        },
    )

    assert score["anchor_check_passed"] is False
    assert score["rejection_reason"] == (
        "evidence_anchor_missing"
    )    
    
def test_score_records_source_rank():
    score = score_retrieval_case(
        {
            "id": "rag-rank",
            "expected_source": "目标文档.docx",
            "expected_retrieval_status": "ok",
        },
        {
            "retrieval_status": "ok",
            "evidences": [
                {"filename": "干扰文档.docx"},
                {"filename": "目标文档.docx"},
            ],
        },
    )

    assert score["source_matches"] is True
    assert score["expected_source_rank"] == 2
    assert score["hit_at_1"] is False
    assert score["passed"] is True    


def test_score_excludes_multi_source_case_from_hit_at_1():
    score = score_retrieval_case(
        {
            "id": "rag-cross",
            "expected_sources": [
                "文档A.docx",
                "文档B.docx",
            ],
            "expected_retrieval_status": "ok",
        },
        {
            "retrieval_status": "ok",
            "evidences": [
                {"filename": "文档A.docx"},
                {"filename": "干扰文档.docx"},
            ],
        },
    )

    assert score["expected_source_count"] == 2
    assert score["expected_source_rank"] == 1
    assert score["hit_at_1"] is None
    assert score["source_matches"] is False
    assert score["passed"] is False


def test_summary_counts_false_positive_and_false_negative():
    summary = summarize_retrieval_scores(
        [
            {
                "expected_status": (
                    "no_reliable_evidence"
                ),
                "actual_status": "ok",
                "passed": False,
                "hit_at_1": None,
            },
            {
                "expected_status": "ok",
                "actual_status": (
                    "no_reliable_evidence"
                ),
                "passed": False,
                "hit_at_1": False,
            },
            {
                "expected_status": "ok",
                "actual_status": "ok",
                "passed": True,
                "hit_at_1": True,
            },
        ]
    )

    assert (
        summary[
            "false_positive_retrieval_cases"
        ]
        == 1
    )

    assert (
        summary[
            "false_negative_retrieval_cases"
        ]
        == 1
    )