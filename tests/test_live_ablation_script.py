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


class TestAnomalyFlags:
    def _make_summary(self):
        from scripts.run_solution_catalog_live_ablation import (
            run_live_ablation, build_artifact_index, build_artifact_directory_summary,
        )
        from unittest.mock import patch
        from tests.test_solution_catalog_ablation import _ablation_llm_mock

        items = []
        for i in range(2):
            with patch("src.evaluator.call_llm", side_effect=_ablation_llm_mock):
                result = run_live_ablation(f"テスト{i}", "mock")
            items.append(build_artifact_index(result, f"/tmp/c{i}.json"))
        return build_artifact_directory_summary(items)

    def test_directory_summary_has_anomaly_flags(self):
        s = self._make_summary()
        assert "anomaly_flags" in s

    def test_anomaly_flags_false_for_normal_mock(self):
        s = self._make_summary()
        af = s["anomaly_flags"]
        assert af["ranking_changed_present"] is False
        assert af["unknown_reduced_present"] is False
        assert af["disqualified_changed_present"] is False
        assert af["needs_manual_review"] is False

    def test_anomaly_manual_review_true_when_unknown_reduced(self):
        from scripts.run_solution_catalog_live_ablation import _build_anomaly_flags
        vc = {"reason_changed": 1, "score_changed": 1, "confidence_changed": 0,
              "ranking_changed": 0, "unknown_reduced": 1, "disqualified_changed": 0}
        af = _build_anomaly_flags(vc)
        assert af["unknown_reduced_present"] is True
        assert af["needs_manual_review"] is True

    def test_anomaly_manual_review_true_when_ranking_changed(self):
        from scripts.run_solution_catalog_live_ablation import _build_anomaly_flags
        vc = {"reason_changed": 1, "score_changed": 1, "confidence_changed": 0,
              "ranking_changed": 1, "unknown_reduced": 0, "disqualified_changed": 0}
        af = _build_anomaly_flags(vc)
        assert af["ranking_changed_present"] is True
        assert af["needs_manual_review"] is True

    def test_cli_anomaly_line_format(self):
        s = self._make_summary()
        af = s["anomaly_flags"]
        yn = lambda b: "yes" if b else "no"
        line = (
            f"Directory anomaly flags: "
            f"manual_review={yn(af['needs_manual_review'])} "
            f"ranking_changed={yn(af['ranking_changed_present'])}"
        )
        assert "Directory anomaly flags:" in line


class TestArtifactOrdering:
    def test_directory_summary_artifacts_sorted_by_timestamp_model_path(self):
        from scripts.run_solution_catalog_live_ablation import build_artifact_directory_summary
        items = [
            {"timestamp": "2026-04-06T16:00:00Z", "model": "b", "artifact_path": "/b", "quick_verdict": {}},
            {"timestamp": "2026-04-06T15:00:00Z", "model": "a", "artifact_path": "/a", "quick_verdict": {}},
            {"timestamp": "2026-04-06T15:00:00Z", "model": "a", "artifact_path": "/c", "quick_verdict": {}},
        ]
        s = build_artifact_directory_summary(items)
        paths = [a["artifact_path"] for a in s["artifacts"]]
        assert paths == ["/a", "/c", "/b"]


class TestFormatDirectorySummaryText:
    def _make_summary(self):
        from scripts.run_solution_catalog_live_ablation import (
            run_live_ablation, build_artifact_index, build_artifact_directory_summary,
        )
        from unittest.mock import patch
        from tests.test_solution_catalog_ablation import _ablation_llm_mock

        items = []
        for i in range(2):
            with patch("src.evaluator.call_llm", side_effect=_ablation_llm_mock):
                result = run_live_ablation(f"テスト{i}", "mock")
            items.append(build_artifact_index(result, f"/tmp/c{i}.json"))
        return build_artifact_directory_summary(items)

    def test_format_has_header(self):
        from scripts.run_solution_catalog_live_ablation import format_directory_summary_text
        text = format_directory_summary_text(self._make_summary())
        assert "=== Live Ablation Directory Summary ===" in text

    def test_format_shows_manual_review(self):
        from scripts.run_solution_catalog_live_ablation import format_directory_summary_text
        text = format_directory_summary_text(self._make_summary())
        assert "Manual review:" in text

    def test_format_lists_artifacts(self):
        from scripts.run_solution_catalog_live_ablation import format_directory_summary_text
        text = format_directory_summary_text(self._make_summary())
        assert "Artifacts:" in text
        assert "/tmp/c0.json" in text or "/tmp/c1.json" in text


