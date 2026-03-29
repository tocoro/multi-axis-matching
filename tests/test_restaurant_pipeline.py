"""Tests for restaurant candidate collection pipeline."""

import json
from unittest.mock import patch

import pytest

from src.evaluator import validate_response
from src.normalizers.restaurant_normalizer import (
    _parse_price_text,
    normalize_restaurant,
)
from src.pipeline.restaurant_pipeline import run_restaurant_pipeline
from src.searchers.place_searcher import search_places
from src.services.infer_search_conditions import infer_search_conditions
from src.mock import MOCK_AXES


# ===================================================================
# A. query understanding
# ===================================================================


class TestInferSearchConditions:
    def test_full_extraction(self):
        c = infer_search_conditions("恵比寿で静かに話せるイタリアン。予算は3000円以内")
        assert c["location"] == "恵比寿"
        assert c["genre"] == "italian"
        assert c["max_price"] == 3000
        assert c["atmosphere"] == "quiet"

    def test_location_only(self):
        c = infer_search_conditions("渋谷で何か食べたい")
        assert c["location"] == "渋谷"
        assert "genre" not in c

    def test_genre_french(self):
        c = infer_search_conditions("フレンチレストランに行きたい")
        assert c["genre"] == "french"

    def test_price_with_comma(self):
        c = infer_search_conditions("予算は10,000円以内")
        assert c["max_price"] == 10000

    def test_atmosphere_casual(self):
        c = infer_search_conditions("カジュアルな店がいい")
        assert c["atmosphere"] == "casual"

    def test_empty_query(self):
        c = infer_search_conditions("おすすめある？")
        assert "location" not in c
        assert "genre" not in c
        assert "max_price" not in c


# ===================================================================
# B. normalize
# ===================================================================


class TestParsePrice:
    def test_range(self):
        assert _parse_price_text("￥2,000〜￥3,000") == (2000, 3000)

    def test_single(self):
        assert _parse_price_text("￥3,000") == (None, 3000)

    def test_none(self):
        assert _parse_price_text(None) == (None, None)

    def test_empty(self):
        assert _parse_price_text("") == (None, None)


class TestNormalizeRestaurant:
    def test_full_record(self):
        retrieved = {
            "source": "place_search",
            "source_id": "place_1",
            "raw_record": {
                "name": "Trattoria A",
                "address": "東京都渋谷区恵比寿南1-2-3",
                "nearest_station": "恵比寿",
                "price_text": "￥2,000〜￥3,000",
                "category": "イタリアン",
                "atmosphere_text": "静かで落ち着いた雰囲気",
                "review_summary": "会話しやすい",
            },
        }
        c = normalize_restaurant(retrieved)
        assert c["candidate_id"] == "place_1"
        assert c["title"] == "Trattoria A"
        attrs = c["structured_attributes"]
        assert attrs["genre"] == "italian"
        assert attrs["nearest_station"] == "恵比寿"
        assert attrs["price_min"] == 2000
        assert attrs["price_max"] == 3000
        assert "quiet" in attrs["atmosphere_tags"]

    def test_genre_normalization(self):
        retrieved = {
            "source": "place_search",
            "source_id": "p",
            "raw_record": {"name": "X", "category": "バー"},
        }
        c = normalize_restaurant(retrieved)
        assert c["structured_attributes"]["genre"] == "bar"

    def test_missing_fields_not_filled(self):
        retrieved = {
            "source": "place_search",
            "source_id": "place_4",
            "raw_record": {
                "name": "Restaurant D",
                "address": None,
                "nearest_station": None,
                "price_text": None,
                "category": None,
                "atmosphere_text": "落ち着いた雰囲気",
                "review_summary": None,
            },
        }
        c = normalize_restaurant(retrieved)
        attrs = c["structured_attributes"]
        assert "genre" not in attrs
        assert "nearest_station" not in attrs
        assert "price_min" not in attrs
        assert "quiet" in attrs["atmosphere_tags"]

    def test_description_generated(self):
        retrieved = {
            "source": "place_search",
            "source_id": "p",
            "raw_record": {
                "name": "Test",
                "nearest_station": "渋谷",
                "category": "カフェ",
                "price_text": "￥1,000〜￥2,000",
            },
        }
        c = normalize_restaurant(retrieved)
        assert "渋谷" in c["description"]
        assert "Test" in c["description"]


# ===================================================================
# C. search filtering + diagnostics
# ===================================================================


def _search_ids(conditions, **kwargs):
    """Helper: return just source_ids from search."""
    output = search_places(conditions, **kwargs)
    return [r["source_id"] for r in output["results"]]


