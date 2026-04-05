"""Clinic solution catalog tests."""

import json
from pathlib import Path
from unittest.mock import patch

import jsonschema
import pytest

ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = ROOT / "schemas" / "solution_catalog.schema.json"
CATALOG_PATH = ROOT / "examples" / "clinic_solution_catalog.json"

CLINIC_IDS = {"clinic_1", "clinic_2", "clinic_3", "clinic_4"}


def _load_schema():
    return json.loads(SCHEMA_PATH.read_text("utf-8"))


def _load_catalog():
    return json.loads(CATALOG_PATH.read_text("utf-8"))


# ===================================================================
# A. Schema validation
# ===================================================================


class TestClinicCatalogSchema:
    def test_all_entries_pass_schema(self):
        schema = _load_schema()
        for entry in _load_catalog():
            jsonschema.validate(instance=entry, schema=schema)

    def test_all_domains_are_clinic(self):
        for entry in _load_catalog():
            assert entry["domain"] == "clinic"

    def test_candidate_ids_match_mock(self):
        ids = {e["candidate_id"] for e in _load_catalog()}
        assert ids == CLINIC_IDS

    def test_4_entries(self):
        assert len(_load_catalog()) == 4


# ===================================================================
# B. Content sanity
# ===================================================================


class TestClinicCatalogContent:
    def test_clinic_1_has_claims(self):
        catalog = {e["candidate_id"]: e for e in _load_catalog()}
        assert len(catalog["clinic_1"]["solution_claims"]) >= 3

    def test_clinic_1_has_after_work(self):
        catalog = {e["candidate_id"]: e for e in _load_catalog()}
        patterns = [c["problem_pattern"] for c in catalog["clinic_1"]["solution_claims"]]
        assert "after_work_visit" in patterns

    def test_clinic_4_weak_only(self):
        catalog = {e["candidate_id"]: e for e in _load_catalog()}
        claims = catalog["clinic_4"]["solution_claims"]
        assert len(claims) == 1
        assert claims[0]["strength"] == "weak"

    def test_clinic_4_no_limitations(self):
        catalog = {e["candidate_id"]: e for e in _load_catalog()}
        assert catalog["clinic_4"]["hard_limitations"] == []

    def test_clinic_3_has_specialty_limitation(self):
        catalog = {e["candidate_id"]: e for e in _load_catalog()}
        patterns = [l["problem_pattern"] for l in catalog["clinic_3"]["hard_limitations"]]
        assert "no_internal_medicine" in patterns

    def test_all_evidence_non_empty_source_type(self):
        for entry in _load_catalog():
            assert entry["evidence"]["source_type"] != ""


# ===================================================================
# C. No unknown as limitation
# ===================================================================


class TestClinicNoUnknownLimitation:
    def test_no_unknown_based_limitation(self):
        for entry in _load_catalog():
            for lim in entry["hard_limitations"]:
                assert "不明" not in lim["reason"]
                assert "情報がな" not in lim["reason"]


# ===================================================================
# D. Pipeline attachment
# ===================================================================


class TestClinicPipelineCatalog:
    @patch("src.evaluator.call_llm")
    def test_clinic_candidates_have_catalog(self, mock_llm):
        from tests.test_clinic_pipeline import _clinic_llm_mock
        mock_llm.side_effect = _clinic_llm_mock
        from src.pipeline.clinic_pipeline import run_clinic_pipeline
        r = run_clinic_pipeline("cat-c1", "内科を受診したい")
        src = r["candidate_sources"]
        assert "solution_catalog" in src["clinic_1"]
        claims = src["clinic_1"]["solution_catalog"]["solution_claims"]
        assert any(c["problem_pattern"] == "after_work_visit" for c in claims)

    @patch("src.evaluator.call_llm")
    def test_clinic_pipeline_without_catalog(self, mock_llm):
        from tests.test_clinic_pipeline import _clinic_llm_mock
        mock_llm.side_effect = _clinic_llm_mock
        from src.pipeline.clinic_pipeline import run_clinic_pipeline
        r = run_clinic_pipeline(
            "cat-c-none", "内科を受診したい",
            catalog_path="/nonexistent/__no__.json",
        )
        assert len(r["ranking"]) == 4
        assert "solution_catalog" not in r["candidate_sources"].get("clinic_1", {})


# ===================================================================
# E. Restaurant catalog not broken
# ===================================================================


class TestRestaurantCatalogIntact:
    def test_restaurant_catalog_still_valid(self):
        schema = _load_schema()
        restaurant_catalog = json.loads(
            (ROOT / "examples" / "restaurant_solution_catalog.json").read_text("utf-8")
        )
        for entry in restaurant_catalog:
            jsonschema.validate(instance=entry, schema=schema)
