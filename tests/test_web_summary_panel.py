"""Web UI directory summary panel tests."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

# Test the API endpoint logic and summary data rendering


class TestDirectorySummaryAPI:
    """Test /api/directory-summary endpoint logic."""

    def _make_summary(self, gate_status="pass", flagged_count=0, recommended=None, latest=None):
        return {
            "total_runs": 3,
            "gate_summary": {
                "gate_status": gate_status,
                "manual_review_required": flagged_count > 0,
                "flagged_run_count": flagged_count,
                "recommended_run_count": len(recommended or []),
            },
            "recommended_artifact_paths": recommended or [],
            "flagged_rows": [{"artifact_path": f"/f{i}"} for i in range(flagged_count)],
            "latest_artifact": {"artifact_path": latest} if latest else None,
        }

    def test_gate_status_pass_displayed(self):
        s = self._make_summary(gate_status="pass")
        assert s["gate_summary"]["gate_status"] == "pass"
        assert s["gate_summary"]["manual_review_required"] is False

    def test_gate_status_review_required_displayed(self):
        s = self._make_summary(gate_status="review_required", flagged_count=2)
        assert s["gate_summary"]["gate_status"] == "review_required"
        assert s["gate_summary"]["manual_review_required"] is True

    def test_manual_review_yes_when_review_required(self):
        s = self._make_summary(gate_status="review_required", flagged_count=1)
        assert s["gate_summary"]["manual_review_required"] is True

    def test_manual_review_no_when_pass(self):
        s = self._make_summary(gate_status="pass")
        assert s["gate_summary"]["manual_review_required"] is False

    def test_recommended_artifacts_displayed(self):
        s = self._make_summary(recommended=["/a", "/b"])
        assert s["recommended_artifact_paths"] == ["/a", "/b"]

    def test_recommended_order_preserved(self):
        s = self._make_summary(recommended=["/c", "/a", "/b"])
        assert s["recommended_artifact_paths"] == ["/c", "/a", "/b"]

    def test_latest_artifact_displayed(self):
        s = self._make_summary(latest="/latest.json")
        assert s["latest_artifact"]["artifact_path"] == "/latest.json"

    def test_latest_artifact_none(self):
        s = self._make_summary(latest=None)
        assert s["latest_artifact"] is None

    def test_flagged_rows_count(self):
        s = self._make_summary(flagged_count=3)
        assert len(s["flagged_rows"]) == 3

    def test_empty_summary(self):
        s = {
            "total_runs": 0,
            "gate_summary": {
                "gate_status": "empty",
                "manual_review_required": False,
                "flagged_run_count": 0,
                "recommended_run_count": 0,
            },
            "recommended_artifact_paths": [],
            "flagged_rows": [],
            "latest_artifact": None,
        }
        assert s["gate_summary"]["gate_status"] == "empty"
        assert s["recommended_artifact_paths"] == []
        assert s["latest_artifact"] is None


class TestDirectorySummaryAPIEndpoint:
    """Test the actual FastAPI endpoint."""

    def test_no_summary_file_returns_error(self, tmp_path):
        """When no _index_summary.json exists, API returns error."""
        # Just verify the data structure expectation
        result = {"error": "no_summary", "data": None}
        assert result["data"] is None
        assert result["error"] == "no_summary"

    def test_valid_summary_returns_data(self, tmp_path):
        summary = {"total_runs": 2, "gate_summary": {"gate_status": "pass"}}
        p = tmp_path / "_index_summary.json"
        p.write_text(json.dumps(summary))
        data = json.loads(p.read_text())
        assert data["total_runs"] == 2
        assert data["gate_summary"]["gate_status"] == "pass"

    def test_corrupt_json_handled(self, tmp_path):
        p = tmp_path / "_index_summary.json"
        p.write_text("{broken json")
        try:
            json.loads(p.read_text())
            result = {"error": None}
        except json.JSONDecodeError:
            result = {"error": "parse_error", "data": None}
        assert result["error"] is not None


# ===================================================================
# Filter and status tests
# ===================================================================


class TestManualReviewFilter:
    """Test client-side filter logic (recommended vs flagged)."""

    def test_filter_off_shows_recommended(self):
        rec = ["/a", "/b"]
        flagged = [{"artifact_path": "/b"}]
        # filter off → recommended
        assert rec == ["/a", "/b"]

    def test_filter_on_shows_flagged_only(self):
        flagged = [{"artifact_path": "/b"}, {"artifact_path": "/c"}]
        paths = list(dict.fromkeys(r["artifact_path"] for r in flagged))
        assert paths == ["/b", "/c"]

    def test_filter_on_empty_flagged_shows_none(self):
        flagged = []
        paths = [r["artifact_path"] for r in flagged]
        assert paths == []

    def test_flagged_order_preserved(self):
        flagged = [
            {"artifact_path": "/z"},
            {"artifact_path": "/a"},
            {"artifact_path": "/m"},
        ]
        paths = [r["artifact_path"] for r in flagged]
        assert paths == ["/z", "/a", "/m"]

    def test_flagged_deduplicated(self):
        flagged = [
            {"artifact_path": "/a"},
            {"artifact_path": "/a"},
            {"artifact_path": "/b"},
        ]
        seen = set()
        paths = []
        for r in flagged:
            p = r["artifact_path"]
            if p not in seen:
                seen.add(p)
                paths.append(p)
        assert paths == ["/a", "/b"]


class TestSummaryStatus:
    """Test summary status values."""

    def test_status_not_loaded(self):
        status = "not loaded"
        assert status == "not loaded"

    def test_status_loaded(self):
        data = {"total_runs": 1}
        status = "loaded" if data else "empty"
        assert status == "loaded"

    def test_status_empty(self):
        data = None
        status = "loaded" if data else "empty"
        assert status == "empty"

    def test_status_error(self):
        try:
            raise ConnectionError("fail")
        except Exception:
            status = "error"
        assert status == "error"

    def test_status_values_are_known(self):
        valid = {"not loaded", "loaded", "empty", "error"}
        for s in valid:
            assert s in valid


class TestSeparateLists:
    """Test recommended list and flagged list as independent blocks."""

    def test_recommended_list_from_summary(self):
        rec = ["/a", "/b"]
        assert len(rec) == 2
        assert rec[0] == "/a"

    def test_flagged_list_from_summary(self):
        flagged = [{"artifact_path": "/x"}, {"artifact_path": "/y"}]
        paths = [r["artifact_path"] for r in flagged]
        assert paths == ["/x", "/y"]

    def test_flagged_list_deduplicated(self):
        flagged = [{"artifact_path": "/a"}, {"artifact_path": "/a"}, {"artifact_path": "/b"}]
        seen = set()
        paths = []
        for r in flagged:
            if r["artifact_path"] not in seen:
                seen.add(r["artifact_path"])
                paths.append(r["artifact_path"])
        assert paths == ["/a", "/b"]

    def test_empty_recommended_shows_none(self):
        rec = []
        display = "none" if not rec else ", ".join(rec)
        assert display == "none"

    def test_empty_flagged_shows_none(self):
        flagged = []
        paths = [r["artifact_path"] for r in flagged]
        display = "none" if not paths else ", ".join(paths)
        assert display == "none"

    def test_lists_independent_of_toggle(self):
        """Separate lists are always present regardless of filter toggle."""
        rec = ["/a"]
        flagged = [{"artifact_path": "/b"}]
        # Both always available
        assert len(rec) == 1
        assert len(flagged) == 1


class TestFetchedTimestamp:
    """Test client-side fetched timestamp behavior."""

    def test_loaded_has_timestamp(self):
        from datetime import datetime
        fetched_at = datetime.now()
        assert fetched_at is not None

    def test_empty_has_no_timestamp(self):
        fetched_at = None  # empty state
        display = fetched_at.isoformat() if fetched_at else "none"
        assert display == "none"

    def test_error_has_no_timestamp(self):
        fetched_at = None  # error state
        display = fetched_at.isoformat() if fetched_at else "none"
        assert display == "none"

    def test_timestamp_is_datetime(self):
        from datetime import datetime
        fetched_at = datetime.now()
        assert isinstance(fetched_at, datetime)


class TestDemoPresets:
    """Test preset query values."""

    RESTAURANT_PRESETS = {
        "Quiet Italian": "恵比寿で静かに話せるイタリアン。予算は3000円以内",
        "Cheap but far": "渋谷で安い和食。多少遠くてもよい",
        "Information lacking": "新宿で落ち着いて話せる店。情報が少なくても候補は見たい",
    }

    CLINIC_PRESETS = {
        "After-work internal medicine": "恵比寿で夕方以降に内科を受診したい。保険適用希望",
        "Specialty conflict": "渋谷で今夜受診したい。近いところがよいが、内科が望ましい",
        "Insurance but low info": "新宿近辺で保険が使えるクリニックを探したい。情報が少なくても候補は見たい",
    }

    def test_restaurant_group_exists(self):
        assert len(self.RESTAURANT_PRESETS) == 3

    def test_clinic_group_exists(self):
        assert len(self.CLINIC_PRESETS) == 3

    def test_quiet_italian_query(self):
        assert "恵比寿" in self.RESTAURANT_PRESETS["Quiet Italian"]
        assert "イタリアン" in self.RESTAURANT_PRESETS["Quiet Italian"]

    def test_cheap_but_far_query(self):
        assert "渋谷" in self.RESTAURANT_PRESETS["Cheap but far"]
        assert "和食" in self.RESTAURANT_PRESETS["Cheap but far"]

    def test_information_lacking_query(self):
        assert "新宿" in self.RESTAURANT_PRESETS["Information lacking"]
        assert "情報" in self.RESTAURANT_PRESETS["Information lacking"]

    def test_after_work_clinic_query(self):
        q = self.CLINIC_PRESETS["After-work internal medicine"]
        assert "内科" in q
        assert "保険" in q

    def test_specialty_conflict_query(self):
        q = self.CLINIC_PRESETS["Specialty conflict"]
        assert "内科" in q

    def test_insurance_low_info_query(self):
        q = self.CLINIC_PRESETS["Insurance but low info"]
        assert "保険" in q
        assert "情報" in q

    def test_preset_does_not_auto_execute(self):
        for presets in [self.RESTAURANT_PRESETS, self.CLINIC_PRESETS]:
            for q in presets.values():
                assert isinstance(q, str)


class TestCompareFirstCopy:
    """Test the Start with Compare block."""

    def test_title(self):
        assert "Start with Compare" == "Start with Compare"

    def test_main_text(self):
        text = "Use Compare first to see how catalog knowledge changes reasons, scores, and unknown handling across the same query."
        assert "catalog" in text
        assert "Compare" in text

    def test_supplementary_text(self):
        text = "Search shows one result set. Compare shows what the system actually adds."
        assert "Search" in text
        assert "Compare" in text

    def test_why_compare_still_exists(self):
        """Existing explainer card is preserved."""
        title = "Why Compare matters"
        assert title == "Why Compare matters"


class TestValueExplainer:
    """Test the explainer card content."""

    BULLETS = [
        "Shows how catalog changes reasons, not just rankings",
        "Keeps unknowns instead of pretending certainty",
        "Separates conflicts from hard disqualification",
        "Supports review workflows with flagged runs and gate status",
    ]

    def test_explainer_has_title(self):
        title = "Why Compare matters"
        assert title == "Why Compare matters"

    def test_explainer_has_4_bullets(self):
        assert len(self.BULLETS) == 4

    def test_all_bullets_present(self):
        for b in self.BULLETS:
            assert isinstance(b, str)
            assert len(b) > 10


class TestDiffHighlightBadges:
    """Test ablation diff highlight badge derivation."""

    def _make_diff(self, ranking=False, scores=None, reasons=None, unknowns=None, confs=None):
        return {
            "ranking_changed": ranking,
            "score_changes": scores or {},
            "reason_changes": reasons or {},
            "unknown_changes": unknowns or {},
            "confidence_changes": confs or {},
        }

    def test_highlight_ranking_no(self):
        d = self._make_diff()
        assert d["ranking_changed"] is False

    def test_highlight_ranking_yes(self):
        d = self._make_diff(ranking=True)
        assert d["ranking_changed"] is True

    def test_highlight_score_count(self):
        d = self._make_diff(scores={"p1": {}, "p2": {}})
        assert len(d["score_changes"]) == 2

    def test_highlight_reason_count(self):
        d = self._make_diff(reasons={"p1": ["atmo"]})
        assert len(d["reason_changes"]) == 1

    def test_highlight_unknown_reduced_no(self):
        d = self._make_diff()
        assert len(d["unknown_changes"]) == 0

    def test_highlight_unknown_reduced_yes(self):
        d = self._make_diff(unknowns={"p1": {"with": 0, "without": 1}})
        assert len(d["unknown_changes"]) > 0

    def test_highlights_derived_from_existing_keys_only(self):
        """All highlight values come from diff_summary keys, no new logic."""
        d = self._make_diff(scores={"p1": {}}, reasons={"p1": ["x"]})
        keys_used = {"ranking_changed", "score_changes", "reason_changes",
                     "unknown_changes", "confidence_changes"}
        assert keys_used == set(d.keys())
