"""Restaurant boundary-condition tests (Cases 1-5).

動的軸選択・多軸評価の安定性と境界条件を確認する。
全ケース共通で同じ query / problem_type / constraints / axes を使い、
候補ごとの評価結果だけを差し替えることでロジックの正しさを検証する。
"""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from src.evaluator import evaluate, validate_response
from src.mock import MOCK_AXES

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"


# ---------------------------------------------------------------------------
# Shared mock infrastructure
# ---------------------------------------------------------------------------

_COMMON_TYPE = {
    "inferred_problem_type": "local.restaurant",
    "confidence": 0.92,
    "reason": "Restaurant query with area, genre, budget",
}

_COMMON_CONSTRAINTS = {
    "hard_constraints": {"budget_max": 3000},
    "soft_preferences": {"atmosphere": "quiet"},
    "notes": [],
}

_COMMON_AXES_RESULT = {
    "axes": MOCK_AXES,
    "reason": "Restaurant: cuisine, budget, atmosphere, location, rating",
}


def _make_dispatcher(candidate_evals: dict):
    """Build a mock call_llm dispatcher with case-specific candidate evals."""

    def dispatch(system_prompt: str, user_message: str) -> dict:
        if "前処理" in system_prompt:
            return _COMMON_TYPE
        if "制約を抽出" in system_prompt:
            return _COMMON_CONSTRAINTS
        if "評価軸選択" in system_prompt:
            return _COMMON_AXES_RESULT
        # evaluate_candidate
        parsed = json.loads(user_message)
        cid = parsed["candidate"]["candidate_id"]
        data = candidate_evals[cid]
        return {"candidate_id": cid, **data}

    return dispatch


def _load_case(n: int) -> dict:
    return json.loads((EXAMPLES / f"restaurant_case_{n}.json").read_text("utf-8"))


def _run_case(n: int, evals: dict) -> dict:
    request = _load_case(n)
    with patch("src.evaluator.call_llm", side_effect=_make_dispatcher(evals)):
        return evaluate(request)


def _entry(response: dict, cid: str) -> dict:
    return next(e for e in response["ranking"] if e["candidate_id"] == cid)


# ===================================================================
# Case 1: 静かだが高い — hard constraint violation で失格
# ===================================================================

_CASE1_EVALS = {
    "c1_good": {
        "axis_scores": [
            {"axis": "cuisine", "score": 0.85, "status": "supported",
             "reason": "Italian", "hard_constraint_violation": False},
            {"axis": "budget", "score": 0.9, "status": "supported",
             "reason": "2500 within 3000", "hard_constraint_violation": False},
            {"axis": "atmosphere", "score": 0.9, "status": "supported",
             "reason": "Quiet and calm", "hard_constraint_violation": False},
            {"axis": "location", "score": 0.0, "status": "unknown",
             "reason": "No address detail"},
            {"axis": "rating", "score": 0.7, "status": "supported",
             "reason": "Decent", "hard_constraint_violation": False},
        ],
        "strengths": ["Quiet", "Within budget"],
        "weaknesses": [],
        "missing_information": ["Exact address"],
        "risk_notes": [],
        "summary_reason": "Good all-round match",
    },
    "c1_expensive": {
        "axis_scores": [
            {"axis": "cuisine", "score": 0.95, "status": "supported",
             "reason": "Fine Italian", "hard_constraint_violation": False},
            {"axis": "budget", "score": 0.0, "status": "conflict",
             "reason": "4500 yen exceeds 3000 max",
             "hard_constraint_violation": True},
            {"axis": "atmosphere", "score": 0.95, "status": "supported",
             "reason": "Very quiet and elegant", "hard_constraint_violation": False},
            {"axis": "location", "score": 0.0, "status": "unknown",
             "reason": "No address detail"},
            {"axis": "rating", "score": 0.85, "status": "supported",
             "reason": "Highly rated", "hard_constraint_violation": False},
        ],
        "strengths": ["Excellent cuisine", "Outstanding atmosphere"],
        "weaknesses": ["Over budget"],
        "missing_information": ["Exact address"],
        "risk_notes": [],
        "summary_reason": "High quality but exceeds hard budget constraint",
    },
}


