"""Multi-domain solution catalog ablation tests."""

import json

import pytest

from src.experiments.multi_domain_catalog_ablation import run_multi_domain_ablation
from src.mock import MOCK_AXES

# Clinic-specific axes
CLINIC_AXES = [
    {"axis": "specialty_fit", "weight": 0.30},
    {"axis": "distance", "weight": 0.20},
    {"axis": "hours", "weight": 0.20},
    {"axis": "insurance", "weight": 0.15},
    {"axis": "availability", "weight": 0.15},
]


def _multi_domain_llm_mock(system_prompt: str, user_message: str) -> dict:
    """Restaurant + clinic 対応の catalog-aware mock。"""
    if "前処理" in system_prompt:
        # query 内容から problem type を判定
        if "内科" in user_message or "クリニック" in user_message or "受診" in user_message:
            return {
                "inferred_problem_type": "local.clinic",
                "confidence": 0.90,
                "reason": "Clinic query",
            }
        return {
            "inferred_problem_type": "local.restaurant",
            "confidence": 0.92,
            "reason": "Restaurant query",
        }

    if "制約を抽出" in system_prompt:
        if "内科" in user_message or "保険" in user_message:
            return {
                "hard_constraints": {"accepts_insurance": True},
                "soft_preferences": {"evening_hours": True},
                "notes": [],
            }
        return {
            "hard_constraints": {"budget_max": 3000},
            "soft_preferences": {"atmosphere": "quiet"},
            "notes": [],
        }

    if "評価軸選択" in system_prompt:
        parsed = json.loads(user_message)
        if parsed.get("problem_type") == "local.clinic":
            return {"axes": CLINIC_AXES, "reason": "Clinic axes"}
        return {"axes": MOCK_AXES, "reason": "Restaurant axes"}

    # evaluate_candidate
    parsed = json.loads(user_message)
    cid = parsed["candidate"]["candidate_id"]
    has_catalog = "solution_catalog" in parsed

    # --- Restaurant candidates ---
    if cid == "place_1":
        atmo_score = 0.90 if has_catalog else 0.85
        atmo_reason = (
            "Quiet and calm (catalog: quiet_conversation claim)" if has_catalog
            else "Quiet keyword in description"
        )
        return {
            "candidate_id": cid,
            "axis_scores": [
                {"axis": "cuisine", "score": 0.85, "status": "supported",
                 "reason": "Italian", "hard_constraint_violation": False},
                {"axis": "budget", "score": 0.90, "status": "supported",
                 "reason": "Within budget", "hard_constraint_violation": False},
                {"axis": "atmosphere", "score": atmo_score, "status": "supported",
                 "reason": atmo_reason, "hard_constraint_violation": False},
                {"axis": "location", "score": 0.90, "status": "supported",
                 "reason": "In Ebisu", "hard_constraint_violation": False},
                {"axis": "rating", "score": 0.0, "status": "unknown",
                 "reason": "No rating data"},
            ],
            "strengths": ["Quiet Italian"], "weaknesses": [],
            "missing_information": ["Rating"], "risk_notes": [],
            "summary_reason": "Strong match",
        }

    if cid == "place_3":
        loc_score = 0.15 if has_catalog else 0.20
        loc_reason = (
            "Nakameguro (catalog: ebisu_area limitation)" if has_catalog
            else "Nakameguro, not Ebisu"
        )
        return {
            "candidate_id": cid,
            "axis_scores": [
                {"axis": "cuisine", "score": 0.85, "status": "supported",
                 "reason": "Italian", "hard_constraint_violation": False},
                {"axis": "budget", "score": 0.90, "status": "supported",
                 "reason": "Affordable", "hard_constraint_violation": False},
                {"axis": "atmosphere", "score": 0.85, "status": "supported",
                 "reason": "Quiet", "hard_constraint_violation": False},
                {"axis": "location", "score": loc_score, "status": "conflict",
                 "reason": loc_reason, "hard_constraint_violation": True},
                {"axis": "rating", "score": 0.0, "status": "unknown",
                 "reason": "No rating data"},
            ],
            "strengths": ["Quality Italian"], "weaknesses": ["Not in Ebisu"],
            "missing_information": ["Rating"], "risk_notes": [],
            "summary_reason": "Good but wrong location",
        }

    # --- Clinic candidates ---
    if cid == "clinic_1":
        hours_score = 0.92 if has_catalog else 0.85
        hours_reason = (
            "Open until 20:00 (catalog: after_work_visit claim)" if has_catalog
            else "Open until 20:00 weekdays"
        )
        return {
            "candidate_id": cid,
            "axis_scores": [
                {"axis": "specialty_fit", "score": 0.85, "status": "supported",
                 "reason": "Internal medicine", "hard_constraint_violation": False},
                {"axis": "distance", "score": 0.90, "status": "supported",
                 "reason": "Ebisu, 2 min walk", "hard_constraint_violation": False},
                {"axis": "hours", "score": hours_score, "status": "supported",
                 "reason": hours_reason, "hard_constraint_violation": False},
                {"axis": "insurance", "score": 0.90, "status": "supported",
                 "reason": "Insurance accepted", "hard_constraint_violation": False},
                {"axis": "availability", "score": 0.80, "status": "supported",
                 "reason": "Same-day OK", "hard_constraint_violation": False},
            ],
            "strengths": ["Evening hours", "Same-day"], "weaknesses": [],
            "missing_information": [], "risk_notes": ["Verify credentials"],
            "summary_reason": "Strong match for after-work visit",
        }

    if cid == "clinic_2":
        hours_score = 0.35 if has_catalog else 0.40
        hours_reason = (
            "Closes 18:00 (catalog: not_for_after_work limitation)" if has_catalog
            else "Closes at 18:00"
        )
        return {
            "candidate_id": cid,
            "axis_scores": [
                {"axis": "specialty_fit", "score": 0.75, "status": "supported",
                 "reason": "Internal + gastro", "hard_constraint_violation": False},
                {"axis": "distance", "score": 0.45, "status": "supported",
                 "reason": "Meguro, 10 min", "hard_constraint_violation": False},
                {"axis": "hours", "score": hours_score, "status": "conflict",
                 "reason": hours_reason, "hard_constraint_violation": False},
                {"axis": "insurance", "score": 0.90, "status": "supported",
                 "reason": "Insurance accepted", "hard_constraint_violation": False},
                {"axis": "availability", "score": 0.30, "status": "conflict",
                 "reason": "No same-day", "hard_constraint_violation": False},
            ],
            "strengths": ["Gastro specialist"], "weaknesses": ["Short hours"],
            "missing_information": [], "risk_notes": ["Verify credentials"],
            "summary_reason": "Specialist but inconvenient",
        }

    if cid == "clinic_4":
        return {
            "candidate_id": cid,
            "axis_scores": [
                {"axis": "specialty_fit", "score": 0.0, "status": "unknown",
                 "reason": "No info"},
                {"axis": "distance", "score": 0.0, "status": "unknown",
                 "reason": "No address"},
                {"axis": "hours", "score": 0.0, "status": "unknown",
                 "reason": "No hours"},
                {"axis": "insurance", "score": 0.0, "status": "unknown",
                 "reason": "No info"},
                {"axis": "availability", "score": 0.0, "status": "unknown",
                 "reason": "No info"},
            ],
            "strengths": [], "weaknesses": ["No information"],
            "missing_information": ["Everything"], "risk_notes": [],
            "summary_reason": "No data",
        }

    # Default fallback
    return {
        "candidate_id": cid,
        "axis_scores": [
            {"axis": "specialty_fit", "score": 0.50, "status": "supported",
             "reason": "Generic", "hard_constraint_violation": False},
            {"axis": "distance", "score": 0.50, "status": "supported",
             "reason": "OK", "hard_constraint_violation": False},
            {"axis": "hours", "score": 0.50, "status": "supported",
             "reason": "OK", "hard_constraint_violation": False},
            {"axis": "insurance", "score": 0.50, "status": "supported",
             "reason": "OK", "hard_constraint_violation": False},
            {"axis": "availability", "score": 0.50, "status": "supported",
             "reason": "OK", "hard_constraint_violation": False},
        ],
        "strengths": [], "weaknesses": [], "missing_information": [],
        "risk_notes": [], "summary_reason": "Default",
    }


