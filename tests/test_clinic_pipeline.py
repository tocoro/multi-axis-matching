"""Clinic pipeline tests: 2ドメイン目の最小 E2E。"""

import json
from unittest.mock import patch

import pytest

from src.evaluator import validate_response
from src.pipeline.clinic_pipeline import run_clinic_pipeline

# Clinic-specific axes (restaurant とは異なる)
CLINIC_AXES = [
    {"axis": "specialty_fit", "weight": 0.30},
    {"axis": "distance", "weight": 0.20},
    {"axis": "hours", "weight": 0.20},
    {"axis": "insurance", "weight": 0.15},
    {"axis": "availability", "weight": 0.15},
]


def _clinic_llm_mock(system_prompt: str, user_message: str) -> dict:
    if "前処理" in system_prompt:
        return {
            "inferred_problem_type": "local.clinic",
            "confidence": 0.90,
            "reason": "Medical clinic query",
        }
    if "制約を抽出" in system_prompt:
        return {
            "hard_constraints": {"accepts_insurance": True},
            "soft_preferences": {"evening_hours": True},
            "notes": [],
        }
    if "評価軸選択" in system_prompt:
        return {"axes": CLINIC_AXES, "reason": "Clinic evaluation axes"}

    parsed = json.loads(user_message)
    cid = parsed["candidate"]["candidate_id"]

    evals = {
        "clinic_1": {
            "axis_scores": [
                {"axis": "specialty_fit", "score": 0.85, "status": "supported",
                 "reason": "Internal medicine matches", "hard_constraint_violation": False},
                {"axis": "distance", "score": 0.90, "status": "supported",
                 "reason": "Ebisu, 2 min walk", "hard_constraint_violation": False},
                {"axis": "hours", "score": 0.90, "status": "supported",
                 "reason": "Open until 20:00 weekdays", "hard_constraint_violation": False},
                {"axis": "insurance", "score": 0.90, "status": "supported",
                 "reason": "Insurance accepted", "hard_constraint_violation": False},
                {"axis": "availability", "score": 0.80, "status": "supported",
                 "reason": "Same-day available", "hard_constraint_violation": False},
            ],
            "strengths": ["Nearby", "Evening hours", "Same-day OK"],
            "weaknesses": [],
            "missing_information": [],
            "risk_notes": ["Medical: verify credentials independently"],
            "summary_reason": "Strong match for after-work internal medicine visit",
        },
        "clinic_2": {
            "axis_scores": [
                {"axis": "specialty_fit", "score": 0.75, "status": "supported",
                 "reason": "Has internal medicine + gastro specialty",
                 "hard_constraint_violation": False},
                {"axis": "distance", "score": 0.45, "status": "supported",
                 "reason": "Meguro, 10 min walk — somewhat far",
                 "hard_constraint_violation": False},
                {"axis": "hours", "score": 0.40, "status": "conflict",
                 "reason": "Closes at 18:00, user wants evening",
                 "hard_constraint_violation": False},
                {"axis": "insurance", "score": 0.90, "status": "supported",
                 "reason": "Insurance accepted", "hard_constraint_violation": False},
                {"axis": "availability", "score": 0.30, "status": "conflict",
                 "reason": "No same-day, appointment required",
                 "hard_constraint_violation": False},
            ],
            "strengths": ["Gastro specialist"],
            "weaknesses": ["Far", "Short hours", "No same-day"],
            "missing_information": [],
            "risk_notes": ["Medical: verify credentials independently"],
            "summary_reason": "Specialist but inconvenient hours and distance",
        },
        "clinic_3": {
            "axis_scores": [
                {"axis": "specialty_fit", "score": 0.15, "status": "conflict",
                 "reason": "Dermatology, not internal medicine",
                 "hard_constraint_violation": False},
                {"axis": "distance", "score": 0.80, "status": "supported",
                 "reason": "Shibuya, 3 min walk", "hard_constraint_violation": False},
                {"axis": "hours", "score": 0.70, "status": "supported",
                 "reason": "Open until 19:00", "hard_constraint_violation": False},
                {"axis": "insurance", "score": 0.90, "status": "supported",
                 "reason": "Insurance accepted", "hard_constraint_violation": False},
                {"axis": "availability", "score": 0.80, "status": "supported",
                 "reason": "Same-day available", "hard_constraint_violation": False},
            ],
            "strengths": ["Nearby", "Same-day OK"],
            "weaknesses": ["Wrong specialty"],
            "missing_information": [],
            "risk_notes": ["Medical: verify credentials independently"],
            "summary_reason": "Convenient but wrong specialty (dermatology)",
        },
        "clinic_4": {
            "axis_scores": [
                {"axis": "specialty_fit", "score": 0.0, "status": "unknown",
                 "reason": "No specialty information"},
                {"axis": "distance", "score": 0.0, "status": "unknown",
                 "reason": "No address"},
                {"axis": "hours", "score": 0.0, "status": "unknown",
                 "reason": "No hours information"},
                {"axis": "insurance", "score": 0.0, "status": "unknown",
                 "reason": "No insurance information"},
                {"axis": "availability", "score": 0.0, "status": "unknown",
                 "reason": "No availability information"},
            ],
            "strengths": [],
            "weaknesses": ["Very little information"],
            "missing_information": ["Specialty", "Address", "Hours", "Insurance", "Availability"],
            "risk_notes": ["Insufficient data", "Medical: verify credentials independently"],
            "summary_reason": "Almost no information available",
        },
    }
    data = evals.get(cid, evals["clinic_4"])
    return {"candidate_id": cid, **data}


