import json
from time import perf_counter
from evals.answer_grounding import (
    check_answer_grounding,
)

def _content_to_text(content) -> str:
    if isinstance(content, str):
        return content

    return json.dumps(
        content,
        ensure_ascii=False,
        default=str,
    )


def collect_answer_reviews(
    cases: list[dict],
    *,
    user_id: int,
    run_graph_fn,
) -> dict:
    reviews = []

    for index, case in enumerate(
        cases,
        start=1,
    ):
        started_at = perf_counter()

        result = run_graph_fn(
            user_id=user_id,
            session_id=-index,
            question=case["question"],
            checkpoint_database=":memory:",
        )

        answer_ms = round(
            (perf_counter() - started_at) * 1000,
            2,
        )

        messages = result.get("messages") or []

        answer = (
            _content_to_text(messages[-1].content)
            if messages
            else "模型没有生成文字回答。"
        )

        reviews.append(
            {
                "id": case["id"],
                "expected_answer_status": case[
                    "expected_answer_status"
                ],
                "expected_evidence_keywords": case.get(
                    "expected_evidence_keywords",
                 [],
                ),
                "must_cite": case.get(
                    "must_cite",
                     False,
                     
                ),
                "abstention_reason": case.get(
                     "abstention_reason",
                     "evidence",
                     ),
                "allow_general_knowledge": case.get(
                   "allow_general_knowledge",
                     False,
                ),
                "expected_sources": case.get(
                   "expected_sources",
                       [],
                ),
                "actual_answer_status": None,
                "review_status": "pending",
                "answer": answer,
                "sources": result.get("sources") or [],
                "steps": result.get("steps") or [],
                "answer_ms": answer_ms,
            }
        )

    return {
        "summary": {
            "total_cases": len(reviews),
            "pending_review_cases": len(reviews),
            "average_answer_ms": (
                round(
                    sum(
                        review["answer_ms"]
                        for review in reviews
                    )
                    / len(reviews),
                    2,
                )
                if reviews
                else None
            ),
        },
        "cases": reviews,
    }
    
def finalize_answer_reviews(
    report: dict,
    reviewed_statuses: dict[str, str],
) -> dict:
    valid_statuses = {
        "answer_with_evidence",
        "abstain",
    }

    for case in report.get("cases", []):
        case_id = case["id"]

        if case_id not in reviewed_statuses:
            continue

        actual_status = reviewed_statuses[case_id]

        if actual_status not in valid_statuses:
            raise ValueError(
                f"未知回答状态：{actual_status}"
            )

        case["actual_answer_status"] = (
            actual_status
        )
        grounding_case = {
           **case,
          "expected_answer_status": actual_status,
        }
        grounding_result = check_answer_grounding(
            answer=case.get("answer", ""),
            case=grounding_case,
            sources=case.get("sources") or [],
        )

        case["grounding_check"] = (
            grounding_result["status"]
        )
        case["grounding_reason"] = (
            grounding_result["reason"]
        )
        case["unsupported_claims"] = (
            grounding_result["unsupported_claims"]
        )

        case["review_status"] = (
           "passed"
        if (
           actual_status
           == case["expected_answer_status"]
           and grounding_result["status"]
           == "passed"
        )
          else "failed"
    )
        

       

    cases = report.get("cases", [])

    reviewed_cases = [
        case
        for case in cases
        if case["review_status"] != "pending"
    ]

    passed_cases = [
        case
        for case in reviewed_cases
        if case["review_status"] == "passed"
    ]

    report["summary"][
        "reviewed_cases"
    ] = len(reviewed_cases)

    report["summary"][
        "passed_answer_cases"
    ] = len(passed_cases)

    report["summary"][
        "pending_review_cases"
    ] = len(cases) - len(reviewed_cases)

    report["summary"][
        "answer_pass_rate"
    ] = (
        len(passed_cases) / len(reviewed_cases)
        if reviewed_cases
        else None
    )

    return report    