class TestCase1QuietButExpensive:
    """高スコアでも予算超過 (hard constraint) なら失格になる。"""

    def test_schema_valid(self):
        r = _run_case(1, _CASE1_EVALS)
        validate_response(r)

    def test_ranks_sequential(self):
        r = _run_case(1, _CASE1_EVALS)
        assert [e["rank"] for e in r["ranking"]] == [1, 2]

    def test_expensive_is_disqualified(self):
        r = _run_case(1, _CASE1_EVALS)
        exp = _entry(r, "c1_expensive")
        assert exp["disqualified"] is True
        assert any("budget" in reason for reason in exp["disqualification_reasons"])

    def test_good_is_not_disqualified(self):
        r = _run_case(1, _CASE1_EVALS)
        good = _entry(r, "c1_good")
        assert good["disqualified"] is False

    def test_good_ranked_above_expensive(self):
        r = _run_case(1, _CASE1_EVALS)
        assert _entry(r, "c1_good")["rank"] < _entry(r, "c1_expensive")["rank"]

    def test_expensive_has_higher_raw_axes_but_still_loses(self):
        """c1_expensive の supported 軸平均は高いが失格で最下位。"""
        r = _run_case(1, _CASE1_EVALS)
        exp = _entry(r, "c1_expensive")
        good = _entry(r, "c1_good")
        # expensive の cuisine + atmosphere は good より高い
        exp_cuisine = next(a for a in exp["axis_scores"] if a["axis"] == "cuisine")
        good_cuisine = next(a for a in good["axis_scores"] if a["axis"] == "cuisine")
        assert exp_cuisine["score"] > good_cuisine["score"]
        # でも失格
        assert exp["rank"] > good["rank"]


# ===================================================================
# Case 2: 安いが遠い — location conflict だが失格にならない
# ===================================================================

_CASE2_EVALS = {
    "c2_local": {
        "axis_scores": [
            {"axis": "cuisine", "score": 0.7, "status": "supported",
             "reason": "Italian", "hard_constraint_violation": False},
            {"axis": "budget", "score": 0.8, "status": "supported",
             "reason": "2800 within 3000", "hard_constraint_violation": False},
            {"axis": "atmosphere", "score": 0.6, "status": "supported",
             "reason": "Calm", "hard_constraint_violation": False},
            {"axis": "location", "score": 0.8, "status": "supported",
             "reason": "3 min from Ebisu station", "hard_constraint_violation": False},
            {"axis": "rating", "score": 0.5, "status": "supported",
             "reason": "Average", "hard_constraint_violation": False},
        ],
        "strengths": ["Close to Ebisu station"],
        "weaknesses": [],
        "missing_information": [],
        "risk_notes": [],
        "summary_reason": "Solid local option",
    },
    "c2_far": {
        "axis_scores": [
            {"axis": "cuisine", "score": 0.8, "status": "supported",
             "reason": "Italian", "hard_constraint_violation": False},
            {"axis": "budget", "score": 0.95, "status": "supported",
             "reason": "1500 yen, very affordable", "hard_constraint_violation": False},
            {"axis": "atmosphere", "score": 0.75, "status": "supported",
             "reason": "Quiet", "hard_constraint_violation": False},
            {"axis": "location", "score": 0.2, "status": "conflict",
             "reason": "Nakameguro, not Ebisu as requested",
             "hard_constraint_violation": False},
            {"axis": "rating", "score": 0.6, "status": "supported",
             "reason": "Good reviews", "hard_constraint_violation": False},
        ],
        "strengths": ["Very affordable", "Good food"],
        "weaknesses": ["Not in Ebisu"],
        "missing_information": [],
        "risk_notes": [],
        "summary_reason": "Great value but location mismatch",
    },
}


class TestCase2CheapButFar:
    """立地 conflict は soft → 失格にならず、トレードオフが順位に反映される。"""

    def test_schema_valid(self):
        r = _run_case(2, _CASE2_EVALS)
        validate_response(r)

    def test_neither_disqualified(self):
        r = _run_case(2, _CASE2_EVALS)
        for entry in r["ranking"]:
            assert entry["disqualified"] is False

    def test_far_location_is_conflict_not_hard(self):
        r = _run_case(2, _CASE2_EVALS)
        far = _entry(r, "c2_far")
        loc = next(a for a in far["axis_scores"] if a["axis"] == "location")
        assert loc["status"] == "conflict"
        assert loc["hard_constraint_violation"] is False

    def test_local_ranked_above_far(self):
        r = _run_case(2, _CASE2_EVALS)
        assert _entry(r, "c2_local")["rank"] < _entry(r, "c2_far")["rank"]

    def test_far_has_lower_total_despite_better_budget(self):
        """c2_far は budget で勝つが location で負けてトータルは下。"""
        r = _run_case(2, _CASE2_EVALS)
        local = _entry(r, "c2_local")
        far = _entry(r, "c2_far")
        assert far["total_score"] < local["total_score"]

    def test_both_full_confidence(self):
        """全軸 supported (conflict 含む) → confidence 1.0。"""
        r = _run_case(2, _CASE2_EVALS)
        for entry in r["ranking"]:
            assert entry["confidence"] == pytest.approx(1.0)


