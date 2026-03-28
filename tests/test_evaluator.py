"""Tests for multi-axis-matching evaluator."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from src.evaluator import (
    HIGH_RISK_TYPES,
    _parse_json_from_llm,
    aggregate_scores,
    check_disqualification,
    evaluate,
    validate_request,
)

EXAMPLE_PATH = Path(__file__).resolve().parent.parent / "examples" / "restaurant.json"

# Axes used by mock LLM (select_axes step)
MOCK_AXES = [
    {"axis": "cuisine", "weight": 0.25},
    {"axis": "budget", "weight": 0.25},
    {"axis": "atmosphere", "weight": 0.2},
    {"axis": "location", "weight": 0.2},
    {"axis": "rating", "weight": 0.1},
]


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
        assert total == pytest.approx(0.78, abs=1e-4)
        assert conf == pytest.approx(1.0)

    def test_unknown_excluded_from_denominator(self):
        scores = [
            {"axis": "a", "score": 0.8, "status": "supported"},
            {"axis": "b", "score": 0.0, "status": "unknown"},
            {"axis": "c", "score": 1.0, "status": "supported"},
        ]
        total, conf = aggregate_scores(scores, self.AXES, is_high_risk=False)
        assert total == pytest.approx(0.6 / 0.7, abs=1e-4)
        assert conf == pytest.approx(0.7, abs=1e-4)

    def test_conflict_included_in_denominator(self):
        """conflict は低スコアとして集計に含める (unknown と違い除外しない)。"""
        scores = [
            {"axis": "a", "score": 0.8, "status": "supported"},
            {"axis": "b", "score": 0.2, "status": "conflict"},
            {"axis": "c", "score": 1.0, "status": "supported"},
        ]
        total, conf = aggregate_scores(scores, self.AXES, is_high_risk=False)
        # (0.5*0.8 + 0.3*0.2 + 0.2*1.0) / 1.0 = 0.66
        assert total == pytest.approx(0.66, abs=1e-4)
        assert conf == pytest.approx(1.0)

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
    def test_no_violation(self):
        scores = [
            {"axis": "a", "score": 0.8, "status": "supported"},
            {"axis": "b", "score": 0.0, "status": "unknown"},
        ]
        disq, reasons = check_disqualification(scores)
        assert disq is False
        assert reasons == []

    def test_conflict_without_hard_violation_does_not_disqualify(self):
        """conflict だが hard_constraint_violation=false → 失格にしない。"""
        scores = [
            {
                "axis": "atmosphere",
                "score": 0.2,
                "status": "conflict",
                "reason": "Noisy but user prefers quiet",
                "hard_constraint_violation": False,
            },
            {"axis": "budget", "score": 0.9, "status": "supported"},
        ]
        disq, reasons = check_disqualification(scores)
        assert disq is False
        assert reasons == []

    def test_hard_constraint_violation_disqualifies(self):
        """hard_constraint_violation=true → 失格。"""
        scores = [
            {
                "axis": "budget",
                "score": 0.0,
                "status": "conflict",
                "reason": "5000 exceeds max 3000",
                "hard_constraint_violation": True,
            },
            {"axis": "cuisine", "score": 0.9, "status": "supported"},
        ]
        disq, reasons = check_disqualification(scores)
        assert disq is True
        assert len(reasons) == 1
        assert "budget" in reasons[0]
        assert "5000 exceeds max 3000" in reasons[0]

    def test_mixed_violations(self):
        """複数軸: hard violation のある軸だけが失格理由になる。"""
        scores = [
            {
                "axis": "budget",
                "score": 0.0,
                "status": "conflict",
                "reason": "Over budget",
                "hard_constraint_violation": True,
            },
            {
                "axis": "atmosphere",
                "score": 0.3,
                "status": "conflict",
                "reason": "Noisy",
                "hard_constraint_violation": False,
            },
            {"axis": "cuisine", "score": 0.8, "status": "supported"},
        ]
        disq, reasons = check_disqualification(scores)
        assert disq is True
        assert len(reasons) == 1
        assert "budget" in reasons[0]


# ---------------------------------------------------------------------------
# validate_request (schema validation)
# ---------------------------------------------------------------------------


class TestValidateRequest:
    def test_valid_example(self):
        data = json.loads(EXAMPLE_PATH.read_text(encoding="utf-8"))
        validate_request(data)

    def test_missing_fields(self):
        with pytest.raises(Exception):
            validate_request({"request_id": "x"})


# ---------------------------------------------------------------------------
# Mock helper
# ---------------------------------------------------------------------------


def _dispatch_mock(system_prompt: str, user_message: str, eval_fn=None) -> dict:
    """Dispatch mock LLM call based on prompt content."""
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
    if "評価軸選択" in system_prompt:
        return {
            "axes": MOCK_AXES,
            "reason": "Restaurant-appropriate axes",
        }
    # evaluate_candidate — delegate to caller if provided
    if eval_fn:
        return eval_fn(system_prompt, user_message)
    # default evaluation
    return {
        "candidate_id": json.loads(user_message)["candidate"]["candidate_id"],
        "axis_scores": [
            {"axis": "cuisine", "score": 0.8, "status": "supported",
             "reason": "Italian", "hard_constraint_violation": False},
            {"axis": "budget", "score": 0.9, "status": "supported",
             "reason": "2500 < 3000", "hard_constraint_violation": False},
            {"axis": "atmosphere", "score": 0.7, "status": "supported",
             "reason": "Calm", "hard_constraint_violation": False},
            {"axis": "location", "score": 0.6, "status": "unknown",
             "reason": "No address"},
            {"axis": "rating", "score": 0.5, "status": "supported",
             "reason": "Average", "hard_constraint_violation": False},
        ],
        "strengths": ["Budget friendly"],
        "weaknesses": ["Location unknown"],
        "missing_information": ["Address not provided"],
        "risk_notes": [],
        "summary_reason": "Good match overall",
    }


# ---------------------------------------------------------------------------
# Full pipeline (LLM mocked)
# ---------------------------------------------------------------------------


class TestFullPipeline:
    @patch("src.evaluator.call_llm")
    def test_pipeline_returns_valid_response(self, mock_llm):
        mock_llm.side_effect = _dispatch_mock

        request = json.loads(EXAMPLE_PATH.read_text(encoding="utf-8"))
        response = evaluate(request)

        assert response["request_id"] == "ex1"
        assert response["inferred_problem_type"] == "local.restaurant"
        assert len(response["ranking"]) == 2
        assert response["ranking"][0]["rank"] == 1
        assert response["ranking"][1]["rank"] == 2
        assert response["ranking"][0]["total_score"] >= response["ranking"][1]["total_score"]

    @patch("src.evaluator.call_llm")
    def test_conflict_without_hard_violation_not_disqualified(self, mock_llm):
        """conflict (soft preference mismatch) は失格にならず低スコアになる。"""

        def eval_fn(_sys, user_message):
            return {
                "candidate_id": json.loads(user_message)["candidate"]["candidate_id"],
                "axis_scores": [
                    {"axis": "cuisine", "score": 0.8, "status": "supported",
                     "reason": "ok", "hard_constraint_violation": False},
                    {"axis": "budget", "score": 0.9, "status": "supported",
                     "reason": "ok", "hard_constraint_violation": False},
                    {"axis": "atmosphere", "score": 0.2, "status": "conflict",
                     "reason": "Noisy, user prefers quiet",
                     "hard_constraint_violation": False},
                    {"axis": "location", "score": 0.7, "status": "supported",
                     "reason": "ok", "hard_constraint_violation": False},
                    {"axis": "rating", "score": 0.6, "status": "supported",
                     "reason": "ok", "hard_constraint_violation": False},
                ],
                "strengths": [],
                "weaknesses": ["Noisy atmosphere"],
                "missing_information": [],
                "risk_notes": [],
                "summary_reason": "Good but noisy",
            }

        mock_llm.side_effect = lambda s, u: _dispatch_mock(s, u, eval_fn=eval_fn)

        request = json.loads(EXAMPLE_PATH.read_text(encoding="utf-8"))
        response = evaluate(request)

        for entry in response["ranking"]:
            assert entry["disqualified"] is False
            # conflict 軸はスコアに含まれる (低スコアとして)
            atm = [a for a in entry["axis_scores"] if a["axis"] == "atmosphere"][0]
            assert atm["status"] == "conflict"
            assert atm["score"] == 0.2

    @patch("src.evaluator.call_llm")
    def test_hard_constraint_violation_disqualifies(self, mock_llm):
        """hard_constraint_violation=true の候補だけが失格になる。"""
        call_count = {"n": 0}

        def eval_fn(_sys, user_message):
            call_count["n"] += 1
            if call_count["n"] == 1:
                # r1: budget に hard constraint violation
                return {
                    "candidate_id": "r1",
                    "axis_scores": [
                        {"axis": "cuisine", "score": 0.9, "status": "supported",
                         "reason": "ok", "hard_constraint_violation": False},
                        {"axis": "budget", "score": 0.0, "status": "conflict",
                         "reason": "5000 yen exceeds 3000 max",
                         "hard_constraint_violation": True},
                        {"axis": "atmosphere", "score": 0.8, "status": "supported",
                         "reason": "ok", "hard_constraint_violation": False},
                        {"axis": "location", "score": 0.7, "status": "supported",
                         "reason": "ok", "hard_constraint_violation": False},
                        {"axis": "rating", "score": 0.8, "status": "supported",
                         "reason": "ok", "hard_constraint_violation": False},
                    ],
                    "strengths": ["Great food"],
                    "weaknesses": ["Over budget"],
                    "missing_information": [],
                    "risk_notes": [],
                    "summary_reason": "Over hard budget limit",
                }
            # r2: conflict on atmosphere but NOT a hard constraint
            return {
                "candidate_id": "r2",
                "axis_scores": [
                    {"axis": "cuisine", "score": 0.5, "status": "supported",
                     "reason": "ok", "hard_constraint_violation": False},
                    {"axis": "budget", "score": 0.8, "status": "supported",
                     "reason": "ok", "hard_constraint_violation": False},
                    {"axis": "atmosphere", "score": 0.2, "status": "conflict",
                     "reason": "Noisy",
                     "hard_constraint_violation": False},
                    {"axis": "location", "score": 0.4, "status": "supported",
                     "reason": "ok", "hard_constraint_violation": False},
                    {"axis": "rating", "score": 0.5, "status": "supported",
                     "reason": "ok", "hard_constraint_violation": False},
                ],
                "strengths": [],
                "weaknesses": ["Noisy"],
                "missing_information": [],
                "risk_notes": [],
                "summary_reason": "OK but noisy",
            }

        mock_llm.side_effect = lambda s, u: _dispatch_mock(s, u, eval_fn=eval_fn)

        request = json.loads(EXAMPLE_PATH.read_text(encoding="utf-8"))
        response = evaluate(request)

        # r1 is disqualified (hard constraint), r2 is not (soft conflict only)
        r2_entry = next(e for e in response["ranking"] if e["candidate_id"] == "r2")
        r1_entry = next(e for e in response["ranking"] if e["candidate_id"] == "r1")

        assert r2_entry["disqualified"] is False
        assert r1_entry["disqualified"] is True
        assert "disqualification_reasons" in r1_entry
        assert any("budget" in r for r in r1_entry["disqualification_reasons"])

        # r2 should be ranked higher than r1
        assert r2_entry["rank"] < r1_entry["rank"]

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
            if "評価軸選択" in system_prompt:
                return {
                    "axes": [
                        {"axis": "specialty", "weight": 0.3},
                        {"axis": "accessibility", "weight": 0.2},
                        {"axis": "reputation", "weight": 0.2},
                        {"axis": "availability", "weight": 0.15},
                        {"axis": "location", "weight": 0.15},
                    ],
                    "reason": "Clinic axes",
                }
            return {
                "candidate_id": "c1",
                "axis_scores": [
                    {"axis": "specialty", "score": 0.7, "status": "supported",
                     "reason": "ok", "hard_constraint_violation": False},
                    {"axis": "accessibility", "score": 0.5, "status": "supported",
                     "reason": "ok", "hard_constraint_violation": False},
                    {"axis": "reputation", "score": 0.6, "status": "supported",
                     "reason": "ok", "hard_constraint_violation": False},
                    {"axis": "availability", "score": 0.0, "status": "unknown",
                     "reason": "no info"},
                    {"axis": "location", "score": 0.8, "status": "supported",
                     "reason": "ok", "hard_constraint_violation": False},
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
