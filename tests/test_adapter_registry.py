"""Adapter registry tests."""

import json
from unittest.mock import patch

import pytest

from src.domain.registry import (
    ADAPTER_REGISTRY,
    CLINIC_BINDING,
    RESTAURANT_BINDING,
    AdapterBinding,
    get_adapter_binding,
)


# ===================================================================
# A. Registry definition
# ===================================================================


class TestRegistryDefinition:
    def test_restaurant_binding_exists(self):
        b = get_adapter_binding("restaurant")
        assert b is not None
        assert b.domain_name == "restaurant"

    def test_clinic_binding_exists(self):
        b = get_adapter_binding("clinic")
        assert b is not None
        assert b.domain_name == "clinic"

    def test_two_bindings_registered(self):
        assert len(ADAPTER_REGISTRY) == 2


# ===================================================================
# B. Binding content
# ===================================================================


class TestBindingContent:
    def test_restaurant_has_searcher(self):
        b = get_adapter_binding("restaurant")
        searcher = b.searcher_factory()
        assert hasattr(searcher, "search_places")

    def test_restaurant_has_retriever(self):
        b = get_adapter_binding("restaurant")
        retriever = b.retriever_factory()
        assert hasattr(retriever, "retrieve_place")

    def test_restaurant_has_normalizer(self):
        b = get_adapter_binding("restaurant")
        assert callable(b.normalizer_fn)

    def test_clinic_has_searcher(self):
        b = get_adapter_binding("clinic")
        searcher = b.searcher_factory()
        assert hasattr(searcher, "search_places")

    def test_clinic_has_retriever(self):
        b = get_adapter_binding("clinic")
        retriever = b.retriever_factory()
        assert hasattr(retriever, "retrieve_place")

    def test_clinic_has_normalizer(self):
        b = get_adapter_binding("clinic")
        assert callable(b.normalizer_fn)

    def test_normalizers_differ(self):
        r = get_adapter_binding("restaurant")
        c = get_adapter_binding("clinic")
        assert r.normalizer_fn is not c.normalizer_fn


# ===================================================================
# C. Pipeline uses registry
# ===================================================================


class TestPipelineUsesRegistry:
    @patch("src.evaluator.call_llm")
    def test_restaurant_pipeline_works_via_registry(self, mock_llm):
        from tests.test_restaurant_pipeline import _pipeline_llm_mock
        mock_llm.side_effect = _pipeline_llm_mock
        from src.pipeline.restaurant_pipeline import run_restaurant_pipeline
        r = run_restaurant_pipeline("reg-r", "恵比寿で静かに話せるイタリアン。予算は3000円以内")
        assert len(r["ranking"]) == 2
        assert r["inferred_problem_type"] == "local.restaurant"

    @patch("src.evaluator.call_llm")
    def test_clinic_pipeline_works_via_registry(self, mock_llm):
        from tests.test_clinic_pipeline import _clinic_llm_mock
        mock_llm.side_effect = _clinic_llm_mock
        from src.pipeline.clinic_pipeline import run_clinic_pipeline
        r = run_clinic_pipeline("reg-c", "内科を受診したい")
        assert len(r["ranking"]) == 4
        assert r["inferred_problem_type"] == "local.clinic"


# ===================================================================
# D. Missing binding
# ===================================================================


class TestMissingBinding:
    def test_unknown_domain_returns_none(self):
        assert get_adapter_binding("unknown") is None

    def test_empty_string_returns_none(self):
        assert get_adapter_binding("") is None
