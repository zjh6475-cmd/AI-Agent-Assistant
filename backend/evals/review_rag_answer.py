import argparse
import json
from pathlib import Path

from evals.rag_answer_review import (
    finalize_answer_reviews,
)
from evals.run_rag_answer_review import (
    write_report,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--input",
        required=True,
    )
    parser.add_argument(
        "--output",
        required=True,
    )
    parser.add_argument(
        "--case-id",
        required=True,
    )
    parser.add_argument(
        "--actual-status",
        required=True,
        choices=[
            "answer_with_evidence",
            "abstain",
        ],
    )

    return parser


def main():
    args = build_parser().parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)

    report = json.loads(
        input_path.read_text(
            encoding="utf-8",
        )
    )

    reviewed_report = finalize_answer_reviews(
        report,
        {
            args.case_id: args.actual_status,
        },
    )

    write_report(
        reviewed_report,
        output_path,
    )

    print(
        json.dumps(
            reviewed_report,
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()