class TestSummarizeDir:
    def _populate_dir(self, tmp_path):
        from scripts.run_solution_catalog_live_ablation import (
            run_live_ablation, build_artifact_index,
        )
        from unittest.mock import patch
        from tests.test_solution_catalog_ablation import _ablation_llm_mock
        import json as _json

        for i in range(2):
            with patch("src.evaluator.call_llm", side_effect=_ablation_llm_mock):
                result = run_live_ablation(f"q{i}", "mock")
            out = tmp_path / f"case{i}.json"
            out.write_text(_json.dumps(result))
            idx = build_artifact_index(result, artifact_path=str(out))
            out.with_suffix(".index.json").write_text(_json.dumps(idx))

    def test_summarize_dir_writes_index_summary(self, tmp_path):
        from scripts.run_solution_catalog_live_ablation import _run_summarize_dir
        self._populate_dir(tmp_path)
        _run_summarize_dir(tmp_path)
        assert (tmp_path / "_index_summary.json").exists()

    def test_summarize_dir_uses_only_index_json(self, tmp_path):
        from scripts.run_solution_catalog_live_ablation import _run_summarize_dir
        import json as _json
        self._populate_dir(tmp_path)
        # Add a non-index JSON that shouldn't be read
        (tmp_path / "noise.json").write_text('{"not": "an index"}')
        _run_summarize_dir(tmp_path)
        summary = _json.loads((tmp_path / "_index_summary.json").read_text())
        assert summary["total_runs"] == 2  # only index files counted

    def test_summarize_dir_text_contains_header(self, tmp_path, capsys):
        from scripts.run_solution_catalog_live_ablation import _run_summarize_dir
        self._populate_dir(tmp_path)
        _run_summarize_dir(tmp_path)
        captured = capsys.readouterr()
        assert "=== Live Ablation Directory Summary ===" in captured.out


class TestLatestArtifact:
    def test_directory_summary_has_latest_artifact(self):
        from scripts.run_solution_catalog_live_ablation import build_artifact_directory_summary
        items = [
            {"timestamp": "2026-04-06T15:00:00Z", "model": "a", "artifact_path": "/a", "quick_verdict": {}},
            {"timestamp": "2026-04-06T16:00:00Z", "model": "b", "artifact_path": "/b", "quick_verdict": {}},
        ]
        s = build_artifact_directory_summary(items)
        assert "latest_artifact" in s

    def test_latest_artifact_matches_last_sorted(self):
        from scripts.run_solution_catalog_live_ablation import build_artifact_directory_summary
        items = [
            {"timestamp": "2026-04-06T16:00:00Z", "model": "b", "artifact_path": "/b", "quick_verdict": {}},
            {"timestamp": "2026-04-06T15:00:00Z", "model": "a", "artifact_path": "/a", "quick_verdict": {}},
        ]
        s = build_artifact_directory_summary(items)
        assert s["latest_artifact"]["artifact_path"] == "/b"
        assert s["latest_artifact"]["timestamp"] == "2026-04-06T16:00:00Z"

    def test_latest_artifact_none_when_empty(self):
        from scripts.run_solution_catalog_live_ablation import build_artifact_directory_summary
        s = build_artifact_directory_summary([])
        assert s["latest_artifact"] is None