def _search_diag(conditions, **kwargs):
    """Helper: return search_diagnostics."""
    return search_places(conditions, **kwargs)["search_diagnostics"]


class TestSearchFiltering:
    def test_genre_and_location_match(self):
        ids = _search_ids({"genre": "italian", "location": "恵比寿"})
        assert "place_1" in ids
        assert "place_3" in ids
        assert "place_2" not in ids
        assert "place_4" not in ids

    def test_genre_filters_out_mismatch(self):
        ids = _search_ids({"genre": "italian"})
        assert "place_2" not in ids

    def test_location_filters_distant(self):
        ids = _search_ids({"location": "恵比寿"})
        assert "place_1" in ids
        assert "place_2" in ids
        assert "place_3" in ids
        assert "place_4" not in ids

    def test_location_neighbor_included(self):
        ids = _search_ids({"genre": "italian", "location": "恵比寿"})
        assert "place_3" in ids

    def test_fallback_on_no_match(self):
        output = search_places({"genre": "sushi", "location": "六本木"})
        assert len(output["results"]) == 4

    def test_fallback_genre_only(self):
        ids = _search_ids({"genre": "italian", "location": "六本木"})
        assert "place_1" in ids
        assert "place_3" in ids
        assert "place_2" not in ids

    def test_no_conditions_returns_all(self):
        output = search_places({})
        assert len(output["results"]) == 4

    def test_budget_soft_sort(self):
        output = search_places({"max_price": 2000})
        assert len(output["results"]) == 4

    def test_deterministic(self):
        c = {"genre": "italian", "location": "恵比寿", "max_price": 3000}
        r1 = search_places(c)
        r2 = search_places(c)
        assert ([x["source_id"] for x in r1["results"]]
                == [x["source_id"] for x in r2["results"]])
        assert r1["search_diagnostics"] == r2["search_diagnostics"]


# ===================================================================
# C-2. search diagnostics
# ===================================================================


class TestSearchDiagnostics:
    def test_strict_hit_no_fallback(self):
        """恵比寿 + italian → strict hit。"""
        d = _search_diag({"genre": "italian", "location": "恵比寿"})
        assert d["fallback_applied"] is False
        assert d["fallback_enabled"] is True
        assert d["matched_stage"] == "genre+location"
        assert d["strict_result_count"] == 2
        assert d["final_result_count"] == 2
        assert d["fallback_steps"] == []

    def test_fallback_rescue_diagnostics(self):
        """sushi + 六本木 → 全件 fallback。"""
        d = _search_diag({"genre": "sushi", "location": "六本木"})
        assert d["fallback_applied"] is True
        assert d["matched_stage"] == "all"
        assert d["strict_result_count"] == 0
        assert d["final_result_count"] == 4
        assert "genre+location" in d["fallback_steps"]

    def test_fallback_to_genre_only(self):
        """italian + 六本木 → genre_only fallback。"""
        d = _search_diag({"genre": "italian", "location": "六本木"})
        assert d["fallback_applied"] is True
        assert d["matched_stage"] == "genre_only"
        assert d["strict_result_count"] == 0
        assert d["final_result_count"] == 2

    def test_strict_conditions_recorded(self):
        d = _search_diag({"genre": "italian", "location": "恵比寿", "max_price": 3000})
        assert d["strict_conditions"] == {
            "genre": "italian", "location": "恵比寿", "max_price": 3000,
        }


# ===================================================================
# C-3. strict mode (enable_fallback=False)
# ===================================================================


class TestStrictMode:
    def test_strict_zero_results(self):
        """sushi + 六本木 strict → 0 件。"""
        output = search_places(
            {"genre": "sushi", "location": "六本木"}, enable_fallback=False)
        assert output["results"] == []
        d = output["search_diagnostics"]
        assert d["fallback_enabled"] is False
        assert d["fallback_applied"] is False
        assert d["matched_stage"] == "strict_only"
        assert d["strict_result_count"] == 0
        assert d["final_result_count"] == 0

    def test_strict_hit_returns_results(self):
        """恵比寿 + italian strict → 2 件 (strict で十分ヒット)。"""
        output = search_places(
            {"genre": "italian", "location": "恵比寿"}, enable_fallback=False)
        assert len(output["results"]) == 2
        d = output["search_diagnostics"]
        assert d["fallback_enabled"] is False
        assert d["fallback_applied"] is False
        assert d["matched_stage"] == "genre+location"

    def test_strict_vs_fallback_same_conditions(self):
        """同一条件で strict 0件 / fallback 4件。"""
        cond = {"genre": "sushi", "location": "六本木"}
        strict = search_places(cond, enable_fallback=False)
        fallback = search_places(cond, enable_fallback=True)
        assert len(strict["results"]) == 0
        assert len(fallback["results"]) == 4


