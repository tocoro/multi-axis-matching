"""Mock place adapter: 固定候補プールによる deterministic 実装。"""

import logging

logger = logging.getLogger(__name__)

# 近隣エリアのグループ定義
_STATION_GROUPS: dict[str, set[str]] = {
    "恵比寿": {"恵比寿", "代官山", "中目黒"},
    "代官山": {"代官山", "恵比寿", "中目黒"},
    "中目黒": {"中目黒", "代官山", "恵比寿"},
    "渋谷": {"渋谷", "表参道", "原宿", "恵比寿"},
    "新宿": {"新宿", "新宿三丁目", "代々木"},
}

_PRICE_LEVEL_MAX: dict[str, int] = {
    "low": 2000,
    "mid": 3500,
    "high": 8000,
}

_MOCK_PLACES = [
    {
        "source": "place_search",
        "source_id": "place_1",
        "title": "Trattoria A",
        "snippet": "静かな雰囲気のイタリアン。恵比寿駅徒歩5分",
        "_tags": {"genre": "italian", "location": "恵比寿", "price_level": "mid"},
    },
    {
        "source": "place_search",
        "source_id": "place_2",
        "title": "Bar B",
        "snippet": "賑やかでカジュアルなバー。恵比寿",
        "_tags": {"genre": "bar", "location": "恵比寿", "price_level": "low"},
    },
    {
        "source": "place_search",
        "source_id": "place_3",
        "title": "Osteria C",
        "snippet": "中目黒の隠れ家イタリアン。リーズナブル",
        "_tags": {"genre": "italian", "location": "中目黒", "price_level": "low"},
    },
    {
        "source": "place_search",
        "source_id": "place_4",
        "title": "Restaurant D",
        "snippet": "落ち着いた雰囲気のお店",
        "_tags": {"genre": "unknown", "location": "unknown", "price_level": "unknown"},
    },
]

_MOCK_DETAILS: dict[str, dict] = {
    "place_1": {
        "name": "Trattoria A",
        "address": "東京都渋谷区恵比寿南1-2-3",
        "nearest_station": "恵比寿",
        "price_text": "￥2,000〜￥3,000",
        "category": "イタリアン",
        "atmosphere_text": "静かで落ち着いた雰囲気",
        "review_summary": "会話しやすいという評価が多い",
    },
    "place_2": {
        "name": "Bar B",
        "address": "東京都渋谷区恵比寿西3-4-5",
        "nearest_station": "恵比寿",
        "price_text": "￥1,000〜￥2,000",
        "category": "バー",
        "atmosphere_text": "賑やかでカジュアルな雰囲気",
        "review_summary": "友人同士で楽しめる",
    },
    "place_3": {
        "name": "Osteria C",
        "address": "東京都目黒区上目黒2-5-6",
        "nearest_station": "中目黒",
        "price_text": "￥1,500〜￥2,500",
        "category": "イタリアン",
        "atmosphere_text": "静かな隠れ家的空間",
        "review_summary": "料理の質が高いと評判",
    },
    "place_4": {
        "name": "Restaurant D",
        "address": None,
        "nearest_station": None,
        "price_text": None,
        "category": None,
        "atmosphere_text": "落ち着いた雰囲気",
        "review_summary": None,
    },
}


def _matches_genre(tags: dict, genre: str | None) -> bool:
    if genre is None:
        return True
    tag_genre = tags.get("genre", "unknown")
    return tag_genre != "unknown" and tag_genre == genre


def _matches_location(tags: dict, location: str | None) -> bool:
    if location is None:
        return True
    tag_loc = tags.get("location", "unknown")
    if tag_loc == "unknown":
        return False
    if tag_loc == location:
        return True
    return tag_loc in _STATION_GROUPS.get(location, set())


def _within_budget(tags: dict, max_price: int | None) -> bool:
    if max_price is None:
        return True
    price_level = tags.get("price_level", "unknown")
    if price_level == "unknown":
        return True
    approx_max = _PRICE_LEVEL_MAX.get(price_level)
    return approx_max is None or approx_max <= max_price


def _format_result(place: dict) -> dict:
    return {
        "source": place["source"],
        "source_id": place["source_id"],
        "title": place["title"],
        "snippet": place["snippet"],
    }


class MockPlaceSearcher:
    """Mock place search adapter: 固定候補プール + 条件フィルタ + fallback。"""

    def search_places(
        self, conditions: dict, *, enable_fallback: bool = True,
    ) -> dict:
        genre = conditions.get("genre")
        location = conditions.get("location")
        max_price = conditions.get("max_price")

        strict_conditions = {
            k: v for k, v in [
                ("genre", genre), ("location", location), ("max_price", max_price),
            ] if v is not None
        }
        fallback_steps: list[str] = []

        # Stage 1: genre + location
        results = [
            p for p in _MOCK_PLACES
            if _matches_genre(p["_tags"], genre)
            and _matches_location(p["_tags"], location)
        ]
        strict_result_count = len(results)
        matched_stage = "genre+location"

        if results:
            pass
        elif not enable_fallback:
            matched_stage = "strict_only"
        else:
            fallback_steps.append("genre+location")
            if genre:
                results = [
                    p for p in _MOCK_PLACES if _matches_genre(p["_tags"], genre)
                ]
            if results:
                matched_stage = "genre_only"
            else:
                fallback_steps.append("genre_only")
                if location:
                    results = [
                        p for p in _MOCK_PLACES
                        if _matches_location(p["_tags"], location)
                    ]
                if results:
                    matched_stage = "location_only"
                else:
                    fallback_steps.append("location_only")
                    results = list(_MOCK_PLACES)
                    matched_stage = "all"
                    fallback_steps.append("all")

        if max_price is not None and results:
            results.sort(key=lambda p: (
                0 if _within_budget(p["_tags"], max_price) else 1
            ))

        formatted = [_format_result(p) for p in results]
        logger.info("MockSearch [%s]: strict=%d final=%d",
                     matched_stage, strict_result_count, len(formatted))

        return {
            "results": formatted,
            "search_diagnostics": {
                "strict_conditions": strict_conditions,
                "fallback_enabled": enable_fallback,
                "fallback_applied": len(fallback_steps) > 0,
                "matched_stage": matched_stage,
                "fallback_steps": fallback_steps,
                "strict_result_count": strict_result_count,
                "final_result_count": len(formatted),
            },
        }


class MockPlaceRetriever:
    """Mock place retrieve adapter: source_id → 固定レコード。"""

    def retrieve_place(self, source: str, source_id: str) -> dict:
        raw_record = _MOCK_DETAILS.get(source_id)
        if raw_record is None:
            logger.warning("No mock data for source_id=%s", source_id)
            raw_record = {"name": source_id}

        logger.info("MockRetrieve %s: %d fields", source_id,
                     sum(1 for v in raw_record.values() if v is not None))
        return {
            "source": source,
            "source_id": source_id,
            "raw_record": raw_record,
        }
