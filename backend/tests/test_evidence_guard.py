from services.evidence_guard import (
    evidence_covers_query_anchors,
)


def test_allows_attention_when_evidence_mentions_it():
    assert evidence_covers_query_anchors(
        "Attention 在句子中主要负责什么？",
        ["Attention 用于识别词之间的关系。"],
    )


def test_rejects_gpu_when_evidence_does_not_mention_gpu():
    assert not evidence_covers_query_anchors(
        "Transformer 的训练使用了哪一款 GPU？",
        ["Transformer 使用 Attention 建模词之间关系。"],
    )


def test_rejects_ip_when_evidence_does_not_mention_ip():
    assert not evidence_covers_query_anchors(
        "模型部署服务器的 IP 地址是什么？",
        ["文档介绍了 Transformer 的 Attention 机制。"],
    )
    
def test_rejects_dataset_name_when_evidence_only_mentions_transformer():
    assert not evidence_covers_query_anchors(
        "根据我上传的文档，Transformer 的训练数据集名称是什么？",
        [
            "Transformer 的核心机制是 Attention，"
            "用于建模词之间的关系。"
        ],
    )    