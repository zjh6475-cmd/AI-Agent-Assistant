"""Run RAG answer evaluation through the same SSE API used by the frontend."""

import argparse
import json
import os
from pathlib import Path
from time import perf_counter
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from dotenv import load_dotenv

from auth import create_token
from evals.run_rag_answer_review import (
    load_cases,
    select_cases,
    write_report,
)


load_dotenv(
    Path(__file__).resolve().parents[1] / ".env"
)

DEFAULT_BASE_URL = os.getenv(
    "EVAL_API_BASE_URL",
    "http://frontend/api",
)

DEFAULT_TIMEOUT_SECONDS = 180.0


def parse_sse_block(
    block: str,
) -> tuple[str, object] | None:
    """解析一条 SSE 数据块。"""
    event_name = ""
    data_lines = []

    for line in block.splitlines():
        if line.startswith("event:"):
            event_name = line[6:].strip()

        elif line.startswith("data:"):
            data_lines.append(
                line[5:].strip()
            )

    if not event_name or not data_lines:
        return None

    try:
        data = json.loads(
            "\n".join(data_lines)
        )
    except json.JSONDecodeError as error:
        raise ValueError(
            f"无法解析 SSE 数据：{block!r}"
        ) from error

    return event_name, data


def parse_sse_events(lines):
    """从 SSE 字节流中解析事件。"""
    block_lines = []

    for raw_line in lines:
        if isinstance(raw_line, bytes):
            line = raw_line.decode("utf-8")
        else:
            line = raw_line

        line = line.rstrip("\r\n")

        if line == "":
            if block_lines:
                event = parse_sse_block(
                    "\n".join(block_lines)
                )

                if event is not None:
                    yield event

                block_lines = []

            continue

        block_lines.append(line)

    if block_lines:
        event = parse_sse_block(
            "\n".join(block_lines)
        )

        if event is not None:
            yield event


def request_stream_events(
    *,
    base_url: str,
    token: str,
    question: str,
    timeout: float,
):
    """调用前端使用的 Agent SSE 接口。"""
    endpoint = (
        f"{base_url.rstrip('/')}"
        "/agent/chat/stream"
    )

    body = json.dumps(
        {
            "message": question,
            "session_id": None,
        },
        ensure_ascii=False,
    ).encode("utf-8")

    request = Request(
        endpoint,
        data=body,
        method="POST",
        headers={
            "Accept": "text/event-stream",
            "Authorization": (
                f"Bearer {token}"
            ),
            "Content-Type": (
                "application/json"
            ),
        },
    )

    try:
        with urlopen(
            request,
            timeout=timeout,
        ) as response:
            status_code = getattr(
                response,
                "status",
                200,
            )

            if (
                status_code < 200
                or status_code >= 300
            ):
                raise RuntimeError(
                    "Agent SSE 请求失败："
                    f"HTTP {status_code}"
                )

            yield from parse_sse_events(
                response
            )

    except HTTPError as error:
        detail = error.read().decode(
            "utf-8",
            errors="replace",
        )

        raise RuntimeError(
            "Agent SSE 请求失败："
            f"HTTP {error.code} {detail}"
        ) from error

    except URLError as error:
        raise RuntimeError(
            "无法连接 Agent SSE 接口："
            f"{error.reason}"
        ) from error


def _sum_numeric_values(
    values: list,
) -> int | float | None:
    """
    汇总数值。

    只要某个调用没有返回有效数值，
    就返回 None，避免生成不完整统计。
    """
    if not values:
        return None

    if not all(
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        for value in values
    ):
        return None

    return sum(values)