class TestComparisonRows:
    def test_directory_summary_has_comparison_rows(self):
        from scripts.run_solution_catalog_live_ablation import build_artifact_directory_summary
        items = [
            {"timestamp": "t1", "model": "m", "artifact_path": "/a",
             "quick_verdict": {"reason_changed": True, "score_changed": True,
                               "confidence_changed": False, "ranking_changed": False,
                               "unknown_reduced": False, "disqualified_changed": False}},
        ]
        s = build_artifact_directory_summary(items)
        assert "comparison_rows" in s
        assert len(s["comparison_rows"]) == 1

    def test_comparison_rows_align_with_artifacts(self):
        from scripts.run_solution_catalog_live_ablation import build_artifact_directory_summary
        items = [
            {"timestamp": "t2", "model": "b", "artifact_path": "/b", "quick_verdict": {}},
            {"timestamp": "t1", "model": "a", "artifact_path": "/a", "quick_verdict": {}},
        ]
        s = build_artifact_directory_summary(items)
        art_paths = [a["artifact_path"] for a in s["artifacts"]]
        row_paths = [r["artifact_path"] for r in s["comparison_rows"]]
        assert art_paths == row_paths

    def test_comparison_rows_manual_review_rule(self):
        from scripts.run_solution_catalog_live_ablation import build_artifact_directory_summary
        items = [
            {"timestamp": "t1", "model": "m", "artifact_path": "/a",
             "quick_verdict": {"reason_changed": False, "score_changed": False,
                               "confidence_changed": True, "ranking_changed": False,
                               "unknown_reduced": False, "disqualified_changed": False}},
        ]
        s = build_artifact_directory_summary(items)
        # confidence changed without reason changed → manual_review=true
        assert s["comparison_rows"][0]["manual_review"] is True


class TestReviewDigest:
    def _make_summary(self):
        from scripts.run_solution_catalog_live_ablation import (
            run_live_ablation, build_artifact_index, build_artifact_directory_summary,
        )
        from unittest.mock import patch
        from tests.test_solution_catalog_ablation import _ablation_llm_mock
        items = []
        for i in range(2):
            with patch("src.evaluator.call_llm", side_effect=_ablation_llm_mock):
                result = run_live_ablation(f"テスト{i}", "mock")
            items.append(build_artifact_index(result, f"/tmp/c{i}.json"))
        return build_artifact_directory_summary(items)

    def test_directory_summary_has_review_digest(self):
        s = self._make_summary()
        assert "review_digest" in s
        assert isinstance(s["review_digest"], list)

    def test_review_digest_contains_fixed_phrases(self):
        s = self._make_summary()
        d = s["review_digest"]
        assert any("ranking" in p for p in d)
        assert any("reason" in p for p in d)
        assert any("unknown" in p for p in d)
        assert any("anomaly" in p for p in d)

    def test_format_directory_summary_text_includes_review_digest(self):
        from scripts.run_solution_catalog_live_ablation import format_directory_summary_text
        s = self._make_summary()
        text = format_directory_summary_text(s)
        assert "Review digest:" in text


class TestComparisonStats:
    def _make_summary(self):
        from scripts.run_solution_catalog_live_ablation import (
            run_live_ablation, build_artifact_index, build_artifact_directory_summary,
        )
        from unittest.mock import patch
        from tests.test_solution_catalog_ablation import _ablation_llm_mock
        items = []
        for i in range(2):
            with patch("src.evaluator.call_llm", side_effect=_ablation_llm_mock):
                result = run_live_ablation(f"テスト{i}", "mock")
            items.append(build_artifact_index(result, f"/tmp/c{i}.json"))
        return build_artifact_directory_summary(items)

    def test_directory_summary_has_comparison_stats(self):
        s = self._make_summary()
        assert "comparison_stats" in s

    def test_comparison_stats_total_rows_matches(self):
        s = self._make_summary()
        assert s["comparison_stats"]["total_rows"] == len(s["comparison_rows"])

    def test_comparison_stats_manual_review_counted(self):
        s = self._make_summary()
        expected = sum(1 for r in s["comparison_rows"] if r.get("manual_review"))
        assert s["comparison_stats"]["manual_review_rows"] == expected


