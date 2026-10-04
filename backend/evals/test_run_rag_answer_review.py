from evals.run_rag_answer_review import (
    build_parser,
    select_cases,
    write_report,
)
import json

def test_select_cases_returns_requested_case():
    cases = [
        {"id": "rag-001"},
        {"id": "rag-009"},
    ]

    selected = select_cases(
        cases,
        case_id="rag-009",
    )

    assert selected == [
        {"id": "rag-009"}
    ]


def test_build_parser_reads_user_and_case_id():
    args = build_parser().parse_args(
        [
            "--user-id",
            "1",
            "--case-id",
            "rag-009",
        ]
    )

    assert args.user_id == 1
    assert isinstance(args.user_id, int)
    assert args.case_id == "rag-009"
    
    
def test_write_report_creates_utf8_json(
    tmp_path,
):
    report = {
        "summary": {
            "total_cases": 1,
        },
        "cases": [
            {
                "id": "rag-009",
            }
        ],
    }

    output_path = (
        tmp_path
        / "reports"
        / "rag-009.json"
    )

    write_report(
        report,
        output_path,
    )

    saved_report = json.loads(
        output_path.read_text(
            encoding="utf-8",
        )
    )

    assert saved_report == report    