QUERY = "恵比寿で夕方以降に内科を受診したい。保険適用希望"


# ===================================================================
# A. Pipeline returns valid response
# ===================================================================


class TestClinicPipelineE2E:
    @patch("src.evaluator.call_llm", side_effect=_clinic_llm_mock)
    def test_response_valid(self, _mock):
        r = run_clinic_pipeline("clinic-1", QUERY)
        validate_response(r)

    @patch("src.evaluator.call_llm", side_effect=_clinic_llm_mock)
    def test_ranking_has_4_candidates(self, _mock):
        r = run_clinic_pipeline("clinic-1", QUERY)
        assert len(r["ranking"]) == 4

    @patch("src.evaluator.call_llm", side_effect=_clinic_llm_mock)
    def test_ranks_sequential(self, _mock):
        r = run_clinic_pipeline("clinic-1", QUERY)
        assert [e["rank"] for e in r["ranking"]] == [1, 2, 3, 4]

    @patch("src.evaluator.call_llm", side_effect=_clinic_llm_mock)
    def test_clinic_1_ranked_first(self, _mock):
        r = run_clinic_pipeline("clinic-1", QUERY)
        assert r["ranking"][0]["candidate_id"] == "clinic_1"

    @patch("src.evaluator.call_llm", side_effect=_clinic_llm_mock)
    def test_problem_type_is_clinic(self, _mock):
        r = run_clinic_pipeline("clinic-1", QUERY)
        assert r["inferred_problem_type"] == "local.clinic"

    @patch("src.evaluator.call_llm", side_effect=_clinic_llm_mock)
    def test_needs_human_review_true(self, _mock):
        """clinic は高リスク領域 → needs_human_review = true。"""
        r = run_clinic_pipeline("clinic-1", QUERY)
        assert r["needs_human_review"] is True


# ===================================================================
# B. Clinic-specific axes
# ===================================================================


