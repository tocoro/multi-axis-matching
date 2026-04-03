"""Prompt contract tests: evaluator prompt にスコア帯域ガイドが含まれていることを検証。"""

from pathlib import Path

PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "evaluate_candidate.txt"


def _load_prompt() -> str:
    return PROMPT_PATH.read_text(encoding="utf-8")


class TestScoreGradientGuide:
    def test_contains_gradient_bands(self):
        p = _load_prompt()
        assert "0.80〜0.95" in p
        assert "0.45〜0.75" in p
        assert "0.20〜0.40" in p
        assert "0.05〜0.25" in p

    def test_discourages_extreme_values(self):
        p = _load_prompt()
        assert "極端値 0.0 / 1.0 を多用しない" in p

    def test_unknown_not_low_score(self):
        p = _load_prompt()
        assert "情報が無いのに score=0.0 を付けない" in p
        assert "unknown は不一致ではない" in p

    def test_partial_match_guidance(self):
        p = _load_prompt()
        assert "部分一致" in p
        assert "中間値" in p

    def test_axis_examples_present(self):
        p = _load_prompt()
        assert "atmosphere" in p
        assert "budget" in p
        assert "location" in p
        assert "genre" in p

    def test_reason_guidance(self):
        p = _load_prompt()
        assert "二値断定" in p
        assert "部分的に合致" in p

    def test_hard_constraint_rules_preserved(self):
        p = _load_prompt()
        assert "hard_constraint_violation" in p
        assert "hard_constraints に対する明示的違反" in p

    def test_status_rules_preserved(self):
        p = _load_prompt()
        assert "supported" in p
        assert "unknown" in p
        assert "conflict" in p