# ===================================================================
# D. pipeline E2E (mock LLM) — filtered search
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

    evals = {
        "place_1": {
            "axis_scores": [
                {"axis": "cuisine", "score": 0.85, "status": "supported",
                 "reason": "Italian", "hard_constraint_violation": False},
                {"axis": "budget", "score": 0.9, "status": "supported",
                 "reason": "2500 avg within 3000", "hard_constraint_violation": False},
                {"axis": "atmosphere", "score": 0.85, "status": "supported",
                 "reason": "Quiet and calm", "hard_constraint_violation": False},
                {"axis": "location", "score": 0.9, "status": "supported",
                 "reason": "In Ebisu", "hard_constraint_violation": False},
                {"axis": "rating", "score": 0.7, "status": "supported",
                 "reason": "Good reviews", "hard_constraint_violation": False},
            ],
            "strengths": ["Quiet Italian in Ebisu"],
            "weaknesses": [],
            "missing_information": [],
            "risk_notes": [],
            "summary_reason": "Strong match",
        },
        "place_3": {
            "axis_scores": [
                {"axis": "cuisine", "score": 0.8, "status": "supported",
                 "reason": "Italian", "hard_constraint_violation": False},
                {"axis": "budget", "score": 0.9, "status": "supported",
                 "reason": "2000 avg within 3000", "hard_constraint_violation": False},
                {"axis": "atmosphere", "score": 0.8, "status": "supported",
                 "reason": "Quiet hideaway", "hard_constraint_violation": False},
                {"axis": "location", "score": 0.2, "status": "conflict",
                 "reason": "Nakameguro, not Ebisu",
                 "hard_constraint_violation": False},
                {"axis": "rating", "score": 0.75, "status": "supported",
                 "reason": "High quality food", "hard_constraint_violation": False},
            ],
            "strengths": ["Quality Italian", "Quiet"],
            "weaknesses": ["Not in Ebisu"],
            "missing_information": [],
            "risk_notes": [],
            "summary_reason": "Good but wrong location",
        },
        "place_4": {
            "axis_scores": [
                {"axis": "cuisine", "score": 0.0, "status": "unknown",
                 "reason": "No cuisine info"},
                {"axis": "budget", "score": 0.0, "status": "unknown",
                 "reason": "No price info"},
                {"axis": "atmosphere", "score": 0.6, "status": "supported",
                 "reason": "Seems calm", "hard_constraint_violation": False},
                {"axis": "location", "score": 0.0, "status": "unknown",
                 "reason": "No address"},
                {"axis": "rating", "score": 0.0, "status": "unknown",
                 "reason": "No reviews"},
            ],
            "strengths": ["Might have calm atmosphere"],
            "weaknesses": ["Very little info"],
            "missing_information": ["Cuisine type", "Price range", "Address", "Reviews"],
            "risk_notes": ["Insufficient data"],
            "summary_reason": "Only atmosphere evaluable",
        },
    }
    # default for unknown candidates
    data = evals.get(cid, {
        "axis_scores": [
            {"axis": "cuisine", "score": 0.5, "status": "supported",
             "reason": "Generic", "hard_constraint_violation": False},
            {"axis": "budget", "score": 0.7, "status": "supported",
             "reason": "OK", "hard_constraint_violation": False},
            {"axis": "atmosphere", "score": 0.5, "status": "supported",
             "reason": "Average", "hard_constraint_violation": False},
            {"axis": "location", "score": 0.5, "status": "supported",
             "reason": "OK", "hard_constraint_violation": False},
            {"axis": "rating", "score": 0.5, "status": "supported",
             "reason": "Average", "hard_constraint_violation": False},
        ],
        "strengths": [], "weaknesses": [], "missing_information": [],
        "risk_notes": [], "summary_reason": "Default mock",
    })
    return {"candidate_id": cid, **data}


