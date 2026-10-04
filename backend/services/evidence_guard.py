import re


_ASCII_ANCHOR_PATTERN = re.compile(
    r"[A-Za-z][A-Za-z0-9._-]{1,}",
)
_IGNORED_FILE_EXTENSIONS = {
    "docx",
    "pdf",
    "txt",
    "md",
    "csv",
    "xlsx",
}
_CHINESE_ANCHOR_PHRASES = (
    "训练数据集",
    "矩阵维度",
    "注意力公式",
    "部署服务器",
    "上线日期",
    "预算",
)

def extract_required_anchors(
    query: str,
) -> set[str]:
    anchors = set()

    for match in _ASCII_ANCHOR_PATTERN.finditer(
        query
    ):
        anchor = match.group(0).lower()

        if anchor not in _IGNORED_FILE_EXTENSIONS:
            anchors.add(anchor)

    anchors.update(
        phrase
        for phrase in _CHINESE_ANCHOR_PHRASES
        if phrase in query
    )

    return anchors


def evidence_covers_query_anchors(
    query: str,
    evidence_texts: list[str],
) -> bool:
    required_anchors = extract_required_anchors(query)

    if not required_anchors:
        return True

    combined_evidence = " ".join(
        evidence_texts,
    ).lower()

    return all(
        anchor in combined_evidence
        for anchor in required_anchors
    )