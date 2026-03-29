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
        # 不明は含めない
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
        """不明な情報は埋めない。"""
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
        assert "price_max" not in attrs
        assert "review_summary" not in attrs
        # atmosphere は推定可能
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
# C & D. pipeline E2E (mock LLM)
# ===================================================================


def _pipeline_llm_mock(system_prompt: str, user_message: str) -> dict:
    """Pipeline E2E 用の LLM mock。"""
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
        return {
            "axes": MOCK_AXES,
            "reason": "Restaurant axes",
        }
    # evaluate_candidate — candidate_id に応じて返す
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
        "place_2": {
            "axis_scores": [
                {"axis": "cuisine", "score": 0.3, "status": "conflict",
                 "reason": "Bar, not Italian", "hard_constraint_violation": False},
                {"axis": "budget", "score": 0.95, "status": "supported",
                 "reason": "Very affordable", "hard_constraint_violation": False},
                {"axis": "atmosphere", "score": 0.2, "status": "conflict",
                 "reason": "Lively, user wants quiet",
                 "hard_constraint_violation": False},
                {"axis": "location", "score": 0.8, "status": "supported",
                 "reason": "In Ebisu", "hard_constraint_violation": False},
                {"axis": "rating", "score": 0.5, "status": "supported",
                 "reason": "Average", "hard_constraint_violation": False},
            ],
            "strengths": ["Affordable"],
            "weaknesses": ["Not Italian", "Noisy"],
            "missing_information": [],
            "risk_notes": [],
            "summary_reason": "Poor genre and atmosphere match",
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
    data = evals.get(cid, evals["place_4"])
    return {"candidate_id": cid, **data}


class TestPipelineE2E:
    """query → search → retrieve → normalize → evaluate が通ること。"""

    @patch("src.evaluator.call_llm", side_effect=_pipeline_llm_mock)
    def test_response_is_schema_valid(self, _mock):
        r = run_restaurant_pipeline("pipe-1", "恵比寿で静かに話せるイタリアン。予算は3000円以内")
        validate_response(r)

    @patch("src.evaluator.call_llm", side_effect=_pipeline_llm_mock)
    def test_ranking_has_four_candidates(self, _mock):
        r = run_restaurant_pipeline("pipe-1", "恵比寿で静かに話せるイタリアン。予算は3000円以内")
        assert len(r["ranking"]) == 4

    @patch("src.evaluator.call_llm", side_effect=_pipeline_llm_mock)
    def test_ranks_sequential(self, _mock):
        r = run_restaurant_pipeline("pipe-1", "恵比寿で静かに話せるイタリアン。予算は3000円以内")
        ranks = [e["rank"] for e in r["ranking"]]
        assert ranks == [1, 2, 3, 4]

    @patch("src.evaluator.call_llm", side_effect=_pipeline_llm_mock)
    def test_at_least_one_not_disqualified(self, _mock):
        r = run_restaurant_pipeline("pipe-1", "恵比寿で静かに話せるイタリアン。予算は3000円以内")
        assert any(not e["disqualified"] for e in r["ranking"])

    @patch("src.evaluator.call_llm", side_effect=_pipeline_llm_mock)
    def test_place_1_ranked_first(self, _mock):
        """条件に最も合う place_1 が1位。"""
        r = run_restaurant_pipeline("pipe-1", "恵比寿で静かに話せるイタリアン。予算は3000円以内")
        first = r["ranking"][0]
        assert first["candidate_id"] == "place_1"

    @patch("src.evaluator.call_llm", side_effect=_pipeline_llm_mock)
    def test_place_2_ranked_below_place_1(self, _mock):
        """place_2 (bar, noisy) は place_1 より下位。"""
        r = run_restaurant_pipeline("pipe-1", "恵比寿で静かに話せるイタリアン。予算は3000円以内")
        p1 = next(e for e in r["ranking"] if e["candidate_id"] == "place_1")
        p2 = next(e for e in r["ranking"] if e["candidate_id"] == "place_2")
        assert p1["rank"] < p2["rank"]


class TestPipelineInfoLacking:
    """情報欠落候補が missing_information に反映されること。"""

    @patch("src.evaluator.call_llm", side_effect=_pipeline_llm_mock)
    def test_place_4_has_missing_information(self, _mock):
        r = run_restaurant_pipeline("pipe-1", "恵比寿で静かに話せるイタリアン。予算は3000円以内")
        p4 = next(e for e in r["ranking"] if e["candidate_id"] == "place_4")
        assert len(p4["missing_information"]) >= 3

    @patch("src.evaluator.call_llm", side_effect=_pipeline_llm_mock)
    def test_place_4_low_confidence(self, _mock):
        r = run_restaurant_pipeline("pipe-1", "恵比寿で静かに話せるイタリアン。予算は3000円以内")
        p4 = next(e for e in r["ranking"] if e["candidate_id"] == "place_4")
        assert p4["confidence"] < 0.5

    @patch("src.evaluator.call_llm", side_effect=_pipeline_llm_mock)
    def test_global_missing_info_includes_place_4_items(self, _mock):
        r = run_restaurant_pipeline("pipe-1", "恵比寿で静かに話せるイタリアン。予算は3000円以内")
        assert "global_missing_information" in r
        assert any("Address" in m or "Price" in m
                    for m in r["global_missing_information"])

    @patch("src.evaluator.call_llm", side_effect=_pipeline_llm_mock)
    def test_place_4_not_disqualified(self, _mock):
        """情報欠落は失格にしない。"""
        r = run_restaurant_pipeline("pipe-1", "恵比寿で静かに話せるイタリアン。予算は3000円以内")
        p4 = next(e for e in r["ranking"] if e["candidate_id"] == "place_4")
        assert p4["disqualified"] is False
