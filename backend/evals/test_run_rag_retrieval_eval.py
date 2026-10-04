from evals.run_rag_retrieval_eval import (
    run_retrieval_evaluation,
    build_parser,
    warm_up_retrieval,
    calculate_p95,
)


def test_run_retrieval_evaluation_scores_cases_and_records_metrics():
    calls = []

    def fake_search_fn(
        *,
        query: str,
        user_id: str,
        k: int,
    ) -> dict:
        calls.append(
            {
                "query": query,
                "user_id": user_id,
                "k": k,
            }
        )

        if query == "Attention 是什么？":
            return {
                "retrieval_status": "ok",
                "evidences": [
                    {
                        "filename": (
                            "Transformer核心原理详解.docx"
                        ),
                    }
                ],
            }

        return {
            "retrieval_status": (
                "no_reliable_evidence"
            ),
            "evidences": [],
        }

    report = run_retrieval_evaluation(
        [
            {
                "id": "rag-001",
                "question": "Attention 是什么？",
                "expected_source": (
                    "Transformer核心原理详解.docx"
                ),
                "expected_retrieval_status": "ok",
            },
            {
                "id": "rag-002",
                "question": "月球基地预算是多少？",
                "expected_source": None,
                "expected_retrieval_status": (
                    "no_reliable_evidence"
                ),
            },
        ],
        user_id="test-user",
        k=3,
        search_fn=fake_search_fn,
    )

    assert calls == [
        {
            "query": "Attention 是什么？",
            "user_id": "test-user",
            "k": 3,
        },
        {
            "query": "月球基地预算是多少？",
            "user_id": "test-user",
            "k": 3,
        },
    ]

    assert report["summary"]["total_cases"] == 2
    assert report["summary"]["passed_cases"] == 2
    assert report["summary"]["source_recall_at_k"] == 1.0
    assert report["summary"]["abstention_accuracy"] == 1.0

    assert len(report["cases"]) == 2
    assert all(
        score["retrieval_ms"] >= 0
        for score in report["cases"]
    )
    assert (
            report["summary"]["p95_retrieval_ms"]
               is not None
       )

    assert (
          report["summary"]["p95_retrieval_ms"]
          >= report["summary"]["average_retrieval_ms"]
        )
    
def test_build_parser_parses_user_id_as_integer():
    args = build_parser().parse_args([
        "--user-id", "1",
        "--k", "3",
    ])

    assert args.user_id == 1
    assert isinstance(args.user_id, int)
    assert args.k == 3    
    
def test_calculate_p95_returns_nearest_rank_value():
    assert calculate_p95([]) is None
    assert calculate_p95(
        [10.0, 20.0, 30.0, 40.0]
    ) == 40.0    
    
def test_warm_up_retrieval_calls_initializer():
    calls = []

    def fake_initializer():
        calls.append(True)

    initialization_ms = warm_up_retrieval(
        fake_initializer,
    )

    assert calls == [True]
    assert initialization_ms >= 0    