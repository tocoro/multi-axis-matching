"""Solution Catalog schema and sample validation tests."""

import json
from pathlib import Path

import jsonschema
import pytest

ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = ROOT / "schemas" / "solution_catalog.schema.json"
CATALOG_PATH = ROOT / "examples" / "restaurant_solution_catalog.json"

# Known mock candidate IDs
MOCK_CANDIDATE_IDS = {"place_1", "place_2", "place_3", "place_4"}


def _load_schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text("utf-8"))


def _load_catalog() -> list[dict]:
    return json.loads(CATALOG_PATH.read_text("utf-8"))


# ===================================================================
# A. Schema validation
# ===================================================================


class TestSchemaValidation:
    def test_all_samples_pass_schema(self):
        schema = _load_schema()
        for entry in _load_catalog():
            jsonschema.validate(instance=entry, schema=schema)

    def test_invalid_entry_fails(self):
        schema = _load_schema()
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(instance={"candidate_id": "x"}, schema=schema)

    def test_invalid_strength_fails(self):
        schema = _load_schema()
        bad = {
            "candidate_id": "x",
            "domain": "restaurant",
            "solution_claims": [
                {"problem_pattern": "p", "strength": "invalid", "reason": "r"}
            ],
            "hard_limitations": [],
            "evidence": {"source_type": "mock", "source_fields": []},
            "metadata": {},
        }
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(instance=bad, schema=schema)


# ===================================================================
# B. Field presence
# ===================================================================


class TestFieldPresence:
    def test_required_fields_exist(self):
        for entry in _load_catalog():
            assert "candidate_id" in entry
            assert "domain" in entry
            assert "solution_claims" in entry
            assert "hard_limitations" in entry
            assert "evidence" in entry
            assert "metadata" in entry

    def test_solution_claims_is_list(self):
        for entry in _load_catalog():
            assert isinstance(entry["solution_claims"], list)

    def test_hard_limitations_is_list(self):
        for entry in _load_catalog():
            assert isinstance(entry["hard_limitations"], list)

    def test_claims_have_required_fields(self):
        for entry in _load_catalog():
            for claim in entry["solution_claims"]:
                assert "problem_pattern" in claim
                assert "strength" in claim
                assert "reason" in claim

    def test_limitations_have_required_fields(self):
        for entry in _load_catalog():
            for lim in entry["hard_limitations"]:
                assert "problem_pattern" in lim
                assert "reason" in lim

    def test_evidence_has_source(self):
        for entry in _load_catalog():
            assert "source_type" in entry["evidence"]
            assert "source_fields" in entry["evidence"]

    def test_all_domains_are_restaurant(self):
        for entry in _load_catalog():
            assert entry["domain"] == "restaurant"

    def test_strength_values_valid(self):
        valid = {"strong", "medium", "weak"}
        for entry in _load_catalog():
            for claim in entry["solution_claims"]:
                assert claim["strength"] in valid


# ===================================================================
# C. Example consistency with mock candidates
# ===================================================================


class TestCandidateConsistency:
    def test_candidate_ids_match_mock(self):
        catalog_ids = {e["candidate_id"] for e in _load_catalog()}
        assert catalog_ids == MOCK_CANDIDATE_IDS

    def test_catalog_has_4_entries(self):
        assert len(_load_catalog()) == 4


# ===================================================================
# D. Content sanity checks
# ===================================================================


class TestContentSanity:
    def test_place_1_has_quiet_conversation_claim(self):
        catalog = {e["candidate_id"]: e for e in _load_catalog()}
        patterns = [c["problem_pattern"] for c in catalog["place_1"]["solution_claims"]]
        assert "quiet_conversation" in patterns

    def test_place_2_has_quiet_limitation(self):
        catalog = {e["candidate_id"]: e for e in _load_catalog()}
        patterns = [l["problem_pattern"] for l in catalog["place_2"]["hard_limitations"]]
        assert "quiet_conversation" in patterns

    def test_place_3_has_location_limitation(self):
        catalog = {e["candidate_id"]: e for e in _load_catalog()}
        patterns = [l["problem_pattern"] for l in catalog["place_3"]["hard_limitations"]]
        assert "ebisu_area" in patterns

    def test_place_4_has_weak_claim_only(self):
        catalog = {e["candidate_id"]: e for e in _load_catalog()}
        claims = catalog["place_4"]["solution_claims"]
        assert len(claims) == 1
        assert claims[0]["strength"] == "weak"

    def test_place_4_has_no_limitations(self):
        """情報欠落候補: limitation を書けるだけの情報がない。"""
        catalog = {e["candidate_id"]: e for e in _load_catalog()}
        assert catalog["place_4"]["hard_limitations"] == []
