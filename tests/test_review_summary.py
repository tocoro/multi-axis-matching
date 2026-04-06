"""Review summary builder tests."""

import json

import pytest

from src.experiments.review_summary import (
    build_cross_domain_review_summary,
    build_review_summary,
    format_review_summary_text,
)
from src.experiments.catalog_ablation import run_ablation
from src.experiments.multi_domain_catalog_ablation import run_multi_domain_ablation
from src.mock import MOCK_AXES
from tests.test_solution_catalog_ablation import _ablation_llm_mock
from tests.test_multi_domain_catalog_ablation import _multi_domain_llm_mock, CASES


# ===================================================================
# A. Single-domain review_summary structure
# ===================================================================


class TestReviewSummaryStructure:
    def test_has_all_keys(self):
        r = run_ablation("rs-1", "恵比寿で静かに話せるイタリアン", llm_mock_fn=_ablation_llm_mock)
        rs = r["review_summary"]
        assert "ranking" in rs
        assert "score" in rs
        assert "confidence" in rs
        assert "reason" in rs
        assert "unknown" in rs
        assert "disqualified" in rs

    def test_ranking_unchanged(self):
        r = run_ablation("rs-2", "恵比寿で静かに話せるイタリアン", llm_mock_fn=_ablation_llm_mock)
        assert r["review_summary"]["ranking"]["changed"] is False
        assert r["review_summary"]["ranking"]["note"] == "ranking unchanged"

    def test_unknown_unchanged(self):
        r = run_ablation("rs-3", "恵比寿で静かに話せるイタリアン", llm_mock_fn=_ablation_llm_mock)
        assert r["review_summary"]["unknown"]["unchanged"] is True
        assert "resolve" in r["review_summary"]["unknown"]["note"]

    def test_score_delta_sign(self):
        r = run_ablation("rs-4", "恵比寿で静かに話せるイタリアン。予算は3000円以内", llm_mock_fn=_ablation_llm_mock)
        scores = r["review_summary"]["score"]["changed_candidates"]
        p1 = next((s for s in scores if s["candidate_id"] == "place_1"), None)
        if p1:
            assert p1["delta"] > 0  # catalog improves atmosphere

    def test_reason_changes_match_diff(self):
        r = run_ablation("rs-5", "恵比寿で静かに話せるイタリアン。予算は3000円以内", llm_mock_fn=_ablation_llm_mock)
        diff_reasons = set(r["diff_summary"]["reason_changes"].keys())
        review_reasons = {c["candidate_id"] for c in r["review_summary"]["reason"]["changed_candidates"]}
        assert review_reasons == diff_reasons

    def test_disqualified_unchanged(self):
        r = run_ablation("rs-6", "恵比寿で静かに話せるイタリアン。予算は3000円以内", llm_mock_fn=_ablation_llm_mock)
        assert r["review_summary"]["disqualified"]["changed_candidates"] == []

    def test_catalog_reference_detected(self):
        r = run_ablation("rs-7", "恵比寿で静かに話せるイタリアン。予算は3000円以内", llm_mock_fn=_ablation_llm_mock)
        reasons = r["review_summary"]["reason"]["changed_candidates"]
        p1 = next((c for c in reasons if c["candidate_id"] == "place_1"), None)
        if p1:
            assert p1["catalog_reference_added"] is True


# ===================================================================
# B. Multi-domain review summary
# ===================================================================


class TestMultiDomainReviewSummary:
    def test_has_cross_domain_review(self):
        r = run_multi_domain_ablation(CASES, llm_mock_fn=_multi_domain_llm_mock)
        assert "cross_domain_review_summary" in r

    def test_both_domains_in_reason_changed(self):
        r = run_multi_domain_ablation(CASES, llm_mock_fn=_multi_domain_llm_mock)
        cs = r["cross_domain_review_summary"]
        assert "restaurant" in cs["reason_changed_domains"]
        assert "clinic" in cs["reason_changed_domains"]

    def test_unknown_reduced_empty(self):
        r = run_multi_domain_ablation(CASES, llm_mock_fn=_multi_domain_llm_mock)
        cs = r["cross_domain_review_summary"]
        assert cs["unknown_reduced_domains"] == []

    def test_interpretation_notes_present(self):
        r = run_multi_domain_ablation(CASES, llm_mock_fn=_multi_domain_llm_mock)
        cs = r["cross_domain_review_summary"]
        assert len(cs["interpretation_notes"]) >= 2

    def test_each_run_has_review_summary(self):
        r = run_multi_domain_ablation(CASES, llm_mock_fn=_multi_domain_llm_mock)
        for run in r["runs"]:
            assert "review_summary" in run


# ===================================================================
# C. Text formatting
# ===================================================================


class TestTextFormatting:
    def test_format_produces_text(self):
        r = run_ablation("fmt-1", "テスト", llm_mock_fn=_ablation_llm_mock)
        text = format_review_summary_text(r["review_summary"], query="テスト", model="mock")
        assert "Review Summary" in text
        assert "テスト" in text
        assert "Ranking" in text
        assert "Unknown" in text

    def test_format_shows_unchanged(self):
        r = run_ablation("fmt-2", "テスト", llm_mock_fn=_ablation_llm_mock)
        text = format_review_summary_text(r["review_summary"])
        assert "unchanged" in text.lower()