# ===================================================================
# Case 3: 静かで安いがジャンル不一致 — cuisine conflict で順位低下
# ===================================================================

_CASE3_EVALS = {
    "c3_italian": {
        "axis_scores": [
            {"axis": "cuisine", "score": 0.85, "status": "supported",
             "reason": "Casual Italian", "hard_constraint_violation": False},
            {"axis": "budget", "score": 0.85, "status": "supported",
             "reason": "2500 within 3000", "hard_constraint_violation": False},
            {"axis": "atmosphere", "score": 0.6, "status": "supported",
             "reason": "Casual, not especially quiet",
             "hard_constraint_violation": False},
            {"axis": "location", "score": 0.0, "status": "unknown",
             "reason": "No address detail"},
            {"axis": "rating", "score": 0.5, "status": "supported",
             "reason": "Average", "hard_constraint_violation": False},
        ],
        "strengths": ["Italian cuisine matches", "Within budget"],
        "weaknesses": ["Atmosphere not outstanding"],
        "missing_information": ["Exact address"],
        "risk_notes": [],
        "summary_reason": "Solid Italian option, casual atmosphere",
    },
    "c3_bistro": {
        "axis_scores": [
            {"axis": "cuisine", "score": 0.2, "status": "conflict",
             "reason": "French bistro, not Italian as requested",
             "hard_constraint_violation": False},
            {"axis": "budget", "score": 0.9, "status": "supported",
             "reason": "2000, well within 3000", "hard_constraint_violation": False},
            {"axis": "atmosphere", "score": 0.9, "status": "supported",
             "reason": "Very quiet", "hard_constraint_violation": False},
            {"axis": "location", "score": 0.0, "status": "unknown",
             "reason": "No address detail"},
            {"axis": "rating", "score": 0.65, "status": "supported",
             "reason": "Good reviews", "hard_constraint_violation": False},
        ],
        "strengths": ["Very quiet", "Affordable"],
        "weaknesses": ["Not Italian"],
        "missing_information": ["Exact address"],
        "risk_notes": [],
        "summary_reason": "Excellent atmosphere and price, but wrong cuisine",
    },
}


class TestCase3WrongCuisine:
    """ジャンル不一致は conflict だが hard violation ではない → 失格にならず順位低下。"""

    def test_schema_valid(self):
        r = _run_case(3, _CASE3_EVALS)
        validate_response(r)

    def test_neither_disqualified(self):
        r = _run_case(3, _CASE3_EVALS)
        for entry in r["ranking"]:
            assert entry["disqualified"] is False

    def test_bistro_cuisine_is_conflict_not_hard(self):
        r = _run_case(3, _CASE3_EVALS)
        bistro = _entry(r, "c3_bistro")
        cuis = next(a for a in bistro["axis_scores"] if a["axis"] == "cuisine")
        assert cuis["status"] == "conflict"
        assert cuis["hard_constraint_violation"] is False

    def test_italian_ranked_above_bistro(self):
        r = _run_case(3, _CASE3_EVALS)
        assert _entry(r, "c3_italian")["rank"] < _entry(r, "c3_bistro")["rank"]

    def test_bistro_atmosphere_higher_but_total_lower(self):
        """bistro は雰囲気で勝つがジャンルで大きく落ちてトータル負け。"""
        r = _run_case(3, _CASE3_EVALS)
        italian = _entry(r, "c3_italian")
        bistro = _entry(r, "c3_bistro")
        it_atm = next(a for a in italian["axis_scores"] if a["axis"] == "atmosphere")
        bi_atm = next(a for a in bistro["axis_scores"] if a["axis"] == "atmosphere")
        assert bi_atm["score"] > it_atm["score"]
        assert bistro["total_score"] < italian["total_score"]

    def test_both_have_same_confidence(self):
        """両方とも location が unknown → 同じ confidence。"""
        r = _run_case(3, _CASE3_EVALS)
        assert (_entry(r, "c3_italian")["confidence"]
                == _entry(r, "c3_bistro")["confidence"])


# ===================================================================
# Case 4: 情報欠落が多い — unknown が confidence に効く
# ===================================================================

