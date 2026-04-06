"""Live ablation script structure tests. No actual API calls."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "run_solution_catalog_live_ablation.py"


class TestScriptArgParsing:
    def test_requires_query(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPT)],
            capture_output=True, text=True, timeout=10,
        )
        assert result.returncode != 0
        assert "required" in result.stderr.lower() or "error" in result.stderr.lower()

    def test_help_flag(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--help"],
            capture_output=True, text=True, timeout=10,
        )
        assert result.returncode == 0
        assert "--query" in result.stdout
        assert "--model" in result.stdout
        assert "--out" in result.stdout


class TestOutputTemplate:
    def test_result_has_required_keys(self):
        """run_live_ablation の戻り値構造を検証 (mock import)。"""
        from src.experiments.catalog_ablation import run_ablation
        from tests.test_solution_catalog_ablation import _ablation_llm_mock

        result = run_ablation("tpl-1", "テスト", llm_mock_fn=_ablation_llm_mock)
        assert "query" in result
        assert "with_catalog" in result
        assert "without_catalog" in result
        assert "diff_summary" in result
        d = result["diff_summary"]
        assert "ranking_changed" in d
        assert "score_changes" in d
        assert "confidence_changes" in d
        assert "unknown_changes" in d
        assert "reason_changes" in d


class TestRunMetadata:
    def _run_live_ablation_mock(self):
        """Mock で run_live_ablation 相当を呼ぶ。"""
        # live script の関数を直接使わず、同等構造を検証
        from scripts.run_solution_catalog_live_ablation import run_live_ablation
        from unittest.mock import patch
        from tests.test_solution_catalog_ablation import _ablation_llm_mock
        with patch("src.evaluator.call_llm", side_effect=_ablation_llm_mock):
            return run_live_ablation("テスト", "mock-model")

    def test_result_has_run_metadata(self):
        result = self._run_live_ablation_mock()
        assert "run_metadata" in result

    def test_run_metadata_has_required_keys(self):
        result = self._run_live_ablation_mock()
        m = result["run_metadata"]
        assert "query" in m
        assert "model" in m
        assert "timestamp" in m
        assert "catalog_mode" in m
        assert "candidate_source" in m
        assert "is_live_llm" in m
        assert "review_summary_version" in m

    def test_run_metadata_catalog_mode_fixed(self):
        result = self._run_live_ablation_mock()
        assert result["run_metadata"]["catalog_mode"] == "with_vs_without"
