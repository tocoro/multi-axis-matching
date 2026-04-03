"""Solution Catalog ablation comparison tests."""

import json

import pytest

from src.experiments.catalog_ablation import run_ablation
from src.mock import MOCK_AXES


# ---------------------------------------------------------------------------
# Catalog-aware mock evaluator
# ---------------------------------------------------------------------------

def _ablation_llm_mock(system_prompt: str, user_message: str) -> dict:
    """catalog の有無で reason / confidence を少し変える mock。"""
    if "前処理" in system_prompt:
        return {
            "inferred_problem_type": "local.restaurant",
            "confidence": 0.92,
            "reason": "Restaurant query",
        }
    if "制約を抽出" in system_prompt:
        return {
            "hard_constraints": {"budget_max": 3000},
            "soft_preferences": {"atmosphere": "quiet"},
            "notes": [],
        }
    if "評価軸選択" in system_prompt:
        return {"axes": MOCK_AXES, "reason": "Restaurant axes"}

    parsed = json.loads(user_message)
    cid = parsed["candidate"]["candidate_id"]
    has_catalog = "solution_catalog" in parsed

    # Case 1: place_1 — quiet_conversation claim の効果
    if cid == "place_1":
        atmo_reason = (
            "Quiet atmosphere, supported by solution catalog quiet_conversation claim"
            if has_catalog
            else "Quiet keyword present in description"
        )
        return {
            "candidate_id": cid,
            "axis_scores": [
                {"axis": "cuisine", "score": 0.85, "status": "supported",
                 "reason": "Italian", "hard_constraint_violation": False},
                {"axis": "budget", "score": 0.90, "status": "supported",
                 "reason": "Within budget", "hard_constraint_violation": False},
                {"axis": "atmosphere", "score": 0.90 if has_catalog else 0.80,
                 "status": "supported",
                 "reason": atmo_reason,
                 "hard_constraint_violation": False},
                {"axis": "location", "score": 0.90, "status": "supported",
                 "reason": "In Ebisu", "hard_constraint_violation": False},
                {"axis": "rating", "score": 0.0, "status": "unknown",
                 "reason": "No rating data"},
            ],
            "strengths": ["Quiet Italian"],
            "weaknesses": [],
            "missing_information": ["Rating"],
            "risk_notes": [],
            "summary_reason": "Strong match",
        }

    # Case 2: place_3 — limitation の補助効果
    if cid == "place_3":
        loc_reason = (
            "Nakameguro, not Ebisu. Solution catalog notes ebisu_area limitation"
            if has_catalog
            else "Nakameguro, not Ebisu as requested"
        )
        return {
            "candidate_id": cid,
            "axis_scores": [
                {"axis": "cuisine", "score": 0.85, "status": "supported",
                 "reason": "Italian", "hard_constraint_violation": False},
                {"axis": "budget", "score": 0.90, "status": "supported",
                 "reason": "Affordable", "hard_constraint_violation": False},
                {"axis": "atmosphere", "score": 0.85, "status": "supported",
                 "reason": "Quiet hideaway", "hard_constraint_violation": False},
                {"axis": "location", "score": 0.15 if has_catalog else 0.20,
                 "status": "conflict",
                 "reason": loc_reason,
                 "hard_constraint_violation": True},
                {"axis": "rating", "score": 0.0, "status": "unknown",
                 "reason": "No rating data"},
            ],
            "strengths": ["Quality Italian"],
            "weaknesses": ["Not in Ebisu"],
            "missing_information": ["Rating"],
            "risk_notes": [],
            "summary_reason": "Good but wrong location",
        }

    # Default
    return {
        "candidate_id": cid,
        "axis_scores": [
            {"axis": "cuisine", "score": 0.5, "status": "supported",
             "reason": "Generic", "hard_constraint_violation": False},
            {"axis": "budget", "score": 0.7, "status": "supported",
             "reason": "OK", "hard_constraint_violation": False},
            {"axis": "atmosphere", "score": 0.5, "status": "supported",
             "reason": "Average", "hard_constraint_violation": False},
            {"axis": "location", "score": 0.5, "status": "supported",
             "reason": "OK", "hard_constraint_violation": False},
            {"axis": "rating", "score": 0.0, "status": "unknown",
             "reason": "No data"},
        ],
        "strengths": [], "weaknesses": [], "missing_information": [],
        "risk_notes": [], "summary_reason": "Default",
    }


