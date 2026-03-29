"""Google Places adapter stubs.

未実装。将来的に Places API (New) の Text Search / Place Details を使用する。
実装時に必要な環境変数: GOOGLE_PLACES_API_KEY

設計詳細は docs/google_places_design.md を参照。
"""

from src.adapters.places.config import GooglePlacesConfig


class GooglePlacesSearcher:
    """Google Places Text Search API による候補検索。

    Endpoint: POST https://places.googleapis.com/v1/places:searchText
    Fields: places.displayName, places.id, places.formattedAddress,
            places.primaryType, places.priceLevel, places.rating
    """

    def __init__(self, config: GooglePlacesConfig | None = None) -> None:
        self._config = config or GooglePlacesConfig.from_env()

    def search_places(
        self, conditions: dict, *, enable_fallback: bool = True,
    ) -> dict:
        raise NotImplementedError(
            "GooglePlacesSearcher is not yet implemented. "
            "Set GOOGLE_PLACES_API_KEY and implement HTTP calls."
        )


class GooglePlacesRetriever:
    """Google Places Place Details API による詳細取得。

    Endpoint: GET https://places.googleapis.com/v1/places/{place_id}
    Fields: displayName, formattedAddress, primaryType, types,
            regularOpeningHours, priceLevel, rating, userRatingCount,
            editorialSummary, websiteUri, googleMapsUri
    """

    def __init__(self, config: GooglePlacesConfig | None = None) -> None:
        self._config = config or GooglePlacesConfig.from_env()

    def retrieve_place(self, source: str, source_id: str) -> dict:
        raise NotImplementedError(
            "GooglePlacesRetriever is not yet implemented. "
            "Set GOOGLE_PLACES_API_KEY and implement HTTP calls."
        )