CASES = [
    {"domain": "restaurant", "query": "恵比寿で静かに話せるイタリアン。予算は3000円以内", "request_id": "md-r"},
    {"domain": "clinic", "query": "仕事帰りに行ける内科。保険適用希望", "request_id": "md-c"},
]


# ===================================================================
# A. Output shape
# ===================================================================


class TestOutputShape:
    def test_has_runs_and_summary(self):
        r = run_multi_domain_ablation(CASES, llm_mock_fn=_multi_domain_llm_mock)
        assert "runs" in r
        assert "cross_domain_summary" in r

    def test_two_runs(self):
        r = run_multi_domain_ablation(CASES, llm_mock_fn=_multi_domain_llm_mock)
        assert len(r["runs"]) == 2

    def test_each_run_has_domain_and_diff(self):
        r = run_multi_domain_ablation(CASES, llm_mock_fn=_multi_domain_llm_mock)
        for run in r["runs"]:
            assert "domain" in run
            assert "with_catalog" in run
            assert "without_catalog" in run
            assert "diff_summary" in run

    def test_domains_are_restaurant_and_clinic(self):
        r = run_multi_domain_ablation(CASES, llm_mock_fn=_multi_domain_llm_mock)
        domains = [run["domain"] for run in r["runs"]]
        assert "restaurant" in domains
        assert "clinic" in domains