def _collect_model_metrics(
    steps: list[dict],
) -> dict:
    """从每次 call_model 步骤中汇总模型指标。"""
    model_steps = [
        step
        for step in steps
        if (
            isinstance(step, dict)
            and step.get("name")
            == "call_model"
        )
    ]

    model_times = [
        step.get("model_ms")
        for step in model_steps
    ]

    model_ms_total = _sum_numeric_values(
        model_times
    )

    if model_ms_total is None:
        model_ms = None
    else:
        model_ms = round(
            float(model_ms_total),
            2,
        )

    tool_decision_model_ms = _sum_numeric_values(
        [
            step.get("model_ms")
            for step in model_steps
            if step.get("model_phase")
            == "tool_decision"
        ]
    )

    answer_generation_model_ms = _sum_numeric_values(
        [
            step.get("model_ms")
            for step in model_steps
            if step.get("model_phase")
            == "answer_generation"
        ]
    )

    usage_list = [
        step.get("usage") or {}
        for step in model_steps
    ]

    input_tokens = _sum_numeric_values(
        [
            usage.get("input_tokens")
            for usage in usage_list
        ]
    )

    output_tokens = _sum_numeric_values(
        [
            usage.get("output_tokens")
            for usage in usage_list
        ]
    )

    total_tokens = _sum_numeric_values(
        [
            usage.get("total_tokens")
            for usage in usage_list
        ]
    )

    return {
        "model_ms": model_ms,
        "tool_decision_model_ms": (
            None
            if tool_decision_model_ms is None
            else round(
                float(tool_decision_model_ms),
                2,
            )
        ),
        "answer_generation_model_ms": (
            None
            if answer_generation_model_ms is None
            else round(
                float(answer_generation_model_ms),
                2,
            )
        ),
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": total_tokens,
    }


def _collect_retrieval_ms(
    steps: list[dict],
) -> float | None:
    """汇总本次请求中成功完成的知识库检索耗时。"""
    retrieval_steps = [
        step
        for step in steps
        if (
            isinstance(step, dict)
            and step.get("name")
            == "search_knowledge_base"
            and step.get("status")
            == "success"
        )
    ]

    retrieval_total = _sum_numeric_values(
        [
            step.get("retrieval_ms")
            for step in retrieval_steps
        ]
    )

    if retrieval_total is None:
        return None

    return round(float(retrieval_total), 2)


def collect_stream_case(
    case: dict,
    *,
    user_id: int,
    base_url: str,
    token: str,
    timeout: float,
    stream_events_fn=request_stream_events,
) -> dict:
    """执行单条前端 SSE 评测。"""
    started_at = perf_counter()

    answer_parts = []
    sources = []
    steps = []
    session_id = None
    event_counts = {}
    completed = False
    error_message = None

    for event_name, data in stream_events_fn(
        base_url=base_url,
        token=token,
        question=case["question"],
        timeout=timeout,
    ):
        event_counts[event_name] = (
            event_counts.get(event_name, 0)
            + 1
        )

        if event_name == "session":
            session_id = data.get(
                "session_id"
            )

        elif event_name == "token":
            answer_parts.append(
                data.get("content") or ""
            )

        elif event_name in {
            "step",
            "retry",
        }:
            steps.append(data)

        elif event_name == "sources":
            sources = data or []

        elif event_name == "error":
            error_message = data.get(
                "message",
                "Agent 流式调用失败。",
            )

        elif event_name == "done":
            completed = True

    total_response_ms = round(
        (perf_counter() - started_at)
        * 1000,
        2,
    )

    if error_message:
        raise RuntimeError(error_message)

    if not completed:
        raise RuntimeError(
            "Agent SSE 流未收到 done 事件。"
        )

    answer = "".join(
        answer_parts
    ).strip()

    if not answer:
        answer = "模型没有生成文字回答。"

    model_metrics = (
        _collect_model_metrics(steps)
    )

    retrieval_ms = _collect_retrieval_ms(
        steps
    )

    return {
        "id": case["id"],
        "expected_answer_status": case[
            "expected_answer_status"
        ],
        "allow_general_knowledge": case.get(
            "allow_general_knowledge",
            False,
        ),
        "expected_evidence_keywords": (
            case.get(
                "expected_evidence_keywords",
                [],
            )
        ),
        "must_cite": case.get(
            "must_cite",
            False,
        ),
        "actual_answer_status": None,
        "review_status": "pending",
        "answer": answer,
        "sources": sources,
        "steps": steps,
        "answer_ms": total_response_ms,
        "total_response_ms": (
            total_response_ms
        ),
        "retrieval_ms": retrieval_ms,
        "model_ms": model_metrics[
            "model_ms"
        ],
        "tool_decision_model_ms": model_metrics[
            "tool_decision_model_ms"
        ],
        "answer_generation_model_ms": model_metrics[
            "answer_generation_model_ms"
        ],
        "input_tokens": model_metrics[
            "input_tokens"
        ],
        "output_tokens": model_metrics[
            "output_tokens"
        ],
        "total_tokens": model_metrics[
            "total_tokens"
        ],
        "session_id": session_id,
        "transport": "http_sse",
        "endpoint": "/agent/chat/stream",
        "event_counts": event_counts,
        "user_id": user_id,
    }


