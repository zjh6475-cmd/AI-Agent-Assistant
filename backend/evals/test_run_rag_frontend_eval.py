from evals.run_rag_frontend_eval import (
    build_parser,
    collect_stream_reviews,
    parse_sse_events,
)


def test_parse_sse_events_reads_frontend_event_format():
    chunks = [
        b"event: session\n",
        b'data: {"session_id": 7}\n',
        b"\n",
        b"event: token\n",
        'data: {"content": "你好"}\n'.encode("utf-8"),
        b"\n",
        b"event: done\n",
        b'data: {"session_id": 7}\n',
        b"\n",
    ]

    assert list(parse_sse_events(chunks)) == [
        ("session", {"session_id": 7}),
        ("token", {"content": "你好"}),
        ("done", {"session_id": 7}),
    ]


def test_collect_stream_reviews_builds_pending_report():
    def fake_stream_events(**kwargs):
        assert kwargs["base_url"] == "http://frontend/api"
        assert kwargs["question"] == "Attention 是什么？"

        yield "session", {"session_id": 18}

        # 模拟检索开始：此事件没有耗时
        yield "step", {
            "name": "search_knowledge_base",
            "status": "running",
            "message": "正在检索知识库",
        }

        # 模拟检索完成：此事件包含耗时
        yield "step", {
            "name": "search_knowledge_base",
            "status": "success",
            "message": "检索完成",
            "retrieval_ms": 234.56,
        }

        # 模拟一次工具决策阶段的模型调用
        yield "step", {
            "name": "call_model",
            "status": "success",
            "model_ms": 120.0,
            "model_phase": "tool_decision",
        }

        # 模拟一次回答生成阶段的模型调用
        yield "step", {
            "name": "call_model",
            "status": "success",
            "model_ms": 80.0,
            "model_phase": "answer_generation",
        }

        yield "token", {
            "content": "Attention 是注意力机制。"
        }
        yield "sources", [
            {"filename": "Transformer.docx"}
        ]
        yield "done", {"session_id": 18}

    report = collect_stream_reviews(
        [
            {
                "id": "rag-001",
                "question": "Attention 是什么？",
                "expected_answer_status": (
                    "answer_with_evidence"
                ),
            }
        ],
        user_id=1,
        base_url="http://frontend/api",
        timeout=10,
        token="test-token",
        stream_events_fn=fake_stream_events,
    )

    case = report["cases"][0]

    assert report["summary"]["transport"] == "http_sse"
    assert case["actual_answer_status"] is None
    assert case["review_status"] == "pending"
    assert case["answer"] == "Attention 是注意力机制。"
    assert case["session_id"] == 18
    assert case["retrieval_ms"] == 234.56

    assert case["model_ms"] == 200.0
    assert case["tool_decision_model_ms"] == 120.0
    assert case["answer_generation_model_ms"] == 80.0
    # [新增] 单 case 时，summary 的端到端平均值等于该 case 的总耗时。
    assert (
        report["summary"]["average_total_response_ms"]
        == case["total_response_ms"]
    )

    # [新增] 旧字段保留兼容，并与新字段一致。
    assert (
        report["summary"]["average_answer_ms"]
        == report["summary"]["average_total_response_ms"]
    )

    assert (
        report["summary"]["average_retrieval_ms"]
        == 234.56
    )
    assert case["event_counts"] == {
        "session": 1,
        "step": 4,
        "token": 1,
        "sources": 1,
        "done": 1,
    }

# [新增] 验证 None 不参与平均值，真实的 0 会参与平均值。
def test_collect_stream_reviews_distinguishes_none_and_zero_retrieval_ms():
    def fake_stream_events(**kwargs):
        question = kwargs["question"]

        yield "session", {"session_id": 20}

        if question == "正常检索":
            yield "step", {
                "name": "search_knowledge_base",
                "status": "success",
                "retrieval_ms": 400.0,
            }
        elif question == "零耗时检索":
            yield "step", {
                "name": "search_knowledge_base",
                "status": "success",
                "retrieval_ms": 0.0,
            }
        # “不检索” case 不产生 search_knowledge_base step，
        # 因此 retrieval_ms 应为 None。

        yield "token", {"content": "测试回答"}
        yield "done", {"session_id": 20}

    report = collect_stream_reviews(
        [
            {
                "id": "retrieval-400",
                "question": "正常检索",
                "expected_answer_status": "answer_with_evidence",
            },
            {
                "id": "retrieval-none",
                "question": "不检索",
                "expected_answer_status": "answer_without_evidence",
            },
            {
                "id": "retrieval-zero",
                "question": "零耗时检索",
                "expected_answer_status": "answer_with_evidence",
            },
        ],
        user_id=1,
        base_url="http://frontend/api",
        timeout=10,
        token="test-token",
        stream_events_fn=fake_stream_events,
    )

    cases = report["cases"]

    # [新增] 分别确认 400、None、0 被正确解析。
    assert cases[0]["retrieval_ms"] == 400.0
    assert cases[1]["retrieval_ms"] is None
    assert cases[2]["retrieval_ms"] == 0.0

    # [新增] None 被排除，0 被保留：(400 + 0) / 2 = 200。
    assert report["summary"]["average_retrieval_ms"] == 200.0


def test_build_parser_supports_frontend_endpoint_options():
    args = build_parser().parse_args(
        [
            "--user-id",
            "1",
            "--case-id",
            "rag-009",
            "--base-url",
            "http://frontend/api",
            "--timeout",
            "240",
        ]
    )

    assert args.user_id == 1
    assert args.case_id == "rag-009"
    assert args.base_url == "http://frontend/api"
    assert args.timeout == 240