QUERY = "恵比寿で静かに話せるイタリアン。予算は3000円以内"


# ===================================================================
# A. Comparison output structure
# ===================================================================


class TestComparisonOutput:
    def test_has_required_keys(self):
        r = run_ablation("abl-1", QUERY, llm_mock_fn=_ablation_llm_mock)
        assert "query" in r
        assert "with_catalog" in r
        assert "without_catalog" in r
        assert "diff_summary" in r

    def test_diff_summary_has_fields(self):
        r = run_ablation("abl-1", QUERY, llm_mock_fn=_ablation_llm_mock)
        d = r["diff_summary"]
        assert "ranking_changed" in d
        assert "score_changes" in d
        assert "confidence_changes" in d
        assert "unknown_changes" in d
        assert "reason_changes" in d

    def test_both_conditions_have_ranking(self):
        r = run_ablation("abl-1", QUERY, llm_mock_fn=_ablation_llm_mock)
        assert len(r["with_catalog"]["ranking"]) >= 1
        assert len(r["without_catalog"]["ranking"]) >= 1


# ===================================================================
# B. Confidence / reason differences
# ===================================================================


class TestCatalogEffect:
    def test_atmosphere_reason_changes_with_catalog(self):
        """place_1 の atmosphere reason が catalog 参照で変わる。"""
        r = run_ablation("abl-2", QUERY, llm_mock_fn=_ablation_llm_mock)
        d = r["diff_summary"]
        assert "place_1" in d["reason_changes"]
        assert "atmosphere" in d["reason_changes"]["place_1"]

    def test_score_changes_exist(self):
        """catalog あり/なしで total_score に差が出る。"""
        r = run_ablation("abl-2", QUERY, llm_mock_fn=_ablation_llm_mock)
        d = r["diff_summary"]
        assert len(d["score_changes"]) > 0

    def test_location_reason_changes_for_place_3(self):
        """place_3 の location reason が catalog limitation 参照で変わる。"""
        r = run_ablation("abl-2", QUERY, llm_mock_fn=_ablation_llm_mock)
        d = r["diff_summary"]
        assert "place_3" in d["reason_changes"]
        assert "location" in d["reason_changes"]["place_3"]


# ===================================================================
# C. Backward compatibility
# ===================================================================


class TestAblationBackwardCompat:
    def test_both_conditions_valid_responses(self):
        from src.evaluator import validate_response
        r = run_ablation("abl-3", QUERY, llm_mock_fn=_ablation_llm_mock)
        validate_response(r["with_catalog"])
        validate_response(r["without_catalog"])


# ===================================================================
# D. No overclaim
# ===================================================================


class TestNoOverclaim:
    def test_unknown_not_reduced_by_catalog(self):
        """catalog があっても unknown 数は減らない (mock 設計上同数)。"""
        r = run_ablation("abl-4", QUERY, llm_mock_fn=_ablation_llm_mock)
        d = r["diff_summary"]
        # unknown_changes が空 = 変化なし
        assert d["unknown_changes"] == {}

    def test_place_3_still_disqualified_with_catalog(self):
        """catalog limitation があっても disqualify ロジックは既存のまま。"""
        r = run_ablation("abl-4", QUERY, llm_mock_fn=_ablation_llm_mock)
        p3_with = next(
            e for e in r["with_catalog"]["ranking"]
            if e["candidate_id"] == "place_3"
        )
        p3_without = next(
            e for e in r["without_catalog"]["ranking"]
            if e["candidate_id"] == "place_3"
        )
        assert p3_with["disqualified"] == p3_without["disqualified"]


# ===================================================================
# E. Deterministic
# ===================================================================


class TestDeterministic:
    def test_same_input_same_output(self):
        r1 = run_ablation("abl-det", QUERY, llm_mock_fn=_ablation_llm_mock)
        r2 = run_ablation("abl-det", QUERY, llm_mock_fn=_ablation_llm_mock)
        assert r1["diff_summary"] == r2["diff_summary"]
