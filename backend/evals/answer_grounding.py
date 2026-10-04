import re


REFUSAL_MARKERS = (
    "当前知识库没有足够资料",
    "无法根据已上传文档",
    "没有检索到可靠证据",
    "无法确认",
    "不能编造",
    "无法给出确定答案",
)

UNSUPPORTED_KNOWLEDGE_MARKERS = (
    "通用知识",
    "并非来自",
    "文档之外",
    "根据常识",
    "例如",
)

CITATION_PATTERN = re.compile(
    r"\[来源[:：](?P<filename>[^；;\]]+)"
    r"(?:[；;]\s*证据ID[:：]"
    r"(?P<source_id>[^\]]+))?\]"
)


def check_citations(
    *,
    answer: str,
    sources: list[dict],
    must_cite: bool,
) -> dict | None:
    citations = list(
        CITATION_PATTERN.finditer(answer)
    )

    if must_cite and not citations:
        return {
            "status": "failed",
            "reason": (
                "回答要求引用来源，"
                "但回答中没有有效引用"
            ),
            "unsupported_claims": [],
        }

    if not citations:
        return None

    source_filenames = {
        str(source.get("filename"))
        for source in sources
        if isinstance(source, dict)
    }

    source_ids = {
        str(source.get("source_id"))
        for source in sources
        if isinstance(source, dict)
    }

    invalid_citations = []

    for citation in citations:
        filename = citation.group(
            "filename"
        ).strip()

        source_id = citation.group(
            "source_id"
        )

        if filename not in source_filenames:
            invalid_citations.append(
                f"不存在的文件名：{filename}"
            )

        if source_id:
            cited_source_ids = [
                item.strip()
                for item in re.split(
                    r"[、,，]\s*",
                    source_id,
                )
                if item.strip()
            ]

            for cited_source_id in cited_source_ids:
                if cited_source_id not in source_ids:
                    invalid_citations.append(
                        f"不存在的证据ID："
                        f"{cited_source_id}"
                    )

    if invalid_citations:
        return {
            "status": "failed",
            "reason": (
                "回答引用了不存在的来源或证据ID"
            ),
            "unsupported_claims": (
                invalid_citations
            ),
        }

    return None


def check_answer_grounding(
    *,
    answer: str,
    case: dict,
    sources: list[dict],
) -> dict:
    expected_status = case[
        "expected_answer_status"
    ]

    allow_general_knowledge = case.get(
        "allow_general_knowledge",
        False,
    )

    source_text = "\n".join(
        str(source.get("content", ""))
        for source in sources
        if isinstance(source, dict)
    )

    citation_result = check_citations(
        answer=answer,
        sources=sources,
        must_cite=case.get(
            "must_cite",
            False,
        ),
    )

    if citation_result is not None:
        return citation_result

    if expected_status == "abstain":
        abstention_reason = case.get(
            "abstention_reason",
            "evidence",
        )

        if abstention_reason == "permission":
            normalized_answer = re.sub(
             r"[*_`]",
             "",
             answer,
            )
            permission_markers = (
                "无法访问其他用户",
                "无法读取其他用户",
                "不能读取或检索其他用户",
                "只能访问当前登录用户",
                "只能访问当前登录用户自己",
                "没有权限",
            )

            has_permission_refusal = any(
                marker in normalized_answer
                for marker in permission_markers
            )

            if not has_permission_refusal:
                return {
                    "status": "failed",
                    "reason": (
                        "权限拒答没有明确说明访问边界"
                    ),
                    "unsupported_claims": [
                        answer
                    ],
                }

            if sources:
                return {
                    "status": "failed",
                    "reason": (
                        "权限拒答不应返回其他用户证据"
                    ),
                    "unsupported_claims": [
                        answer
                    ],
                }

            return {
                "status": "passed",
                "reason": (
                    "权限边界说明明确，"
                    "且没有返回未授权证据"
                ),
                "unsupported_claims": [],
            }

        has_refusal = any(
            marker in answer
            for marker in REFUSAL_MARKERS
        )

        if not has_refusal:
            return {
                "status": "failed",
                "reason": (
                    "拒答回答没有明确说明证据不足"
                ),
                "unsupported_claims": [
                    answer
                ],
            }

        if (
            not allow_general_knowledge
            and any(
                marker in answer
                for marker in (
                    UNSUPPORTED_KNOWLEDGE_MARKERS
                )
            )
        ):
            return {
                "status": "failed",
                "reason": (
                    "严格拒答回答中出现了"
                    "证据之外的知识补充"
                ),
                "unsupported_claims": [
                    answer
                ],
            }

        if (
            not allow_general_knowledge
            and not sources
        ):
            return {
                "status": "passed",
                "reason": (
                    "回答明确拒答，"
                    "且没有使用外部证据"
                ),
                "unsupported_claims": [],
            }

        return {
            "status": "passed",
            "reason": (
                "回答包含明确拒答说明"
            ),
            "unsupported_claims": [],
        }

    if expected_status == "answer_with_evidence":
        if not sources:
            return {
                "status": "failed",
                "reason": (
                    "回答要求有证据，"
                    "但没有返回证据"
                ),
                "unsupported_claims": [
                    answer
                ],
            }

        expected_keywords = case.get(
            "expected_evidence_keywords",
            [],
        )

        missing_source_keywords = [
            keyword
            for keyword in expected_keywords
            if keyword not in source_text
        ]

        if missing_source_keywords:
            return {
                "status": "failed",
                "reason": (
                    "证据中缺少预期关键词"
                ),
                "unsupported_claims": (
                    missing_source_keywords
                ),
            }

        missing_answer_keywords = [
            keyword
            for keyword in expected_keywords
            if keyword not in answer
        ]

        if missing_answer_keywords:
            return {
                "status": "failed",
                "reason": (
                    "回答中缺少预期证据关键词"
                ),
                "unsupported_claims": (
                    missing_answer_keywords
                ),
            }

        return {
            "status": "passed",
            "reason": (
                "回答存在证据，"
                "且回答和证据均包含预期关键词"
            ),
            "unsupported_claims": [],
        }

    return {
        "status": "not_applicable",
        "reason": "未知回答状态",
        "unsupported_claims": [],
    }