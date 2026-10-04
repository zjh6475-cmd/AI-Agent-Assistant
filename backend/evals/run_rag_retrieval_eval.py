import argparse
import json
from pathlib import Path
from time import perf_counter
import math

from evals.rag_eval_scoring import (
    score_retrieval_case,
    summarize_retrieval_scores,
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

def warm_up_retrieval(initializer) -> float:
    started_at = perf_counter()

    initializer()

    return round(
        (perf_counter() - started_at) * 1000,
        2,
    )
def warm_up_search(
    search_fn,
    *,
    user_id: int,
    k: int,
) -> float:
    started_at = perf_counter()

    search_fn(
        query="评测预热查询",
        user_id=user_id,
        k=k,
    )

    return round(
        (perf_counter() - started_at) * 1000,
        2,
    )
def calculate_p95(
    values: list[float],
) -> float | None:
    if not values:
        return None

    ordered_values = sorted(values)

    rank = max(
        1,
        math.ceil(
            len(ordered_values) * 0.95
        ),
    )

    return round(
        ordered_values[rank - 1],
        2,
    )

def run_retrieval_evaluation(
    cases: list[dict],
    *,
    user_id: int,
    k: int,
    search_fn,
) -> dict:
    scores = []

    for case in cases:
        started_at = perf_counter()

        result = search_fn(
            query=case["question"],
            user_id=user_id,
            k=k,
        )

        retrieval_ms = round(
            (perf_counter() - started_at) * 1000,
            2,
        )

        score = score_retrieval_case(
            case,
            result,
        )

        score["retrieval_ms"] = retrieval_ms
        scores.append(score)

    summary = summarize_retrieval_scores(
        scores,
    )

    summary["average_retrieval_ms"] = (
        round(
            sum(
                score["retrieval_ms"]
                for score in scores
            )
            / len(scores),
            2,
        )
        if scores
        else None
    )
    
    summary["p95_retrieval_ms"] = calculate_p95(
    [
        score["retrieval_ms"]
        for score in scores
    ]
)


    return {
        "summary": summary,
        "cases": scores,
    }
    

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--user-id",
        required=True,
        type=int,
    )

    parser.add_argument(
        "--k",
        type=int,
        default=3,
    )

    return parser

def main():
    args = build_parser().parse_args()

    # 只在真正执行评测时才导入真实检索服务。
    from services.vector_service import (
        get_vector_db,
        search_chunks,
    )

    initialization_ms = warm_up_retrieval(
        get_vector_db,
    )
    warmup_search_ms = warm_up_search(
    search_chunks,
    user_id=args.user_id,
    k=args.k,
)

    report = {
        "initialization_ms": initialization_ms,
        "warmup_search_ms": warmup_search_ms,
        **run_retrieval_evaluation(
            load_cases(),
            user_id=args.user_id,
            k=args.k,
            search_fn=search_chunks,
        ),
    }

    print(
        json.dumps(
            report,
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()