_CASE4_EVALS = {
    "c4_known": {
        "axis_scores": [
            {"axis": "cuisine", "score": 0.8, "status": "supported",
             "reason": "Italian", "hard_constraint_violation": False},
            {"axis": "budget", "score": 0.85, "status": "supported",
             "reason": "2500 within 3000", "hard_constraint_violation": False},
            {"axis": "atmosphere", "score": 0.75, "status": "supported",
             "reason": "Calm interior", "hard_constraint_violation": False},
            {"axis": "location", "score": 0.7, "status": "supported",
             "reason": "In Ebisu area", "hard_constraint_violation": False},
            {"axis": "rating", "score": 0.6, "status": "supported",
             "reason": "Tabelog 3.5", "hard_constraint_violation": False},
        ],
        "strengths": ["Full information available", "All axes supported"],
        "weaknesses": [],
        "missing_information": [],
        "risk_notes": [],
        "summary_reason": "Well-documented, solid match",
    },
    "c4_vague": {
        "axis_scores": [
            {"axis": "cuisine", "score": 0.0, "status": "unknown",
             "reason": "No cuisine information"},
            {"axis": "budget", "score": 0.0, "status": "unknown",
             "reason": "No price information"},
            {"axis": "atmosphere", "score": 0.6, "status": "supported",
             "reason": "Described as calm atmosphere",
             "hard_constraint_violation": False},
            {"axis": "location", "score": 0.0, "status": "unknown",
             "reason": "No address"},
            {"axis": "rating", "score": 0.0, "status": "unknown",
             "reason": "No rating data"},
        ],
        "strengths": ["Seems to have calm atmosphere"],
        "weaknesses": ["Very little information available"],
        "missing_information": [
            "Cuisine type",
            "Price range",
            "Address",
            "Rating / reviews",
        ],
        "risk_notes": ["Insufficient data to evaluate most axes"],
        "summary_reason": "Only atmosphere is evaluable; critical info missing",
    },
}


class TestCase4InformationLacking:
    """unknown が複数 → confidence 低下、missing_information に反映。"""

    def test_schema_valid(self):
        r = _run_case(4, _CASE4_EVALS)
        validate_response(r)

    def test_known_ranked_above_vague(self):
        r = _run_case(4, _CASE4_EVALS)
        assert _entry(r, "c4_known")["rank"] < _entry(r, "c4_vague")["rank"]

    def test_neither_disqualified(self):
        """unknown は失格にしない。"""
        r = _run_case(4, _CASE4_EVALS)
        for entry in r["ranking"]:
            assert entry["disqualified"] is False

    def test_vague_has_much_lower_confidence(self):
        r = _run_case(4, _CASE4_EVALS)
        known = _entry(r, "c4_known")
        vague = _entry(r, "c4_vague")
        assert known["confidence"] == pytest.approx(1.0)
        # vague: only atmosphere(0.2) out of total(1.0) → 0.2
        assert vague["confidence"] == pytest.approx(0.2)
        assert vague["confidence"] < known["confidence"]

    def test_unknown_excluded_from_score_not_penalized(self):
        """vague の total_score は atmosphere だけで計算 → 0.6 (低くはない)。"""
        r = _run_case(4, _CASE4_EVALS)
        vague = _entry(r, "c4_vague")
        assert vague["total_score"] == pytest.approx(0.6, abs=1e-3)

    def test_vague_has_multiple_missing_information(self):
        r = _run_case(4, _CASE4_EVALS)
        vague = _entry(r, "c4_vague")
        assert len(vague["missing_information"]) >= 3

    def test_global_missing_information_populated(self):
        r = _run_case(4, _CASE4_EVALS)
        assert "global_missing_information" in r
        assert len(r["global_missing_information"]) >= 3

    def test_vague_unknown_count(self):
        """vague は 5 軸中 4 軸が unknown。"""
        r = _run_case(4, _CASE4_EVALS)
        vague = _entry(r, "c4_vague")
        unknowns = [a for a in vague["axis_scores"] if a["status"] == "unknown"]
        assert len(unknowns) == 4


# ===================================================================
# Case 5: すべてそこそこ — 3 候補の相対順位
# ===================================================================

