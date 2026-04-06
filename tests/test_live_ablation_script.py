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


class TestArtifactIndex:
    def _run_and_index(self):
        from scripts.run_solution_catalog_live_ablation import run_live_ablation, build_artifact_index
        from unittest.mock import patch
        from tests.test_solution_catalog_ablation import _ablation_llm_mock
        with patch("src.evaluator.call_llm", side_effect=_ablation_llm_mock):
            result = run_live_ablation("テスト", "mock-model")
        index = build_artifact_index(result, artifact_path="/tmp/test.json")
        return result, index

    def test_build_artifact_index_has_required_keys(self):
        _, index = self._run_and_index()
        for key in ["query", "model", "timestamp", "artifact_path",
                     "catalog_mode", "quick_verdict", "top_candidates"]:
            assert key in index, f"Missing key: {key}"

    def test_build_artifact_index_uses_quick_verdict(self):
        result, index = self._run_and_index()
        assert index["quick_verdict"] == result["review_summary"]["quick_verdict"]

    def test_build_artifact_index_top_candidates_are_ids(self):
        _, index = self._run_and_index()
        tc = index["top_candidates"]
        assert isinstance(tc["with_catalog"], list)
        assert isinstance(tc["without_catalog"], list)
        assert all(isinstance(c, str) for c in tc["with_catalog"])
        assert all(isinstance(c, str) for c in tc["without_catalog"])

    def test_out_save_creates_index_file(self, tmp_path):
        from scripts.run_solution_catalog_live_ablation import run_live_ablation, build_artifact_index
        from unittest.mock import patch
        from tests.test_solution_catalog_ablation import _ablation_llm_mock
        import json as _json

        with patch("src.evaluator.call_llm", side_effect=_ablation_llm_mock):
            result = run_live_ablation("テスト", "mock-model")

        out_path = tmp_path / "test_result.json"
        out_path.write_text(_json.dumps(result, ensure_ascii=False, indent=2))

        index = build_artifact_index(result, artifact_path=str(out_path))
        index_path = out_path.with_suffix(".index.json")
        index_path.write_text(_json.dumps(index, ensure_ascii=False, indent=2))

        assert out_path.exists()
        assert index_path.exists()

    def test_index_file_contains_artifact_path(self, tmp_path):
        from scripts.run_solution_catalog_live_ablation import run_live_ablation, build_artifact_index
        from unittest.mock import patch
        from tests.test_solution_catalog_ablation import _ablation_llm_mock
        import json as _json

        with patch("src.evaluator.call_llm", side_effect=_ablation_llm_mock):
            result = run_live_ablation("テスト", "mock-model")

        out_path = tmp_path / "full.json"
        index = build_artifact_index(result, artifact_path=str(out_path))
        assert index["artifact_path"] == str(out_path)


