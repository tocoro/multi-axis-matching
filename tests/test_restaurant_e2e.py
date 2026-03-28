"""End-to-end tests using the restaurant example."""

import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from src.evaluator import evaluate, validate_response
from src.mock import mock_restaurant_dispatch

ROOT = Path(__file__).resolve().parent.parent
EXAMPLE_PATH = ROOT / "examples" / "restaurant.json"
EXPECTED_PATH = ROOT / "examples" / "restaurant.expected.json"
SCRIPT_PATH = ROOT / "scripts" / "run_restaurant_example.py"


def _run_mock_evaluate() -> dict:
    request = json.loads(EXAMPLE_PATH.read_text(encoding="utf-8"))
    with patch("src.evaluator.call_llm", side_effect=mock_restaurant_dispatch):
        return evaluate(request)


# ---------------------------------------------------------------------------
# Schema & structure
# ---------------------------------------------------------------------------


class TestRestaurantMockEvaluate:
    def test_response_passes_schema_validation(self):
        response = _run_mock_evaluate()
        validate_response(response)

    def test_ranking_has_two_entries(self):
        response = _run_mock_evaluate()
        assert len(response["ranking"]) == 2

    def test_ranks_are_sequential(self):
        response = _run_mock_evaluate()
        ranks = [e["rank"] for e in response["ranking"]]
        assert ranks == [1, 2]

    def test_at_least_one_not_disqualified(self):
        response = _run_mock_evaluate()
        assert any(not e["disqualified"] for e in response["ranking"])

    def test_r1_ranked_above_r2(self):
        """r1 (quiet Italian) should outscore r2 (noisy bar)."""
        response = _run_mock_evaluate()
        r1 = next(e for e in response["ranking"] if e["candidate_id"] == "r1")
        r2 = next(e for e in response["ranking"] if e["candidate_id"] == "r2")
        assert r1["rank"] < r2["rank"]
        assert r1["total_score"] > r2["total_score"]

    def test_r2_atmosphere_is_conflict_but_not_disqualified(self):
        """r2 has atmosphere conflict (soft preference) → not disqualified."""
        response = _run_mock_evaluate()
        r2 = next(e for e in response["ranking"] if e["candidate_id"] == "r2")
        atm = next(a for a in r2["axis_scores"] if a["axis"] == "atmosphere")
        assert atm["status"] == "conflict"
        assert atm["hard_constraint_violation"] is False
        assert r2["disqualified"] is False

    def test_problem_type_is_local_restaurant(self):
        response = _run_mock_evaluate()
        assert response["inferred_problem_type"] == "local.restaurant"

    def test_needs_human_review_false(self):
        response = _run_mock_evaluate()
        assert response["needs_human_review"] is False


# ---------------------------------------------------------------------------
# Deterministic output
# ---------------------------------------------------------------------------


class TestDeterministicOutput:
    def test_mock_output_matches_expected_json(self):
        response = _run_mock_evaluate()
        expected = json.loads(EXPECTED_PATH.read_text(encoding="utf-8"))
        assert response == expected

    def test_mock_is_idempotent(self):
        """Two consecutive runs produce identical output."""
        r1 = _run_mock_evaluate()
        r2 = _run_mock_evaluate()
        assert r1 == r2


# ---------------------------------------------------------------------------
# Script execution
# ---------------------------------------------------------------------------


class TestScriptExecution:
    def test_mock_mode_exits_zero(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPT_PATH), "--mock"],
            capture_output=True, text=True, timeout=30,
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"

    def test_mock_mode_outputs_valid_json(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPT_PATH), "--mock"],
            capture_output=True, text=True, timeout=30,
        )
        response = json.loads(result.stdout)
        validate_response(response)
        assert len(response["ranking"]) == 2

    def test_mock_mode_with_info_logging(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPT_PATH), "--mock", "--log-level", "INFO"],
            capture_output=True, text=True, timeout=30,
        )
        assert result.returncode == 0
        # Logs go to stderr, JSON to stdout
        assert "Evaluation started" in result.stderr
        json.loads(result.stdout)  # stdout is still valid JSON
