import argparse
import json
from pathlib import Path

from evals.rag_answer_review import (
    collect_answer_reviews,
)


RAG_EVAL_CASES_FILE = (
    Path(__file__).resolve().parent
    / "rag_eval_cases.jsonl"
)


def load_cases() -> list[dict]:
    return [
        json.loads(line)
        for line in RAG_EVAL_CASES_FILE.read_text(
            encoding="utf-8",
        ).splitlines()
        if line.strip()
    ]


def select_cases(
    cases: list[dict],
    *,
    case_id: str | None,
) -> list[dict]:
    if case_id is None:
        return cases

    selected = [
        case
        for case in cases
        if case["id"] == case_id
    ]

    if not selected:
        raise ValueError(
            f"未知评测用例：{case_id}"
        )

    return selected


def write_report(
    report: dict,
    output_path: Path,
) -> None:
    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path.write_text(
        json.dumps(
            report,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )




def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--user-id",
        
        required=True,
        type=int,
    )
    parser.add_argument(
        "--case-id",
        
        default=None,
    )
    parser.add_argument(
        "--output",
        default=None,
    )

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    try:
        cases = select_cases(
            load_cases(),
            case_id=args.case_id,
        )
    except ValueError as exc:
        parser.error(str(exc))

    # 仅在真实运行时导入图与模型。
    from graph.project_graph import run_agent_graph

    report = collect_answer_reviews(
        cases,
        user_id=args.user_id,
        run_graph_fn=run_agent_graph,
    )
    if args.output:
        write_report(
            report,
            Path(args.output),
        )

    print(
        json.dumps(
            report,
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()