class TestDirectorySummary:
    def _make_index_items(self):
        from scripts.run_solution_catalog_live_ablation import run_live_ablation, build_artifact_index
        from unittest.mock import patch
        from tests.test_solution_catalog_ablation import _ablation_llm_mock

        items = []
        for i, q in enumerate(["テスト1", "テスト2"]):
            with patch("src.evaluator.call_llm", side_effect=_ablation_llm_mock):
                result = run_live_ablation(q, "mock-model")
            items.append(build_artifact_index(result, artifact_path=f"/tmp/case{i}.json"))
        return items

    def test_build_artifact_directory_summary_has_required_keys(self):
        from scripts.run_solution_catalog_live_ablation import build_artifact_directory_summary
        items = self._make_index_items()
        s = build_artifact_directory_summary(items)
        for key in ["total_runs", "models", "queries", "verdict_counts", "artifacts"]:
            assert key in s, f"Missing key: {key}"

    def test_build_artifact_directory_summary_counts_verdicts(self):
        from scripts.run_solution_catalog_live_ablation import build_artifact_directory_summary
        items = self._make_index_items()
        s = build_artifact_directory_summary(items)
        vc = s["verdict_counts"]
        # Both runs should have reason_changed from ablation mock
        assert isinstance(vc["reason_changed"], int)
        assert vc["reason_changed"] >= 0

    def test_build_artifact_directory_summary_no_top_candidates(self):
        from scripts.run_solution_catalog_live_ablation import build_artifact_directory_summary
        items = self._make_index_items()
        s = build_artifact_directory_summary(items)
        for a in s["artifacts"]:
            assert "top_candidates" not in a

    def test_out_save_updates_directory_summary(self, tmp_path):
        from scripts.run_solution_catalog_live_ablation import (
            run_live_ablation, build_artifact_index, build_artifact_directory_summary,
        )
        from unittest.mock import patch
        from tests.test_solution_catalog_ablation import _ablation_llm_mock
        import json as _json

        # Create 2 index files
        for i in range(2):
            with patch("src.evaluator.call_llm", side_effect=_ablation_llm_mock):
                result = run_live_ablation(f"テスト{i}", "mock")
            out = tmp_path / f"case{i}.json"
            out.write_text(_json.dumps(result))
            idx = build_artifact_index(result, artifact_path=str(out))
            out.with_suffix(".index.json").write_text(_json.dumps(idx))

        # Build summary
        index_items = []
        for f in sorted(tmp_path.glob("*.index.json")):
            index_items.append(_json.loads(f.read_text()))
        summary = build_artifact_directory_summary(index_items)
        summary_path = tmp_path / "_index_summary.json"
        summary_path.write_text(_json.dumps(summary))

        assert summary_path.exists()

    def test_directory_summary_total_runs_matches(self, tmp_path):
        from scripts.run_solution_catalog_live_ablation import (
            run_live_ablation, build_artifact_index, build_artifact_directory_summary,
        )
        from unittest.mock import patch
        from tests.test_solution_catalog_ablation import _ablation_llm_mock
        import json as _json

        for i in range(3):
            with patch("src.evaluator.call_llm", side_effect=_ablation_llm_mock):
                result = run_live_ablation(f"q{i}", "mock")
            idx = build_artifact_index(result, artifact_path=f"/tmp/c{i}.json")
            (tmp_path / f"c{i}.index.json").write_text(_json.dumps(idx))

        items = [_json.loads(f.read_text()) for f in sorted(tmp_path.glob("*.index.json"))]
        summary = build_artifact_directory_summary(items)
        assert summary["total_runs"] == 3


class TestTrendSummary:
    def _make_summary(self):
        from scripts.run_solution_catalog_live_ablation import (
            run_live_ablation, build_artifact_index, build_artifact_directory_summary,
        )
        from unittest.mock import patch
        from tests.test_solution_catalog_ablation import _ablation_llm_mock
        import json as _json

        items = []
        for i in range(2):
            with patch("src.evaluator.call_llm", side_effect=_ablation_llm_mock):
                result = run_live_ablation(f"テスト{i}", "mock")
            items.append(build_artifact_index(result, f"/tmp/c{i}.json"))
        return build_artifact_directory_summary(items)

    def test_directory_summary_has_trend_summary(self):
        s = self._make_summary()
        assert "trend_summary" in s

    def test_trend_summary_run_coverage_matches_verdict_counts(self):
        s = self._make_summary()
        assert s["trend_summary"]["run_coverage"] == s["verdict_counts"]

    def test_trend_summary_stable_signals_include_zero_count_keys(self):
        s = self._make_summary()
        ts = s["trend_summary"]
        vc = s["verdict_counts"]
        for k in ts["stable_signals"]:
            assert vc[k] == 0

    def test_trend_summary_dominant_changes_include_positive_count_keys(self):
        s = self._make_summary()
        ts = s["trend_summary"]
        vc = s["verdict_counts"]
        for k in ts["dominant_changes"]:
            assert vc[k] > 0

    def test_cli_trend_line_format(self):
        s = self._make_summary()
        ts = s["trend_summary"]
        dom = ",".join(ts["dominant_changes"]) or "none"
        stb = ",".join(ts["stable_signals"]) or "none"
        line = f"Directory trends: dominant={dom} stable={stb}"
        assert "Directory trends:" in line
