import json
from pathlib import Path


RAG_EVAL_CASES_FILE = (
    Path(__file__).resolve().parent
    / "rag_eval_cases.jsonl"
)

REQUIRED_FIELDS = {
    "id",
    "category",
    "question",
    "expected_source",
    "expected_evidence_keywords",
    "allow_general_knowledge",
    "expected_retrieval_status",
    "must_cite",
    "expected_answer_status",
}


def load_cases():
    return [
        json.loads(line)
        for line in RAG_EVAL_CASES_FILE.read_text(
            encoding="utf-8",
        ).splitlines()
        if line.strip()
    ]


def test_rag_eval_cases_have_required_fields_and_unique_ids():
    cases = load_cases()

    assert len(cases) >= 2

    ids = set()


    for case in cases:
        assert REQUIRED_FIELDS <= set(case)
        if "expected_sources" in case:
            assert isinstance(
                case["expected_sources"],
                list,
            )
            assert case["expected_sources"]
            assert all(
                isinstance(source, str)
                and source.strip()
                for source in case["expected_sources"]
            )
            
            
            
        assert case["id"] not in ids
        assert case["question"].strip()
        assert isinstance(
            case["expected_evidence_keywords"],
            list,
        )
        assert isinstance(
            case["allow_general_knowledge"],
            bool,
        )
        assert isinstance(
            case["must_cite"],
            bool,
        )
        assert case["expected_answer_status"] in {
            "answer_with_evidence",
            "abstain",
        }
        
           
        ids.add(case["id"])
       


def test_rag_eval_case_expectations_match_retrieval_status():
    for case in load_cases():
        status = case["expected_retrieval_status"]

        assert status in {
            "ok",
            "no_reliable_evidence",
        }
        assert case["expected_answer_status"] in {
            "answer_with_evidence",
            "abstain",
        }

        if status == "ok":
            expected_sources = case.get(
                "expected_sources"
            )

            if expected_sources is None:
                expected_sources = [
                    case["expected_source"]
                ]

            assert expected_sources
            assert case["expected_evidence_keywords"]
            assert case["must_cite"] is True
            assert case["expected_answer_status"] == (
                "answer_with_evidence"
            )
        else:
            assert case["expected_source"] is None
            assert case.get(
                "expected_sources",
                [],
            ) == []
            assert case["expected_evidence_keywords"] == []
            assert case["must_cite"] is False
            assert case["expected_answer_status"] == (
                "abstain"
            )