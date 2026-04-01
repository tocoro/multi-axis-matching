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

# Fixed mapping: 地名 → locationBias circle パラメータ
# 将来的に Geocoding API に差し替える想定。値は概算。
_LOCATION_BIAS_CIRCLES: dict[str, dict] = {
    "恵比寿": {"latitude": 35.6467, "longitude": 139.7100, "radius": 1500.0},
    "渋谷": {"latitude": 35.6580, "longitude": 139.7016, "radius": 2000.0},
    "新宿": {"latitude": 35.6900, "longitude": 139.7000, "radius": 2500.0},
    "六本木": {"latitude": 35.6628, "longitude": 139.7310, "radius": 2000.0},
    "銀座": {"latitude": 35.6717, "longitude": 139.7649, "radius": 1500.0},
    "池袋": {"latitude": 35.7295, "longitude": 139.7109, "radius": 2000.0},
    "中目黒": {"latitude": 35.6440, "longitude": 139.6988, "radius": 1500.0},
    "代官山": {"latitude": 35.6486, "longitude": 139.7030, "radius": 1000.0},
}


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


def build_location_bias(location: str | None) -> dict | None:
    """Fixed mapping から locationBias パラメータを構築する。

    未知の地名には None を返す。将来的に Geocoding API で置き換え可能。
    """
    if location is None:
        return None
    coords = _LOCATION_BIAS_CIRCLES.get(location)
    if coords is None:
        return None
    return {
        "circle": {
            "center": {
                "latitude": coords["latitude"],
                "longitude": coords["longitude"],
            },
            "radius": coords["radius"],
        }
    }


def _format_primary_type(raw: str) -> str:
    """primaryType の API 生値を表示用に軽整形する。"""
    return raw.replace("_", " ")


def _build_snippet(place: dict) -> str:
    """API レスポンスの place から snippet を構築する。"""
    parts: list[str] = []
    if place.get("formattedAddress"):
        parts.append(place["formattedAddress"])
    if place.get("primaryType"):
        parts.append(_format_primary_type(place["primaryType"]))
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


def _build_search_body(
    text_query: str,
    conditions: dict,
    max_results: int,
) -> tuple[dict, bool]:
    """Text Search API の request body を構築する。

    Returns:
        (body dict, location_bias_applied bool)
    """
    body: dict = {
        "textQuery": text_query,
        "maxResultCount": max_results,
    }

    location = conditions.get("location")
    bias = build_location_bias(location)
    if bias is not None:
        body["locationBias"] = bias
        return body, True

    return body, False


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
        body, location_bias_applied = _build_search_body(
            text_query, conditions, self._config.max_results,
        )
        strict_conditions = {
            k: v for k, v in [
                ("genre", conditions.get("genre")),
                ("location", conditions.get("location")),
                ("max_price", conditions.get("max_price")),
            ] if v is not None
        }

        logger.info("Google Places search: textQuery=%r bias=%s",
                     text_query, location_bias_applied)

        api_error = None
        places: list[dict] = []

        try:
            places = self._call_api(body)
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
            # strict 1回目の API 結果件数 (fallback 未実装のため api_result_count と同値)
            "strict_result_count": api_result_count,
            "final_result_count": len(results),
            "text_query": text_query,
            "location_bias_applied": location_bias_applied,
            "api_result_count": api_result_count,
            "api_error": api_error,
        }

        logger.info("Google Places search done: %d results, bias=%s, error=%s",
                     len(results), location_bias_applied, api_error)
        return {"results": results, "search_diagnostics": diagnostics}

    def _call_api(self, body: dict) -> list[dict]:
        """Text Search API を呼び出す。

        Args:
            body: 構築済みの request body (textQuery, maxResultCount, locationBias 等)
        """
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": self._config.api_key,
            "X-Goog-FieldMask": _FIELD_MASK,
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
