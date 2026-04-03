"""Solution Catalog integration tests."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from src.catalog.loader import get_catalog_entry, load_solution_catalog
from src.evaluator import validate_response
from src.mock import MOCK_AXES
from src.pipeline.restaurant_pipeline import run_restaurant_pipeline

ROOT = Path(__file__).resolve().parent.parent
CATALOG_PATH = ROOT / "examples" / "restaurant_solution_catalog.json"


# ===================================================================
# A. Catalog loader / lookup
# ===================================================================


class TestCatalogLoader:
    def test_load_default(self):
        catalog = load_solution_catalog()
        assert len(catalog) == 4
        assert "place_1" in catalog

    def test_load_explicit_path(self):
        catalog = load_solution_catalog(CATALOG_PATH)
        assert "place_1" in catalog

    def test_load_nonexistent_returns_empty(self):
        catalog = load_solution_catalog("/nonexistent/path.json")
        assert catalog == {}

    def test_get_entry_found(self):
        catalog = load_solution_catalog()
        entry = get_catalog_entry(catalog, "place_1")
        assert entry is not None
        assert entry["candidate_id"] == "place_1"
        assert "solution_claims" in entry

    def test_get_entry_not_found(self):
        catalog = load_solution_catalog()
        assert get_catalog_entry(catalog, "nonexistent") is None


# ===================================================================
# B. Pipeline attaches catalog
# ===================================================================


def _pipeline_llm_mock(system_prompt: str, user_message: str) -> dict:
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
    return {
        "candidate_id": cid,
        "axis_scores": [
            {"axis": "cuisine", "score": 0.85, "status": "supported",
             "reason": "Italian", "hard_constraint_violation": False},
            {"axis": "budget", "score": 0.9, "status": "supported",
             "reason": "OK", "hard_constraint_violation": False},
            {"axis": "atmosphere", "score": 0.8, "status": "supported",
             "reason": "Quiet", "hard_constraint_violation": False},
            {"axis": "location", "score": 0.7, "status": "supported",
             "reason": "Nearby", "hard_constraint_violation": False},
            {"axis": "rating", "score": 0.6, "status": "supported",
             "reason": "Average", "hard_constraint_violation": False},
        ],
        "strengths": [], "weaknesses": [], "missing_information": [],
        "risk_notes": [], "summary_reason": "OK",
    }


class TestPipelineCatalogAttachment:
    QUERY = "恵比寿で静かに話せるイタリアン。予算は3000円以内"

    @patch("src.evaluator.call_llm", side_effect=_pipeline_llm_mock)
    def test_candidates_have_catalog(self, _mock):
        r = run_restaurant_pipeline("cat-1", self.QUERY)
        src = r["candidate_sources"]
        # place_1 は catalog に存在 → solution_catalog が付く
        assert "solution_catalog" in src["place_1"]
        claims = src["place_1"]["solution_catalog"]["solution_claims"]
        assert any(c["problem_pattern"] == "quiet_conversation" for c in claims)

    @patch("src.evaluator.call_llm", side_effect=_pipeline_llm_mock)
    def test_pipeline_still_valid_response(self, _mock):
        r = run_restaurant_pipeline("cat-1", self.QUERY)
        validate_response(r)

    @patch("src.evaluator.call_llm", side_effect=_pipeline_llm_mock)
    def test_pipeline_without_catalog(self, _mock):
        """catalog が無いパスでも落ちない。"""
        r = run_restaurant_pipeline(
            "cat-none", self.QUERY,
            catalog_path="/nonexistent/path.json",
        )
        validate_response(r)
        assert len(r["ranking"]) == 2
        # catalog 未添付
        src = r["candidate_sources"]
        assert "solution_catalog" not in src.get("place_1", {})


# ===================================================================
# C. Evaluator receives catalog in user_message
# ===================================================================


class TestEvaluatorCatalogContext:
    @patch("src.evaluator.call_llm", side_effect=_pipeline_llm_mock)
    def test_catalog_in_llm_user_message(self, mock_llm):
        """catalog があるとき user_message に solution_catalog が含まれる。"""
        run_restaurant_pipeline("cat-ctx", "恵比寿で静かに話せるイタリアン。予算は3000円以内")

        # evaluate_candidate の呼び出しを探す
        for call in mock_llm.call_args_list:
            system_prompt = call[0][0]
            user_message = call[0][1]
            if "候補を評価" in system_prompt:
                msg = json.loads(user_message)
                if "solution_catalog" in msg:
                    assert "solution_claims" in msg["solution_catalog"]
                    return
        pytest.fail("No evaluate call with solution_catalog found")

    @patch("src.evaluator.call_llm", side_effect=_pipeline_llm_mock)
    def test_no_catalog_still_works(self, mock_llm):
        """catalog なしでも evaluate は正常動作。"""
        r = run_restaurant_pipeline(
            "cat-none", "恵比寿で静かに話せるイタリアン",
            catalog_path="/nonexistent/path.json",
        )
        assert len(r["ranking"]) == 2


# ===================================================================
# D. Backward compatibility
# ===================================================================


class TestBackwardCompat:
    @patch("src.evaluator.call_llm", side_effect=_pipeline_llm_mock)
    def test_existing_mock_pipeline_works(self, _mock):
        r = run_restaurant_pipeline("compat-1", "恵比寿で静かに話せるイタリアン。予算は3000円以内")
        assert len(r["ranking"]) == 2
        assert r["ranking"][0]["rank"] == 1

    @patch("src.evaluator.call_llm", side_effect=_pipeline_llm_mock)
    def test_diagnostics_preserved(self, _mock):
        r = run_restaurant_pipeline("compat-1", "恵比寿で静かに話せるイタリアン。予算は3000円以内")
        assert "search_diagnostics" in r


# ===================================================================
# E. Prototype correction: no unknown as limitation
# ===================================================================


class TestNoUnknownAsLimitation:
    def test_no_late_night_limitation(self):
        """不明 (営業時間不明) は limitation にしない修正が反映されている。"""
        catalog = load_solution_catalog()
        place_1 = catalog["place_1"]
        patterns = [l["problem_pattern"] for l in place_1["hard_limitations"]]
        assert "late_night_dining" not in patterns

    def test_all_limitations_have_evidence_based_reasons(self):
        """全 limitation の reason が情報不足ではなく明確な根拠に基づく。"""
        catalog = load_solution_catalog()
        for entry in catalog.values():
            for lim in entry["hard_limitations"]:
                assert "不明" not in lim["reason"]
                assert "情報がな" not in lim["reason"]