class TestPipelineE2E:
    QUERY = "恵比寿で静かに話せるイタリアン。予算は3000円以内"

    @patch("src.evaluator.call_llm", side_effect=_pipeline_llm_mock)
    def test_response_is_schema_valid(self, _mock):
        r = run_restaurant_pipeline("pipe-1", self.QUERY)
        validate_response(r)

    @patch("src.evaluator.call_llm", side_effect=_pipeline_llm_mock)
    def test_search_filters_to_two_candidates(self, _mock):
        r = run_restaurant_pipeline("pipe-1", self.QUERY)
        assert len(r["ranking"]) == 2
        ids = {e["candidate_id"] for e in r["ranking"]}
        assert ids == {"place_1", "place_3"}

    @patch("src.evaluator.call_llm", side_effect=_pipeline_llm_mock)
    def test_ranks_sequential(self, _mock):
        r = run_restaurant_pipeline("pipe-1", self.QUERY)
        assert [e["rank"] for e in r["ranking"]] == [1, 2]

    @patch("src.evaluator.call_llm", side_effect=_pipeline_llm_mock)
    def test_place_1_ranked_first(self, _mock):
        r = run_restaurant_pipeline("pipe-1", self.QUERY)
        assert r["ranking"][0]["candidate_id"] == "place_1"

    @patch("src.evaluator.call_llm", side_effect=_pipeline_llm_mock)
    def test_bar_excluded_by_search(self, _mock):
        r = run_restaurant_pipeline("pipe-1", self.QUERY)
        ids = {e["candidate_id"] for e in r["ranking"]}
        assert "place_2" not in ids

    @patch("src.evaluator.call_llm", side_effect=_pipeline_llm_mock)
    def test_neither_disqualified(self, _mock):
        r = run_restaurant_pipeline("pipe-1", self.QUERY)
        for entry in r["ranking"]:
            assert entry["disqualified"] is False

    @patch("src.evaluator.call_llm", side_effect=_pipeline_llm_mock)
    def test_diagnostics_in_response(self, _mock):
        """search_diagnostics が response に含まれる。"""
        r = run_restaurant_pipeline("pipe-1", self.QUERY)
        d = r["search_diagnostics"]
        assert d["fallback_applied"] is False
        assert d["matched_stage"] == "genre+location"
        assert d["strict_result_count"] == 2


class TestPipelineFallback:
    @patch("src.evaluator.call_llm", side_effect=_pipeline_llm_mock)
    def test_no_match_returns_all_candidates(self, _mock):
        r = run_restaurant_pipeline("pipe-fb", "六本木で寿司が食べたい。予算は5000円")
        assert len(r["ranking"]) == 4

    @patch("src.evaluator.call_llm", side_effect=_pipeline_llm_mock)
    def test_fallback_still_valid_response(self, _mock):
        r = run_restaurant_pipeline("pipe-fb", "六本木で寿司が食べたい。予算は5000円")
        validate_response(r)

    @patch("src.evaluator.call_llm", side_effect=_pipeline_llm_mock)
    def test_fallback_diagnostics_in_response(self, _mock):
        r = run_restaurant_pipeline("pipe-fb", "六本木で寿司が食べたい。予算は5000円")
        d = r["search_diagnostics"]
        assert d["fallback_applied"] is True
        assert d["matched_stage"] == "all"

    @patch("src.evaluator.call_llm", side_effect=_pipeline_llm_mock)
    def test_fallback_includes_info_lacking(self, _mock):
        r = run_restaurant_pipeline("pipe-fb", "六本木で寿司が食べたい。予算は5000円")
        p4 = next(e for e in r["ranking"] if e["candidate_id"] == "place_4")
        assert len(p4["missing_information"]) >= 3
        assert p4["confidence"] < 0.5
        assert p4["disqualified"] is False


class TestPipelineStrict:
    @patch("src.evaluator.call_llm", side_effect=_pipeline_llm_mock)
    def test_strict_zero_results(self, _mock):
        """strict で 0 件 → 空 ranking。"""
        r = run_restaurant_pipeline(
            "pipe-strict", "六本木で寿司が食べたい",
            enable_fallback=False)
        assert r["ranking"] == []
        assert r["search_diagnostics"]["fallback_enabled"] is False
        assert r["search_diagnostics"]["final_result_count"] == 0

    @patch("src.evaluator.call_llm", side_effect=_pipeline_llm_mock)
    def test_strict_with_hits(self, _mock):
        """strict でもヒットすれば通常通り evaluate。"""
        r = run_restaurant_pipeline(
            "pipe-strict", "恵比寿で静かに話せるイタリアン。予算は3000円以内",
            enable_fallback=False)
        assert len(r["ranking"]) == 2
        assert r["search_diagnostics"]["fallback_enabled"] is False
        assert r["search_diagnostics"]["fallback_applied"] is False
