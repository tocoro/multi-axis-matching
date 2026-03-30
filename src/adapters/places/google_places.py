"""Google Places adapter.

GooglePlacesSearcher: Text Search API (New) による候補検索。
GooglePlacesRetriever: 未実装 (Place Details)。

設計詳細は docs/google_places_design.md を参照。
"""

import logging

import httpx

from src.adapters.places.config import GooglePlacesConfig

logger = logging.getLogger(__name__)

_TEXT_SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"
_FIELD_MASK = (
    "places.id,"
    "places.displayName,"
    "places.formattedAddress,"
    "places.primaryType,"
    "places.priceLevel,"
    "places.rating"
)


def build_text_query(conditions: dict) -> str:
    """conditions から Google Places textQuery を構築する。

    Rules:
      genre + location → "{genre} restaurant in {location}"
      genre only       → "{genre} restaurant"
      location only    → "restaurant in {location}"
      none             → "restaurant"
    """
    genre = conditions.get("genre")
    location = conditions.get("location")

    parts: list[str] = []
    if genre:
        parts.append(f"{genre} restaurant")
    else:
        parts.append("restaurant")
    if location:
        parts.append(f"in {location}")

    return " ".join(parts)


def _build_snippet(place: dict) -> str:
    """API レスポンスの place から snippet を構築する。"""
    parts: list[str] = []
    if place.get("formattedAddress"):
        parts.append(place["formattedAddress"])
    if place.get("primaryType"):
        parts.append(place["primaryType"])
    if place.get("priceLevel"):
        parts.append(place["priceLevel"])
    if place.get("rating"):
        parts.append(f"rating {place['rating']}")
    return " / ".join(parts) if parts else ""


def _place_to_result(place: dict) -> dict:
    """API レスポンスの place を results[] 形式に変換する。"""
    display_name = place.get("displayName", {})
    return {
        "source": "google_places",
        "source_id": place.get("id", ""),
        "title": display_name.get("text", ""),
        "snippet": _build_snippet(place),
    }


class GooglePlacesSearcher:
    """Google Places Text Search API (New) による候補検索。"""

    def __init__(self, config: GooglePlacesConfig | None = None) -> None:
        self._config = config or GooglePlacesConfig.from_env()

    def search_places(
        self, conditions: dict, *, enable_fallback: bool = True,
    ) -> dict:
        if not self._config.api_key:
            raise ValueError(
                "GOOGLE_PLACES_API_KEY is not set. "
                "Provide it via environment variable or GooglePlacesConfig."
            )

        text_query = build_text_query(conditions)
        strict_conditions = {
            k: v for k, v in [
                ("genre", conditions.get("genre")),
                ("location", conditions.get("location")),
                ("max_price", conditions.get("max_price")),
            ] if v is not None
        }

        logger.info("Google Places search: textQuery=%r", text_query)

        api_error = None
        places: list[dict] = []

        try:
            places = self._call_api(text_query)
        except httpx.TimeoutException:
            api_error = "timeout"
            logger.warning("Google Places API timeout")
        except httpx.HTTPStatusError as e:
            api_error = f"http_{e.response.status_code}"
            logger.warning("Google Places API error: %s", e.response.status_code)
        except httpx.HTTPError as e:
            api_error = "http_error"
            logger.warning("Google Places API error: %s", e)

        api_result_count = len(places)
        results = [_place_to_result(p) for p in places]

        diagnostics = {
            "strict_conditions": strict_conditions,
            "fallback_enabled": enable_fallback,
            "fallback_applied": False,
            "matched_stage": "text_search",
            "fallback_steps": [],
            "strict_result_count": api_result_count,
            "final_result_count": len(results),
            "text_query": text_query,
            "location_bias_applied": False,
            "api_result_count": api_result_count,
            "api_error": api_error,
        }

        logger.info("Google Places search done: %d results, error=%s",
                     len(results), api_error)
        return {"results": results, "search_diagnostics": diagnostics}

    def _call_api(self, text_query: str) -> list[dict]:
        """Text Search API を呼び出す。"""
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": self._config.api_key,
            "X-Goog-FieldMask": _FIELD_MASK,
        }
        body = {
            "textQuery": text_query,
            "maxResultCount": self._config.max_results,
        }

        with httpx.Client(timeout=self._config.timeout_seconds) as client:
            resp = client.post(_TEXT_SEARCH_URL, json=body, headers=headers)
            resp.raise_for_status()

        data = resp.json()
        return data.get("places", [])


class GooglePlacesRetriever:
    """Google Places Place Details API による詳細取得。未実装。"""

    def __init__(self, config: GooglePlacesConfig | None = None) -> None:
        self._config = config or GooglePlacesConfig.from_env()

    def retrieve_place(self, source: str, source_id: str) -> dict:
        raise NotImplementedError(
            "GooglePlacesRetriever is not yet implemented. "
            "Set GOOGLE_PLACES_API_KEY and implement HTTP calls."
        )