# ===================================================================
# B. Restaurant backward compat
# ===================================================================


class TestRestaurantAblationCompat:
    def test_restaurant_run_has_ranking(self):
        r = run_multi_domain_ablation(CASES, llm_mock_fn=_multi_domain_llm_mock)
        rest = next(run for run in r["runs"] if run["domain"] == "restaurant")
        assert len(rest["with_catalog"]["ranking"]) >= 1

    def test_restaurant_diff_summary_present(self):
        r = run_multi_domain_ablation(CASES, llm_mock_fn=_multi_domain_llm_mock)
        rest = next(run for run in r["runs"] if run["domain"] == "restaurant")
        d = rest["diff_summary"]
        assert "ranking_changed" in d
        assert "reason_changes" in d


# ===================================================================
# C. Clinic catalog effect
# ===================================================================


class TestClinicCatalogEffect:
    def test_clinic_reason_changes(self):
        r = run_multi_domain_ablation(CASES, llm_mock_fn=_multi_domain_llm_mock)
        clinic = next(run for run in r["runs"] if run["domain"] == "clinic")
        d = clinic["diff_summary"]
        assert len(d["reason_changes"]) > 0

    def test_clinic_score_changes(self):
        r = run_multi_domain_ablation(CASES, llm_mock_fn=_multi_domain_llm_mock)
        clinic = next(run for run in r["runs"] if run["domain"] == "clinic")
        d = clinic["diff_summary"]
        assert len(d["score_changes"]) > 0

    def test_clinic_1_hours_reason_references_catalog(self):
        r = run_multi_domain_ablation(CASES, llm_mock_fn=_multi_domain_llm_mock)
        clinic = next(run for run in r["runs"] if run["domain"] == "clinic")
        assert "clinic_1" in clinic["diff_summary"]["reason_changes"]
        assert "hours" in clinic["diff_summary"]["reason_changes"]["clinic_1"]


# ===================================================================
# D. No overclaim
# ===================================================================


class TestNoOverclaim:
    def test_unknown_not_reduced(self):
        r = run_multi_domain_ablation(CASES, llm_mock_fn=_multi_domain_llm_mock)
        for run in r["runs"]:
            assert run["diff_summary"]["unknown_changes"] == {}

    def test_cross_domain_no_unknown_reduction(self):
        r = run_multi_domain_ablation(CASES, llm_mock_fn=_multi_domain_llm_mock)
        assert r["cross_domain_summary"]["unknown_reduced_domains"] == []


# ===================================================================
# E. Deterministic
# ===================================================================


class TestDeterministic:
    def test_same_input_same_output(self):
        r1 = run_multi_domain_ablation(CASES, llm_mock_fn=_multi_domain_llm_mock)
        r2 = run_multi_domain_ablation(CASES, llm_mock_fn=_multi_domain_llm_mock)
        for i in range(2):
            assert r1["runs"][i]["diff_summary"] == r2["runs"][i]["diff_summary"]
        assert r1["cross_domain_summary"] == r2["cross_domain_summary"]


# ===================================================================
# F. Cross-domain summary
# ===================================================================


class TestCrossDomainSummary:
    def test_both_domains_have_reason_changes(self):
        r = run_multi_domain_ablation(CASES, llm_mock_fn=_multi_domain_llm_mock)
        cs = r["cross_domain_summary"]
        assert "restaurant" in cs["reason_changed_domains"]
        assert "clinic" in cs["reason_changed_domains"]

    def test_both_domains_have_score_changes(self):
        r = run_multi_domain_ablation(CASES, llm_mock_fn=_multi_domain_llm_mock)
        cs = r["cross_domain_summary"]
        assert "restaurant" in cs["score_changed_domains"]
        assert "clinic" in cs["score_changed_domains"]