_CASE5_EVALS = {
    "c5_strong": {
        "axis_scores": [
            {"axis": "cuisine", "score": 0.9, "status": "supported",
             "reason": "Popular Italian", "hard_constraint_violation": False},
            {"axis": "budget", "score": 0.85, "status": "supported",
             "reason": "2500 within 3000", "hard_constraint_violation": False},
            {"axis": "atmosphere", "score": 0.85, "status": "supported",
             "reason": "Quiet and calm", "hard_constraint_violation": False},
            {"axis": "location", "score": 0.0, "status": "unknown",
             "reason": "General Ebisu area, no exact address"},
            {"axis": "rating", "score": 0.75, "status": "supported",
             "reason": "Tabelog 3.8", "hard_constraint_violation": False},
        ],
        "strengths": ["High ratings", "Quiet atmosphere", "Good cuisine"],
        "weaknesses": [],
        "missing_information": ["Exact address"],
        "risk_notes": [],
        "summary_reason": "Strong match on all evaluable axes",
    },
    "c5_mid": {
        "axis_scores": [
            {"axis": "cuisine", "score": 0.7, "status": "supported",
             "reason": "Italian", "hard_constraint_violation": False},
            {"axis": "budget", "score": 0.75, "status": "supported",
             "reason": "2800, within 3000 but tight",
             "hard_constraint_violation": False},
            {"axis": "atmosphere", "score": 0.6, "status": "supported",
             "reason": "Average atmosphere", "hard_constraint_violation": False},
            {"axis": "location", "score": 0.5, "status": "supported",
             "reason": "In Ebisu", "hard_constraint_violation": False},
            {"axis": "rating", "score": 0.55, "status": "supported",
             "reason": "No notable reviews", "hard_constraint_violation": False},
        ],
        "strengths": ["Meets all basic criteria"],
        "weaknesses": ["Nothing stands out"],
        "missing_information": [],
        "risk_notes": [],
        "summary_reason": "Adequate on all axes, no standout quality",
    },
    "c5_weak": {
        "axis_scores": [
            {"axis": "cuisine", "score": 0.4, "status": "supported",
             "reason": "Bar, not specifically Italian",
             "hard_constraint_violation": False},
            {"axis": "budget", "score": 0.9, "status": "supported",
             "reason": "2000, well within budget",
             "hard_constraint_violation": False},
            {"axis": "atmosphere", "score": 0.3, "status": "conflict",
             "reason": "Lively/noisy, user wants quiet",
             "hard_constraint_violation": False},
            {"axis": "location", "score": 0.0, "status": "unknown",
             "reason": "No exact address"},
            {"axis": "rating", "score": 0.4, "status": "supported",
             "reason": "Average", "hard_constraint_violation": False},
        ],
        "strengths": ["Very affordable"],
        "weaknesses": ["Noisy", "Not clearly Italian"],
        "missing_information": ["Exact address"],
        "risk_notes": [],
        "summary_reason": "Cheap but poor cuisine and atmosphere match",
    },
}


class TestCase5AllMediocre:
    """3 候補の相対順位が正しく出ること。conflict は低スコアとして反映。"""

    def test_schema_valid(self):
        r = _run_case(5, _CASE5_EVALS)
        validate_response(r)

    def test_ranks_sequential(self):
        r = _run_case(5, _CASE5_EVALS)
        assert [e["rank"] for e in r["ranking"]] == [1, 2, 3]

    def test_none_disqualified(self):
        r = _run_case(5, _CASE5_EVALS)
        for entry in r["ranking"]:
            assert entry["disqualified"] is False

    def test_ranking_order(self):
        r = _run_case(5, _CASE5_EVALS)
        assert _entry(r, "c5_strong")["rank"] == 1
        assert _entry(r, "c5_mid")["rank"] == 2
        assert _entry(r, "c5_weak")["rank"] == 3

    def test_scores_descending(self):
        r = _run_case(5, _CASE5_EVALS)
        scores = [e["total_score"] for e in r["ranking"]]
        assert scores == sorted(scores, reverse=True)

    def test_mid_has_full_confidence(self):
        """c5_mid は全軸 supported → confidence 1.0。"""
        r = _run_case(5, _CASE5_EVALS)
        mid = _entry(r, "c5_mid")
        assert mid["confidence"] == pytest.approx(1.0)

    def test_strong_and_weak_have_lower_confidence(self):
        """c5_strong と c5_weak は location unknown → confidence < 1.0。"""
        r = _run_case(5, _CASE5_EVALS)
        mid = _entry(r, "c5_mid")
        strong = _entry(r, "c5_strong")
        weak = _entry(r, "c5_weak")
        assert strong["confidence"] < mid["confidence"]
        assert weak["confidence"] < mid["confidence"]

    def test_weak_atmosphere_is_conflict(self):
        r = _run_case(5, _CASE5_EVALS)
        weak = _entry(r, "c5_weak")
        atm = next(a for a in weak["axis_scores"] if a["axis"] == "atmosphere")
        assert atm["status"] == "conflict"
        assert atm["hard_constraint_violation"] is False

    def test_mid_total_score_is_moderate(self):
        """c5_mid は 0.55-0.75 の範囲に収まる中程度スコア。"""
        r = _run_case(5, _CASE5_EVALS)
        mid = _entry(r, "c5_mid")
        assert 0.55 < mid["total_score"] < 0.75
