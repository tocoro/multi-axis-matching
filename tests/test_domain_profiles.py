"""DomainProfile / ProblemTypeSpec tests."""

import json
from unittest.mock import patch

import pytest

from src.domain.profiles import (
    CLINIC_PROFILE,
    DOMAIN_PROFILES,
    RESTAURANT_PROFILE,
    DomainProfile,
    ProblemTypeSpec,
    get_domain_profile,
)


# ===================================================================
# A. Profile definition
# ===================================================================


class TestProfileDefinition:
    def test_restaurant_profile_exists(self):
        p = get_domain_profile("restaurant")
        assert p is not None
        assert p.domain_name == "restaurant"

    def test_clinic_profile_exists(self):
        p = get_domain_profile("clinic")
        assert p is not None
        assert p.domain_name == "clinic"

    def test_restaurant_problem_type(self):
        p = get_domain_profile("restaurant")
        assert p.default_problem_type.problem_type == "local.restaurant"

    def test_clinic_problem_type(self):
        p = get_domain_profile("clinic")
        assert p.default_problem_type.problem_type == "local.clinic"

    def test_restaurant_risk_normal(self):
        p = get_domain_profile("restaurant")
        assert p.default_problem_type.risk_level == "normal"

    def test_clinic_risk_high(self):
        p = get_domain_profile("clinic")
        assert p.default_problem_type.risk_level == "high"

    def test_restaurant_supports_catalog(self):
        assert RESTAURANT_PROFILE.supports_solution_catalog is True

    def test_two_profiles_registered(self):
        assert len(DOMAIN_PROFILES) == 2


# ===================================================================
# B. Pipeline consistency
# ===================================================================


class TestPipelineConsistency:
    @patch("src.evaluator.call_llm")
    def test_restaurant_problem_type_matches_profile(self, mock_llm):
        from tests.test_restaurant_pipeline import _pipeline_llm_mock
        mock_llm.side_effect = _pipeline_llm_mock
        from src.pipeline.restaurant_pipeline import run_restaurant_pipeline
        r = run_restaurant_pipeline("prof-r", "恵比寿で静かに話せるイタリアン。予算は3000円以内")
        assert r["inferred_problem_type"] == RESTAURANT_PROFILE.default_problem_type.problem_type

    @patch("src.evaluator.call_llm")
    def test_clinic_problem_type_matches_profile(self, mock_llm):
        from tests.test_clinic_pipeline import _clinic_llm_mock
        mock_llm.side_effect = _clinic_llm_mock
        from src.pipeline.clinic_pipeline import run_clinic_pipeline
        r = run_clinic_pipeline("prof-c", "内科を受診したい")
        assert r["inferred_problem_type"] == CLINIC_PROFILE.default_problem_type.problem_type

    @patch("src.evaluator.call_llm")
    def test_restaurant_domain_profile_in_response(self, mock_llm):
        from tests.test_restaurant_pipeline import _pipeline_llm_mock
        mock_llm.side_effect = _pipeline_llm_mock
        from src.pipeline.restaurant_pipeline import run_restaurant_pipeline
        r = run_restaurant_pipeline("prof-r2", "恵比寿で静かに話せるイタリアン。予算は3000円以内")
        assert r["domain_profile"]["domain"] == "restaurant"
        assert r["domain_profile"]["risk_level"] == "normal"

    @patch("src.evaluator.call_llm")
    def test_clinic_domain_profile_in_response(self, mock_llm):
        from tests.test_clinic_pipeline import _clinic_llm_mock
        mock_llm.side_effect = _clinic_llm_mock
        from src.pipeline.clinic_pipeline import run_clinic_pipeline
        r = run_clinic_pipeline("prof-c2", "内科を受診したい")
        assert r["domain_profile"]["domain"] == "clinic"
        assert r["domain_profile"]["risk_level"] == "high"


# ===================================================================
# C. Example axes
# ===================================================================


class TestExampleAxes:
    def test_restaurant_axes_include_cuisine(self):
        p = get_domain_profile("restaurant")
        assert "cuisine" in p.default_problem_type.example_axes

    def test_restaurant_axes_include_budget(self):
        p = get_domain_profile("restaurant")
        assert "budget" in p.default_problem_type.example_axes

    def test_clinic_axes_include_specialty(self):
        p = get_domain_profile("clinic")
        assert "specialty_fit" in p.default_problem_type.example_axes

    def test_clinic_axes_include_insurance(self):
        p = get_domain_profile("clinic")
        assert "insurance" in p.default_problem_type.example_axes

    def test_axes_differ_between_domains(self):
        r = get_domain_profile("restaurant")
        c = get_domain_profile("clinic")
        assert set(r.default_problem_type.example_axes) != set(c.default_problem_type.example_axes)


# ===================================================================
# D. Missing profile
# ===================================================================


class TestMissingProfile:
    def test_unknown_domain_returns_none(self):
        assert get_domain_profile("unknown_domain") is None

    def test_empty_string_returns_none(self):
        assert get_domain_profile("") is None
