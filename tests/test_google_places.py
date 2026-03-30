"""Tests for GooglePlacesSearcher."""

import json
from unittest.mock import patch, MagicMock

import httpx
import pytest

from src.adapters.places.config import GooglePlacesConfig
from src.adapters.places.google_places import (
    GooglePlacesSearcher,
    GooglePlacesRetriever,
    build_text_query,
)


# ===================================================================
# A. textQuery generation
# ===================================================================


class TestBuildTextQuery:
    def test_genre_and_location(self):
        assert build_text_query({"genre": "italian", "location": "恵比寿"}) == \
            "italian restaurant in 恵比寿"

    def test_genre_only(self):
        assert build_text_query({"genre": "french"}) == "french restaurant"

    def test_location_only(self):
        assert build_text_query({"location": "渋谷"}) == "restaurant in 渋谷"

    def test_no_conditions(self):
        assert build_text_query({}) == "restaurant"

    def test_max_price_ignored(self):
        q = build_text_query({"genre": "italian", "max_price": 3000})
        assert "3000" not in q
        assert q == "italian restaurant"

    def test_atmosphere_ignored(self):
        q = build_text_query({"genre": "italian", "atmosphere": "quiet"})
        assert q == "italian restaurant"


# ===================================================================
# B. API response mocked
# ===================================================================

_MOCK_API_RESPONSE = {
    "places": [
        {
            "id": "ChIJ_abc123",
            "displayName": {"text": "Trattoria Test", "languageCode": "ja"},
            "formattedAddress": "東京都渋谷区恵比寿1-2-3",
            "primaryType": "italian_restaurant",
            "priceLevel": "PRICE_LEVEL_MODERATE",
            "rating": 4.2,
        },
        {
            "id": "ChIJ_def456",
            "displayName": {"text": "Osteria Mock", "languageCode": "ja"},
            "formattedAddress": "東京都渋谷区恵比寿4-5-6",
            "primaryType": "italian_restaurant",
            "rating": 3.8,
        },
    ]
}


def _make_config(api_key="test-key"):
    return GooglePlacesConfig(api_key=api_key, timeout_seconds=5, max_results=5)


def _mock_response(json_data, status_code=200):
    resp = httpx.Response(
        status_code=status_code,
        json=json_data,
        request=httpx.Request("POST", "https://example.com"),
    )
    return resp


class TestGooglePlacesSearcherMocked:
    @patch("src.adapters.places.google_places.httpx.Client")
    def test_returns_results_and_diagnostics(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = _mock_response(_MOCK_API_RESPONSE)
        mock_client_cls.return_value = mock_client

        searcher = GooglePlacesSearcher(config=_make_config())
        output = searcher.search_places({"genre": "italian", "location": "恵比寿"})

        results = output["results"]
        diag = output["search_diagnostics"]

        assert len(results) == 2
        assert results[0]["source"] == "google_places"
        assert results[0]["source_id"] == "ChIJ_abc123"
        assert results[0]["title"] == "Trattoria Test"
        assert "恵比寿" in results[0]["snippet"]
        assert "rating 4.2" in results[0]["snippet"]

        assert diag["text_query"] == "italian restaurant in 恵比寿"
        assert diag["api_result_count"] == 2
        assert diag["final_result_count"] == 2
        assert diag["api_error"] is None
        assert diag["matched_stage"] == "text_search"
        assert diag["fallback_applied"] is False

    @patch("src.adapters.places.google_places.httpx.Client")
    def test_empty_results(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = _mock_response({})
        mock_client_cls.return_value = mock_client

        searcher = GooglePlacesSearcher(config=_make_config())
        output = searcher.search_places({"genre": "sushi", "location": "六本木"})

        assert output["results"] == []
        assert output["search_diagnostics"]["api_result_count"] == 0
        assert output["search_diagnostics"]["api_error"] is None

    @patch("src.adapters.places.google_places.httpx.Client")
    def test_strict_conditions_recorded(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = _mock_response(_MOCK_API_RESPONSE)
        mock_client_cls.return_value = mock_client

        searcher = GooglePlacesSearcher(config=_make_config())
        output = searcher.search_places({
            "genre": "italian", "location": "恵比寿", "max_price": 3000,
        })

        diag = output["search_diagnostics"]
        assert diag["strict_conditions"] == {
            "genre": "italian", "location": "恵比寿", "max_price": 3000,
        }

    @patch("src.adapters.places.google_places.httpx.Client")
    def test_snippet_handles_missing_fields(self, mock_client_cls):
        """priceLevel 等が無い place でも snippet が壊れない。"""
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = _mock_response({
            "places": [{"id": "x", "displayName": {"text": "Minimal"}}],
        })
        mock_client_cls.return_value = mock_client

        searcher = GooglePlacesSearcher(config=_make_config())
        output = searcher.search_places({})
        assert output["results"][0]["title"] == "Minimal"
        assert output["results"][0]["snippet"] == ""


# ===================================================================
# C. Error handling
# ===================================================================


class TestGooglePlacesSearcherErrors:
    def test_no_api_key_raises(self):
        searcher = GooglePlacesSearcher(config=_make_config(api_key=""))
        with pytest.raises(ValueError, match="GOOGLE_PLACES_API_KEY"):
            searcher.search_places({"genre": "italian"})

    @patch("src.adapters.places.google_places.httpx.Client")
    def test_timeout_returns_empty_with_diagnostics(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.side_effect = httpx.ReadTimeout("timeout")
        mock_client_cls.return_value = mock_client

        searcher = GooglePlacesSearcher(config=_make_config())
        output = searcher.search_places({"genre": "italian"})

        assert output["results"] == []
        assert output["search_diagnostics"]["api_error"] == "timeout"
        assert output["search_diagnostics"]["api_result_count"] == 0

    @patch("src.adapters.places.google_places.httpx.Client")
    def test_http_error_returns_empty_with_diagnostics(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        resp = _mock_response({"error": "forbidden"}, status_code=403)
        mock_client.post.return_value = resp
        # raise_for_status を呼ぶと例外になるように設定
        def raise_for_status():
            raise httpx.HTTPStatusError("403", request=resp.request, response=resp)
        resp.raise_for_status = raise_for_status
        mock_client_cls.return_value = mock_client

        searcher = GooglePlacesSearcher(config=_make_config())
        output = searcher.search_places({"genre": "italian"})

        assert output["results"] == []
        assert output["search_diagnostics"]["api_error"] == "http_403"


# ===================================================================
# D. Adapter injection compatibility
# ===================================================================


class TestAdapterCompatibility:
    def test_mock_adapter_still_works(self):
        from src.adapters.places import MockPlaceSearcher
        output = MockPlaceSearcher().search_places(
            {"genre": "italian", "location": "恵比寿"})
        assert len(output["results"]) == 2

    def test_google_searcher_is_injectable(self):
        """GooglePlacesSearcher は PlaceSearcher interface を満たす。"""
        from src.pipeline.restaurant_pipeline import run_restaurant_pipeline
        # API key がないので呼ぶと ValueError だが、型としては注入可能
        searcher = GooglePlacesSearcher(config=_make_config(api_key=""))
        with pytest.raises(ValueError, match="GOOGLE_PLACES_API_KEY"):
            run_restaurant_pipeline(
                "test", "テスト", place_searcher=searcher)

    def test_retriever_still_not_implemented(self):
        with pytest.raises(NotImplementedError):
            GooglePlacesRetriever().retrieve_place("x", "y")
