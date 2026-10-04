from evals.review_rag_answer import (
    build_parser,
)


def test_build_parser_reads_review_arguments():
    args = build_parser().parse_args(
        [
            "--input",
            "/app/data/eval_reports/rag-009.json",
            "--output",
            "/app/data/eval_reports/rag-009-reviewed.json",
            "--case-id",
            "rag-009",
            "--actual-status",
            "abstain",
        ]
    )

    assert args.case_id == "rag-009"
    assert args.actual_status == "abstain"
    assert args.input.endswith(
        "rag-009.json"
    )
    assert args.output.endswith(
        "rag-009-reviewed.json"
    )