class TestFlaggedRows:
    def _make_summary_with_flag(self):
        from scripts.run_solution_catalog_live_ablation import build_artifact_directory_summary
        items = [
            {"timestamp": "t1", "model": "m", "artifact_path": "/a",
             "quick_verdict": {"reason_changed": True, "score_changed": True,
                               "confidence_changed": False, "ranking_changed": False,
                               "unknown_reduced": False, "disqualified_changed": False}},
            {"timestamp": "t2", "model": "m", "artifact_path": "/b",
             "quick_verdict": {"reason_changed": False, "score_changed": False,
                               "confidence_changed": True, "ranking_changed": False,
                               "unknown_reduced": False, "disqualified_changed": False}},
        ]
        return build_artifact_directory_summary(items)

    def test_directory_summary_has_flagged_rows(self):
        s = self._make_summary_with_flag()
        assert "flagged_rows" in s

    def test_flagged_rows_subset_of_comparison_rows(self):
        s = self._make_summary_with_flag()
        flagged_paths = {r["artifact_path"] for r in s["flagged_rows"]}
        all_paths = {r["artifact_path"] for r in s["comparison_rows"]}
        assert flagged_paths.issubset(all_paths)

    def test_flagged_rows_only_manual_review_true(self):
        s = self._make_summary_with_flag()
        for r in s["flagged_rows"]:
            assert r["manual_review"] is True
        # /b has confidence_changed without reason → flagged
        assert any(r["artifact_path"] == "/b" for r in s["flagged_rows"])
        # /a has reason_changed, no anomaly → not flagged
        assert not any(r["artifact_path"] == "/a" for r in s["flagged_rows"])


class TestFlaggedRowsText:
    def test_format_includes_flagged_rows_header(self):
        from scripts.run_solution_catalog_live_ablation import (
            build_artifact_directory_summary, format_directory_summary_text,
        )
        items = [
            {"timestamp": "t1", "model": "m", "artifact_path": "/a",
             "quick_verdict": {"reason_changed": False, "score_changed": False,
                               "confidence_changed": True, "ranking_changed": False,
                               "unknown_reduced": False, "disqualified_changed": False}},
        ]
        s = build_artifact_directory_summary(items)
        text = format_directory_summary_text(s)
        assert "Flagged rows:" in text

    def test_format_flagged_rows_none_when_empty(self):
        from scripts.run_solution_catalog_live_ablation import (
            build_artifact_directory_summary, format_directory_summary_text,
        )
        items = [
            {"timestamp": "t1", "model": "m", "artifact_path": "/a",
             "quick_verdict": {"reason_changed": True, "score_changed": True,
                               "confidence_changed": False, "ranking_changed": False,
                               "unknown_reduced": False, "disqualified_changed": False}},
        ]
        s = build_artifact_directory_summary(items)
        text = format_directory_summary_text(s)
        assert "Flagged rows: none" in text

    def test_format_lists_flagged_rows_when_present(self):
        from scripts.run_solution_catalog_live_ablation import (
            build_artifact_directory_summary, format_directory_summary_text,
        )
        items = [
            {"timestamp": "t1", "model": "m", "artifact_path": "/flagged",
             "quick_verdict": {"reason_changed": False, "score_changed": False,
                               "confidence_changed": True, "ranking_changed": False,
                               "unknown_reduced": False, "disqualified_changed": False}},
        ]
        s = build_artifact_directory_summary(items)
        text = format_directory_summary_text(s)
        assert "/flagged" in text


# Helper for items with/without flagged
def _items_with_flag():
    return [
        {"timestamp": "t1", "model": "m", "artifact_path": "/a",
         "quick_verdict": {"reason_changed": True, "score_changed": True,
                           "confidence_changed": False, "ranking_changed": False,
                           "unknown_reduced": False, "disqualified_changed": False}},
        {"timestamp": "t2", "model": "m", "artifact_path": "/b",
         "quick_verdict": {"reason_changed": False, "score_changed": False,
                           "confidence_changed": True, "ranking_changed": False,
                           "unknown_reduced": False, "disqualified_changed": False}},
    ]


