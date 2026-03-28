"""Tests for multi-axis-matching evaluator."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from src.evaluator import (
    AXES_BY_TYPE,
    HIGH_RISK_TYPES,
    _parse_json_from_llm,
    aggregate_scores,
    check_disqualification,
    evaluate,
    get_axes_for_type,
    validate_request,
)

EXAMPLE_PATH = Path(__file__).resolve().parent.parent / "examples" / "restaurant.json"


# ---------------------------------------------------------------------------
# _parse_json_from_llm
# ---------------------------------------------------------------------------


class TestParseJsonFromLlm:
    def test_plain_json(self):
        assert _parse_json_from_llm('{"a": 1}') == {"a": 1}

    def test_code_block(self):
        raw = '```json\n{"a": 1}\n```'
        assert _parse_json_from_llm(raw) == {"a": 1}

    def test_invalid_json_raises(self):
        with pytest.raises(json.JSONDecodeError):
            _parse_json_from_llm("not json")


# ---------------------------------------------------------------------------
# get_axes_for_type
# ---------------------------------------------------------------------------


class TestGetAxes:
    def test_known_type(self):
        axes = get_axes_for_type("local.restaurant")
        assert len(axes) == 5
        assert sum(a["weight"] for a in axes) == pytest.approx(1.0)

    def test_unknown_type_returns_generic(self):
        axes = get_axes_for_type("unknown.type")
        assert len(axes) == 3
        assert axes[0]["axis"] == "relevance"

    def test_all_defined_types_weights_sum_to_one(self):
        for ptype, axes in AXES_BY_TYPE.items():
            total = sum(a["weight"] for a in axes)
            assert total == pytest.approx(1.0), f"{ptype} weights sum to {total}"


# ---------------------------------------------------------------------------
# aggregate_scores
# ---------------------------------------------------------------------------


class TestAggregateScores:
    AXES = [
        {"axis": "a", "weight": 0.5},
        {"axis": "b", "weight": 0.3},
        {"axis": "c", "weight": 0.2},
    ]

    def test_all_supported(self):
        scores = [
            {"axis": "a", "score": 0.8, "status": "supported"},
            {"axis": "b", "score": 0.6, "status": "supported"},
            {"axis": "c", "score": 1.0, "status": "supported"},
        ]
        total, conf = aggregate_scores(scores, self.AXES, is_high_risk=False)
        # (0.5*0.8 + 0.3*0.6 + 0.2*1.0) / 1.0 = 0.78
        assert total == pytest.approx(0.78, abs=1e-4)
        assert conf == pytest.approx(1.0)

    def test_unknown_excluded_from_denominator(self):
        scores = [
            {"axis": "a", "score": 0.8, "status": "supported"},
            {"axis": "b", "score": 0.0, "status": "unknown"},
            {"axis": "c", "score": 1.0, "status": "supported"},
        ]
        # valid weight = 0.5 + 0.2 = 0.7
        # weighted = 0.5*0.8 + 0.2*1.0 = 0.6
        # total = 0.6 / 0.7 ≈ 0.8571
        total, conf = aggregate_scores(scores, self.AXES, is_high_risk=False)
        assert total == pytest.approx(0.6 / 0.7, abs=1e-4)
        assert conf == pytest.approx(0.7, abs=1e-4)

    def test_all_unknown(self):
        scores = [
            {"axis": "a", "score": 0.0, "status": "unknown"},
            {"axis": "b", "score": 0.0, "status": "unknown"},
            {"axis": "c", "score": 0.0, "status": "unknown"},
        ]
        total, conf = aggregate_scores(scores, self.AXES, is_high_risk=False)
        assert total == 0.0
        assert conf == 0.0

    def test_high_risk_penalty(self):
        scores = [
            {"axis": "a", "score": 0.9, "status": "supported"},
            {"axis": "b", "score": 0.0, "status": "unknown"},
            {"axis": "c", "score": 0.0, "status": "unknown"},
        ]
        # valid weight = 0.5, total weight = 1.0 → confidence = 0.5 (< 0.7)
        # raw total = 0.9, penalty → 0.9 * 0.5 = 0.45
        total, conf = aggregate_scores(scores, self.AXES, is_high_risk=True)
        assert conf == pytest.approx(0.5)
        assert total == pytest.approx(0.45, abs=1e-4)

    def test_high_risk_no_penalty_when_confident(self):
        scores = [
            {"axis": "a", "score": 0.8, "status": "supported"},
            {"axis": "b", "score": 0.6, "status": "supported"},
            {"axis": "c", "score": 1.0, "status": "supported"},
        ]
        total, conf = aggregate_scores(scores, self.AXES, is_high_risk=True)
        assert conf == pytest.approx(1.0)
        assert total == pytest.approx(0.78, abs=1e-4)


# ---------------------------------------------------------------------------
# check_disqualification
# ---------------------------------------------------------------------------


class TestCheckDisqualification:
    def test_no_conflict(self):
        scores = [
            {"axis": "a", "score": 0.8, "status": "supported"},
            {"axis": "b", "score": 0.0, "status": "unknown"},
        ]
        disq, reasons = check_disqualification(scores)
        assert disq is False
        assert reasons == []

    def test_conflict_disqualifies(self):
        scores = [
            {"axis": "a", "score": 0.0, "status": "conflict", "reason": "Over budget"},
            {"axis": "b", "score": 0.8, "status": "supported"},
        ]
        disq, reasons = check_disqualification(scores)
        assert disq is True
        assert len(reasons) == 1
        assert "Over budget" in reasons[0]


# ---------------------------------------------------------------------------
# validate_request (schema validation)
# ---------------------------------------------------------------------------


class TestValidateRequest:
    def test_valid_example(self):
        data = json.loads(EXAMPLE_PATH.read_text(encoding="utf-8"))
        validate_request(data)  # should not raise

    def test_missing_fields(self):
        with pytest.raises(Exception):
            validate_request({"request_id": "x"})


# ---------------------------------------------------------------------------
# Full pipeline (LLM mocked)
# ---------------------------------------------------------------------------


def _make_mock_call_llm():
    """Return a side_effect function that responds per prompt file."""

    def mock_call_llm(system_prompt: str, user_message: str) -> dict:
        if "前処理" in system_prompt:
            return {
                "inferred_problem_type": "local.restaurant",
                "confidence": 0.92,
                "reason": "Restaurant query detected",
            }
        if "制約を抽出" in system_prompt:
            return {
                "hard_constraints": {"budget_max": 3000},
                "soft_preferences": {"atmosphere": "quiet"},
                "notes": [],
            }
        # evaluate_candidate
        return {
            "candidate_id": json.loads(user_message)["candidate"]["candidate_id"],
            "axis_scores": [
                {"axis": "cuisine_match", "score": 0.8, "status": "supported", "reason": "Italian"},
                {"axis": "budget_match", "score": 0.9, "status": "supported", "reason": "2500 < 3000"},
                {"axis": "atmosphere_match", "score": 0.7, "status": "supported", "reason": "Calm"},
                {"axis": "location_match", "score": 0.6, "status": "unknown", "reason": "No address"},
                {"axis": "rating", "score": 0.5, "status": "supported", "reason": "Average"},
            ],
            "strengths": ["Budget friendly"],
            "weaknesses": ["Location unknown"],
            "missing_information": ["Address not provided"],
            "risk_notes": [],
            "summary_reason": "Good match overall",
        }

    return mock_call_llm


class TestFullPipeline:
    @patch("src.evaluator.call_llm")
    def test_pipeline_returns_valid_response(self, mock_llm):
        mock_llm.side_effect = _make_mock_call_llm()

        request = json.loads(EXAMPLE_PATH.read_text(encoding="utf-8"))
        response = evaluate(request)

        assert response["request_id"] == "ex1"
        assert response["inferred_problem_type"] == "local.restaurant"
        assert len(response["ranking"]) == 2
        assert response["ranking"][0]["rank"] == 1
        assert response["ranking"][1]["rank"] == 2
        # First rank should have higher or equal score
        assert response["ranking"][0]["total_score"] >= response["ranking"][1]["total_score"]

    @patch("src.evaluator.call_llm")
    def test_disqualified_candidate_ranked_last(self, mock_llm):
        call_count = {"n": 0}

        def side_effect(system_prompt, user_message):
            if "前処理" in system_prompt:
                return {
                    "inferred_problem_type": "local.restaurant",
                    "confidence": 0.9,
                    "reason": "test",
                }
            if "制約を抽出" in system_prompt:
                return {"hard_constraints": {}, "soft_preferences": {}, "notes": []}

            call_count["n"] += 1
            if call_count["n"] == 1:
                # First candidate: high score but conflict
                return {
                    "candidate_id": "r1",
                    "axis_scores": [
                        {"axis": "cuisine_match", "score": 0.9, "status": "supported", "reason": "ok"},
                        {"axis": "budget_match", "score": 0.0, "status": "conflict", "reason": "Over budget"},
                        {"axis": "atmosphere_match", "score": 0.8, "status": "supported", "reason": "ok"},
                        {"axis": "location_match", "score": 0.7, "status": "supported", "reason": "ok"},
                        {"axis": "rating", "score": 0.8, "status": "supported", "reason": "ok"},
                    ],
                    "strengths": [],
                    "weaknesses": ["Over budget"],
                    "missing_information": [],
                    "risk_notes": [],
                    "summary_reason": "Disqualified",
                }
            # Second candidate: lower score but no conflict
            return {
                "candidate_id": "r2",
                "axis_scores": [
                    {"axis": "cuisine_match", "score": 0.5, "status": "supported", "reason": "ok"},
                    {"axis": "budget_match", "score": 0.8, "status": "supported", "reason": "ok"},
                    {"axis": "atmosphere_match", "score": 0.3, "status": "supported", "reason": "ok"},
                    {"axis": "location_match", "score": 0.4, "status": "supported", "reason": "ok"},
                    {"axis": "rating", "score": 0.5, "status": "supported", "reason": "ok"},
                ],
                "strengths": [],
                "weaknesses": [],
                "missing_information": [],
                "risk_notes": [],
                "summary_reason": "OK",
            }

        mock_llm.side_effect = side_effect

        request = json.loads(EXAMPLE_PATH.read_text(encoding="utf-8"))
        response = evaluate(request)

        # r1 is disqualified → ranked last
        assert response["ranking"][0]["candidate_id"] == "r2"
        assert response["ranking"][0]["disqualified"] is False
        assert response["ranking"][1]["candidate_id"] == "r1"
        assert response["ranking"][1]["disqualified"] is True

    @patch("src.evaluator.call_llm")
    def test_high_risk_sets_needs_human_review(self, mock_llm):
        def side_effect(system_prompt, user_message):
            if "前処理" in system_prompt:
                return {
                    "inferred_problem_type": "local.clinic",
                    "confidence": 0.85,
                    "reason": "Medical",
                }
            if "制約を抽出" in system_prompt:
                return {"hard_constraints": {}, "soft_preferences": {}, "notes": []}
            return {
                "candidate_id": "c1",
                "axis_scores": [
                    {"axis": "specialty_match", "score": 0.7, "status": "supported", "reason": "ok"},
                    {"axis": "accessibility", "score": 0.5, "status": "supported", "reason": "ok"},
                    {"axis": "reputation", "score": 0.6, "status": "supported", "reason": "ok"},
                    {"axis": "availability", "score": 0.0, "status": "unknown", "reason": "no info"},
                    {"axis": "location_match", "score": 0.8, "status": "supported", "reason": "ok"},
                ],
                "strengths": [],
                "weaknesses": [],
                "missing_information": ["Hours not listed"],
                "risk_notes": ["Medical advice — verify credentials"],
                "summary_reason": "Needs review",
            }

        mock_llm.side_effect = side_effect

        request = {
            "request_id": "clinic1",
            "user_query": "膝が痛い。近くの整形外科",
            "candidates": [
                {"candidate_id": "c1", "title": "Clinic X", "description": "整形外科"},
            ],
        }
        response = evaluate(request)

        assert response["needs_human_review"] is True
        assert response["inferred_problem_type"] == "local.clinic"