def collect_stream_reviews(
    cases: list[dict],
    *,
    user_id: int,
    base_url: str,
    timeout: float,
    token: str | None = None,
    stream_events_fn=request_stream_events,
) -> dict:
    """执行多条前端 SSE 评测。"""
    token = token or create_token(
        user_id
    )

    reviews = []

    for case in cases:
        reviews.append(
            collect_stream_case(
                case,
                user_id=user_id,
                base_url=base_url,
                token=token,
                timeout=timeout,
                stream_events_fn=(
                    stream_events_fn
                ),
            )
        )

    response_times = [
        review["total_response_ms"]
        for review in reviews
    ]
     # [新增] 明确命名：这是完整 SSE 请求的平均耗时，
    # 不是单纯回答生成模型的耗时。
    average_total_response_ms = (
        round(
            sum(response_times)
            / len(response_times),
            2,
        )
        if response_times
        else None
    )

    model_times = [
        review["model_ms"]
        for review in reviews
        if review["model_ms"] is not None
    ]

    retrieval_times = [
        review["retrieval_ms"]
        for review in reviews
        if review["retrieval_ms"] is not None
    ]

    # [本次新增] 汇集有工具决策模型耗时的 case。
    # is not None 会保留真实的 0，只排除“没有数据”的 case。
    tool_decision_times = [
        review["tool_decision_model_ms"]
        for review in reviews
        if review["tool_decision_model_ms"]
        is not None
    ]

    # [本次新增] 汇集有回答生成模型耗时的 case。
    answer_generation_times = [
        review["answer_generation_model_ms"]
        for review in reviews
        if review["answer_generation_model_ms"]
        is not None
    ]

    total_token_values = [
        review["total_tokens"]
        for review in reviews
        if review["total_tokens"]
        is not None
    ]

    return {
        "summary": {
            "total_cases": len(reviews),
            "pending_review_cases": len(
                reviews
            ),
            # [新增] 新代码和新报告使用语义明确的字段。
            "average_total_response_ms": (
                average_total_response_ms
            ),

            # [兼容保留] 旧字段复用新字段，避免重复计算和逻辑分叉。
            "average_answer_ms": average_total_response_ms,
            
            "average_model_ms": (
                round(
                    sum(model_times)
                    / len(model_times),
                    2,
                )
                if model_times
                else None
            ),

            # [本次新增] 多 case 的工具决策模型耗时平均值。
            "average_tool_decision_model_ms": (
                round(
                    sum(tool_decision_times)
                    / len(tool_decision_times),
                    2,
                )
                if tool_decision_times
                else None
            ),

            # [本次新增] 多 case 的回答生成模型耗时平均值。
            "average_answer_generation_model_ms": (
                round(
                    sum(answer_generation_times)
                    / len(answer_generation_times),
                    2,
                )
                if answer_generation_times
                else None
            ),

            "average_retrieval_ms": (
                round(
                    sum(retrieval_times)
                    / len(retrieval_times),
                    2,
                )
                if retrieval_times
                else None
            ),
            "average_total_tokens": (
                round(
                    sum(total_token_values)
                    / len(total_token_values),
                    2,
                )
                if total_token_values
                else None
            ),
            "transport": "http_sse",
            "endpoint": (
                "/agent/chat/stream"
            ),
        },
        "cases": reviews,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "通过前端使用的 "
            "/agent/chat/stream "
            "评测 RAG 回答。"
        )
    )

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
        "--base-url",
        default=DEFAULT_BASE_URL,
        help=(
            "API 基地址，例如 "
            "http://frontend/api"
        ),
    )

    parser.add_argument(
        "--timeout",
        type=float,
        default=DEFAULT_TIMEOUT_SECONDS,
    )

    parser.add_argument(
        "--token",
        default=None,
        help=(
            "可选：复用前端登录 Token；"
            "默认按 user-id 生成测试 Token。"
        ),
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

        report = collect_stream_reviews(
            cases,
            user_id=args.user_id,
            base_url=args.base_url,
            timeout=args.timeout,
            token=args.token,
        )

    except (
        RuntimeError,
        ValueError,
    ) as error:
        parser.error(str(error))

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