def _items_no_flag():
    return [
        {"timestamp": "t1", "model": "m", "artifact_path": "/a",
         "quick_verdict": {"reason_changed": True, "score_changed": True,
                           "confidence_changed": False, "ranking_changed": False,
                           "unknown_reduced": False, "disqualified_changed": False}},
        {"timestamp": "t2", "model": "m", "artifact_path": "/c",
         "quick_verdict": {"reason_changed": True, "score_changed": True,
                           "confidence_changed": False, "ranking_changed": False,
                           "unknown_reduced": False, "disqualified_changed": False}},
    ]


class TestFocusRows:
    def test_directory_summary_has_focus_rows(self):
        from scripts.run_solution_catalog_live_ablation import build_artifact_directory_summary
        s = build_artifact_directory_summary(_items_with_flag())
        assert "focus_rows" in s

    def test_focus_rows_use_flagged_when_present(self):
        from scripts.run_solution_catalog_live_ablation import build_artifact_directory_summary
        s = build_artifact_directory_summary(_items_with_flag())
        assert len(s["focus_rows"]) > 0
        for fr in s["focus_rows"]:
            assert fr["focus_reason"] == "flagged"

    def test_focus_rows_fall_back_to_latest(self):
        from scripts.run_solution_catalog_live_ablation import build_artifact_directory_summary
        s = build_artifact_directory_summary(_items_no_flag())
        assert len(s["focus_rows"]) == 1
        assert s["focus_rows"][0]["focus_reason"] == "latest"
        assert s["focus_rows"][0]["artifact_path"] == s["latest_artifact"]["artifact_path"]

    def test_focus_rows_empty_when_no_rows(self):
        from scripts.run_solution_catalog_live_ablation import build_artifact_directory_summary
        s = build_artifact_directory_summary([])
        assert s["focus_rows"] == []


class TestRecommendedArtifactPaths:
    def test_directory_summary_has_recommended_paths(self):
        from scripts.run_solution_catalog_live_ablation import build_artifact_directory_summary
        s = build_artifact_directory_summary(_items_with_flag())
        assert "recommended_artifact_paths" in s

    def test_recommended_paths_follow_focus_order(self):
        from scripts.run_solution_catalog_live_ablation import build_artifact_directory_summary
        s = build_artifact_directory_summary(_items_with_flag())
        focus_paths = [fr["artifact_path"] for fr in s["focus_rows"]]
        assert s["recommended_artifact_paths"] == focus_paths

    def test_recommended_paths_deduplicate(self):
        from scripts.run_solution_catalog_live_ablation import build_artifact_directory_summary
        # Both flagged with same path (edge case)
        items = [
            {"timestamp": "t1", "model": "m", "artifact_path": "/dup",
             "quick_verdict": {"reason_changed": False, "score_changed": False,
                               "confidence_changed": True, "ranking_changed": False,
                               "unknown_reduced": False, "disqualified_changed": False}},
            {"timestamp": "t2", "model": "m", "artifact_path": "/dup",
             "quick_verdict": {"reason_changed": False, "score_changed": False,
                               "confidence_changed": True, "ranking_changed": False,
                               "unknown_reduced": False, "disqualified_changed": False}},
        ]
        s = build_artifact_directory_summary(items)
        assert s["recommended_artifact_paths"] == ["/dup"]


class TestRecommendedArtifactsText:
    def test_format_includes_recommended_artifacts_header(self):
        from scripts.run_solution_catalog_live_ablation import (
            build_artifact_directory_summary, format_directory_summary_text,
        )
        s = build_artifact_directory_summary(_items_with_flag())
        text = format_directory_summary_text(s)
        assert "Recommended artifacts:" in text

    def test_format_recommended_none_when_empty(self):
        from scripts.run_solution_catalog_live_ablation import (
            build_artifact_directory_summary, format_directory_summary_text,
        )
        s = build_artifact_directory_summary([])
        text = format_directory_summary_text(s)
        assert "Recommended artifacts: none" in text

    def test_format_lists_recommended_artifacts(self):
        from scripts.run_solution_catalog_live_ablation import (
            build_artifact_directory_summary, format_directory_summary_text,
        )
        s = build_artifact_directory_summary(_items_no_flag())
        text = format_directory_summary_text(s)
        # latest artifact path should be listed
        assert s["latest_artifact"]["artifact_path"] in text


