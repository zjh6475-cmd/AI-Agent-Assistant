def score_retrieval_case(
    case: dict,
    result: dict,
) -> dict:
    expected_status = case[
        "expected_retrieval_status"
    ]
    actual_status = result.get(
        "retrieval_status"
    )

    evidences = result.get(
        "evidences"
    ) or []

    # [新增] 保留 evidence 原始顺序，
    # 用于计算期望来源的实际排名。
    retrieved_filenames = [
        evidence["filename"]
        for evidence in evidences
        if evidence.get("filename")
    ]

    # [修改] 对外展示的来源仍然去重并排序。
    retrieved_sources = sorted(
        set(retrieved_filenames)
    )

    status_matches = (
        actual_status == expected_status
    )

    # [新增] 默认没有排名数据。
    expected_source_rank = None
    expected_source_count = None
    hit_at_1 = None

    if expected_status == "ok":
        expected_sources = case.get(
            "expected_sources"
        )

        if expected_sources is None:
            expected_sources = (
                [case["expected_source"]]
                if case["expected_source"]
                else []
            )

        expected_source_count = len(
            expected_sources
        )

        source_matches = all(
            source in retrieved_sources
            for source in expected_sources
        )

        # [新增] 找到所有期望来源的排名。
        expected_source_ranks = [
            index + 1
            for index, filename in enumerate(
                retrieved_filenames
            )
            if filename in expected_sources
        ]

        # [新增] 多个期望来源时，记录最靠前的一个排名。
        expected_source_rank = (
            min(expected_source_ranks)
            if expected_source_ranks
            else None
        )

        # [修改] 只有单一期望来源的 case 才参与 hit@1。
        # 跨文档 case 需要所有期望来源都被召回，
        # 不能因为其中一个来源排第一就算 hit@1。
        hit_at_1 = (
            expected_source_rank == 1
            if expected_source_count == 1
            else None
        )

        passed = (
            status_matches
            and source_matches
        )

    else:
        # 没有可靠证据的 case 不参与来源排名。
        source_matches = None
        expected_source_rank = None
        expected_source_count = None
        hit_at_1 = None

        passed = (
            status_matches
            and not evidences
        )

    return {
        "id": case["id"],
        "expected_status": expected_status,
        "actual_status": actual_status,
        "retrieved_sources": retrieved_sources,
        "status_matches": status_matches,
        "source_matches": source_matches,
        "expected_source_rank": (
            expected_source_rank
        ),
        "expected_source_count": (
            expected_source_count
        ),
        "hit_at_1": hit_at_1,
        "passed": passed,
        "anchor_check_passed": result.get(
            "anchor_check_passed"
        ),
        "rejection_reason": result.get(
            "rejection_reason"
        ),
    }
    
def summarize_retrieval_scores(
    scores: list[dict],
) -> dict:
    total_cases = len(scores)

    passed_cases = sum(
        score["passed"]
        for score in scores
    )

    source_scores = [
        score
        for score in scores
        if score["expected_status"] == "ok"
    ]

    source_recalled_cases = sum(
        score["passed"]
        for score in source_scores
    )

    # [修改] 只有单一期望来源的 case 才参与 hit@1。
    # 拒答 case 和跨文档 case 的 hit_at_1 都是 None，
    # 不应被当成排名失败。
    source_rank_scores = [
        score
        for score in source_scores
        if score.get("hit_at_1") is not None
    ]

    hit_at_1_cases = sum(
        score["hit_at_1"]
        for score in source_rank_scores
    )

    abstention_scores = [
        score
        for score in scores
        if score["expected_status"]
        == "no_reliable_evidence"
    ]

    correct_abstentions = sum(
        score["passed"]
        for score in abstention_scores
    )
    false_positive_retrieval_cases = sum(
        score.get("expected_status")
        == "no_reliable_evidence"
        and score.get("actual_status")
        == "ok"
        for score in scores
    ) 

    false_negative_retrieval_cases = sum(
       score.get("expected_status") == "ok"
       and score.get("actual_status")
       == "no_reliable_evidence"
       for score in scores
    )
    false_positive_retrieval_case_ids = [
       score.get("id")
       for score in scores
       if score.get("id")
       and score.get("expected_status")
       == "no_reliable_evidence"
       and score.get("actual_status")
       == "ok"
    ]

    false_negative_retrieval_case_ids = [
       score.get("id")
       for score in scores
       if score.get("id")
       and score.get("expected_status") == "ok"
       and score.get("actual_status")
       == "no_reliable_evidence"
    ]

    return {
        "total_cases": total_cases,
        "passed_cases": passed_cases,
        "case_pass_rate": (
            passed_cases / total_cases
            if total_cases
            else None
        ),
        "source_case_count": len(source_scores),
        "source_recalled_cases": (
            source_recalled_cases
        ),
        "source_recall_at_k": (
            source_recalled_cases
            / len(source_scores)
            if source_scores
            else None
        ),
        "hit_at_1_case_count": (
            len(source_rank_scores)
        ),
        "hit_at_1_cases": hit_at_1_cases,
        "hit_at_1_rate": (
            hit_at_1_cases
            / len(source_rank_scores)
            if source_rank_scores
            else None
        ),
        "abstention_case_count": (
            len(abstention_scores)
        ),
        "correct_abstentions": (
            correct_abstentions
        ),
        "abstention_accuracy": (
            correct_abstentions
            / len(abstention_scores)
            if abstention_scores
            else None
        ),
        "anchor_rejected_cases": sum(
            score.get("rejection_reason")
            == "evidence_anchor_missing"
            for score in scores
        ),
        "false_positive_retrieval_cases": (
            false_positive_retrieval_cases
        ),
        "false_negative_retrieval_cases": (
            false_negative_retrieval_cases
        ),
        "false_positive_retrieval_case_ids": (
             false_positive_retrieval_case_ids
        ),
        "false_negative_retrieval_case_ids": (
            false_negative_retrieval_case_ids
        ),
        
    }    