class TestClinicAxes:
    @patch("src.evaluator.call_llm", side_effect=_clinic_llm_mock)
    def test_axes_include_specialty(self, _mock):
        r = run_clinic_pipeline("clinic-2", QUERY)
        axes = {a["axis"] for a in r["selected_axes"]}
        assert "specialty_fit" in axes

    @patch("src.evaluator.call_llm", side_effect=_clinic_llm_mock)
    def test_axes_include_insurance(self, _mock):
        r = run_clinic_pipeline("clinic-2", QUERY)
        axes = {a["axis"] for a in r["selected_axes"]}
        assert "insurance" in axes

    @patch("src.evaluator.call_llm", side_effect=_clinic_llm_mock)
    def test_axes_differ_from_restaurant(self, _mock):
        """restaurant axes (cuisine, budget, atmosphere) とは異なる。"""
        r = run_clinic_pipeline("clinic-2", QUERY)
        axes = {a["axis"] for a in r["selected_axes"]}
        assert "cuisine" not in axes
        assert "budget" not in axes
        assert "atmosphere" not in axes


# ===================================================================
# C. Unknown for info-lacking candidate
# ===================================================================


class TestClinicUnknown:
    @patch("src.evaluator.call_llm", side_effect=_clinic_llm_mock)
    def test_clinic_4_has_all_unknown(self, _mock):
        r = run_clinic_pipeline("clinic-3", QUERY)
        c4 = next(e for e in r["ranking"] if e["candidate_id"] == "clinic_4")
        unknowns = [a for a in c4["axis_scores"] if a["status"] == "unknown"]
        assert len(unknowns) == 5

    @patch("src.evaluator.call_llm", side_effect=_clinic_llm_mock)
    def test_clinic_4_low_confidence(self, _mock):
        r = run_clinic_pipeline("clinic-3", QUERY)
        c4 = next(e for e in r["ranking"] if e["candidate_id"] == "clinic_4")
        assert c4["confidence"] == 0.0

    @patch("src.evaluator.call_llm", side_effect=_clinic_llm_mock)
    def test_clinic_4_has_missing_info(self, _mock):
        r = run_clinic_pipeline("clinic-3", QUERY)
        c4 = next(e for e in r["ranking"] if e["candidate_id"] == "clinic_4")
        assert len(c4["missing_information"]) >= 4


# ===================================================================
# D. Specialty mismatch as conflict (not hard violation)
# ===================================================================


class TestClinicConflict:
    @patch("src.evaluator.call_llm", side_effect=_clinic_llm_mock)
    def test_clinic_3_specialty_conflict(self, _mock):
        r = run_clinic_pipeline("clinic-4", QUERY)
        c3 = next(e for e in r["ranking"] if e["candidate_id"] == "clinic_3")
        spec = next(a for a in c3["axis_scores"] if a["axis"] == "specialty_fit")
        assert spec["status"] == "conflict"
        assert spec["hard_constraint_violation"] is False

    @patch("src.evaluator.call_llm", side_effect=_clinic_llm_mock)
    def test_clinic_3_not_disqualified(self, _mock):
        """specialty mismatch は conflict だが失格ではない。"""
        r = run_clinic_pipeline("clinic-4", QUERY)
        c3 = next(e for e in r["ranking"] if e["candidate_id"] == "clinic_3")
        assert c3["disqualified"] is False


# ===================================================================
# E. Restaurant path not broken
# ===================================================================


class TestRestaurantIntact:
    @patch("src.evaluator.call_llm")
    def test_restaurant_pipeline_still_works(self, mock_llm):
        """clinic 追加後も restaurant pipeline が正常動作する。"""
        # pipeline 用の mock を使う (place_3 を含む)
        from tests.test_restaurant_pipeline import _pipeline_llm_mock
        mock_llm.side_effect = _pipeline_llm_mock
        from src.pipeline.restaurant_pipeline import run_restaurant_pipeline
        r = run_restaurant_pipeline("compat", "恵比寿で静かに話せるイタリアン。予算は3000円以内")
        assert len(r["ranking"]) == 2
        assert r["inferred_problem_type"] == "local.restaurant"