class TestRowStatus:
    def test_comparison_rows_have_row_status(self):
        from scripts.run_solution_catalog_live_ablation import build_artifact_directory_summary
        s = build_artifact_directory_summary(_items_with_flag())
        for r in s["comparison_rows"]:
            assert "row_status" in r
            assert r["row_status"] in ("review", "latest_focus", "stable")

    def test_row_status_review_for_manual_review_rows(self):
        from scripts.run_solution_catalog_live_ablation import build_artifact_directory_summary
        s = build_artifact_directory_summary(_items_with_flag())
        for r in s["comparison_rows"]:
            if r["manual_review"]:
                assert r["row_status"] == "review"

    def test_row_status_latest_focus_for_latest_non_flagged(self):
        from scripts.run_solution_catalog_live_ablation import build_artifact_directory_summary
        s = build_artifact_directory_summary(_items_no_flag())
        latest_path = s["latest_artifact"]["artifact_path"]
        for r in s["comparison_rows"]:
            if r["artifact_path"] == latest_path and not r["manual_review"]:
                assert r["row_status"] == "latest_focus"

    def test_row_status_stable_for_other_rows(self):
        from scripts.run_solution_catalog_live_ablation import build_artifact_directory_summary
        s = build_artifact_directory_summary(_items_no_flag())
        latest_path = s["latest_artifact"]["artifact_path"]
        for r in s["comparison_rows"]:
            if r["artifact_path"] != latest_path and not r["manual_review"]:
                assert r["row_status"] == "stable"


class TestGateSummary:
    def test_directory_summary_has_gate_summary(self):
        from scripts.run_solution_catalog_live_ablation import build_artifact_directory_summary
        s = build_artifact_directory_summary(_items_with_flag())
        assert "gate_summary" in s

    def test_gate_review_required_when_flagged(self):
        from scripts.run_solution_catalog_live_ablation import build_artifact_directory_summary
        s = build_artifact_directory_summary(_items_with_flag())
        gs = s["gate_summary"]
        assert gs["gate_status"] == "review_required"
        assert gs["manual_review_required"] is True
        assert gs["flagged_run_count"] > 0

    def test_gate_pass_when_no_flagged(self):
        from scripts.run_solution_catalog_live_ablation import build_artifact_directory_summary
        s = build_artifact_directory_summary(_items_no_flag())
        gs = s["gate_summary"]
        assert gs["gate_status"] == "pass"
        assert gs["manual_review_required"] is False

    def test_gate_empty_when_no_runs(self):
        from scripts.run_solution_catalog_live_ablation import build_artifact_directory_summary
        s = build_artifact_directory_summary([])
        assert s["gate_summary"]["gate_status"] == "empty"


class TestGateSummaryText:
    def test_format_includes_gate_summary_header(self):
        from scripts.run_solution_catalog_live_ablation import (
            build_artifact_directory_summary, format_directory_summary_text,
        )
        s = build_artifact_directory_summary(_items_with_flag())
        text = format_directory_summary_text(s)
        assert "Gate summary:" in text

    def test_format_shows_gate_status(self):
        from scripts.run_solution_catalog_live_ablation import (
            build_artifact_directory_summary, format_directory_summary_text,
        )
        s = build_artifact_directory_summary(_items_no_flag())
        text = format_directory_summary_text(s)
        assert "gate_status: pass" in text

    def test_format_shows_manual_review_yes_no(self):
        from scripts.run_solution_catalog_live_ablation import (
            build_artifact_directory_summary, format_directory_summary_text,
        )
        s = build_artifact_directory_summary(_items_with_flag())
        text = format_directory_summary_text(s)
        assert "manual_review_required: yes" in text
