"""Mock place search: 検索条件から候補サマリを返す。

フィルタ方針:
  Hard filter — genre, location が明確に不一致なら除外
  Soft filter — max_price は優先度付けに使用 (除外しない)
  Fallback   — 0 件時は段階的に条件緩和 (enable_fallback=True のとき)
  Strict     — enable_fallback=False なら strict 条件のみ。0 件ならそのまま 0 件
"""

import logging

logger = logging.getLogger(__name__)

# 近隣エリアのグループ定義 (location soft-match 用)
_STATION_GROUPS: dict[str, set[str]] = {
    "恵比寿": {"恵比寿", "代官山", "中目黒"},
    "代官山": {"代官山", "恵比寿", "中目黒"},
    "中目黒": {"中目黒", "代官山", "恵比寿"},
    "渋谷": {"渋谷", "表参道", "原宿", "恵比寿"},
    "新宿": {"新宿", "新宿三丁目", "代々木"},
}

# price_level → 概算上限のマッピング
_PRICE_LEVEL_MAX: dict[str, int] = {
    "low": 2000,
    "mid": 3500,
    "high": 8000,
}

# 固定の候補プール
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


def _matches_genre(tags: dict, genre: str | None) -> bool:
    if genre is None:
        return True
    tag_genre = tags.get("genre", "unknown")
    if tag_genre == "unknown":
        return False
    return tag_genre == genre


def _matches_location(tags: dict, location: str | None) -> bool:
    if location is None:
        return True
    tag_loc = tags.get("location", "unknown")
    if tag_loc == "unknown":
        return False
    if tag_loc == location:
        return True
    neighbors = _STATION_GROUPS.get(location, set())
    return tag_loc in neighbors


def _within_budget(tags: dict, max_price: int | None) -> bool:
    if max_price is None:
        return True
    price_level = tags.get("price_level", "unknown")
    if price_level == "unknown":
        return True
    approx_max = _PRICE_LEVEL_MAX.get(price_level)
    if approx_max is None:
        return True
    return approx_max <= max_price


def _format_result(place: dict) -> dict:
    return {
        "source": place["source"],
        "source_id": place["source_id"],
        "title": place["title"],
        "snippet": place["snippet"],
    }


def search_places(conditions: dict, *, enable_fallback: bool = True) -> dict:
    """Mock search: 条件に基づいて候補を絞り込んで返す。

    Returns:
        {
            "results": [...],
            "search_diagnostics": {
                "strict_conditions": {...},
                "fallback_enabled": bool,
                "fallback_applied": bool,
                "matched_stage": str,
                "fallback_steps": [...],
                "strict_result_count": int,
                "final_result_count": int,
            }
        }
    """
    genre = conditions.get("genre")
    location = conditions.get("location")
    max_price = conditions.get("max_price")

    strict_conditions = {
        k: v for k, v in [
            ("genre", genre), ("location", location), ("max_price", max_price),
        ] if v is not None
    }

    fallback_steps: list[str] = []

    # --- Stage 1: genre + location (strict) ---
    results = [
        p for p in _MOCK_PLACES
        if _matches_genre(p["_tags"], genre) and _matches_location(p["_tags"], location)
    ]
    strict_result_count = len(results)
    matched_stage = "genre+location"

    if results:
        # Strict hit — no fallback needed
        pass
    elif not enable_fallback:
        # Strict mode: return empty
        matched_stage = "strict_only"
    else:
        # --- Fallback ---
        fallback_steps.append("genre+location")

        # Stage 2: genre only
        if genre:
            results = [p for p in _MOCK_PLACES if _matches_genre(p["_tags"], genre)]
        if results:
            matched_stage = "genre_only"
        else:
            fallback_steps.append("genre_only")

            # Stage 3: location only
            if location:
                results = [p for p in _MOCK_PLACES if _matches_location(p["_tags"], location)]
            if results:
                matched_stage = "location_only"
            else:
                fallback_steps.append("location_only")

                # Stage 4: all
                results = list(_MOCK_PLACES)
                matched_stage = "all"
                fallback_steps.append("all")

    # --- Soft sort: budget-friendly first ---
    if max_price is not None and results:
        results.sort(key=lambda p: (
            0 if _within_budget(p["_tags"], max_price) else 1
        ))

    fallback_applied = len(fallback_steps) > 0
    formatted = [_format_result(p) for p in results]

    diagnostics = {
        "strict_conditions": strict_conditions,
        "fallback_enabled": enable_fallback,
        "fallback_applied": fallback_applied,
        "matched_stage": matched_stage,
        "fallback_steps": fallback_steps,
        "strict_result_count": strict_result_count,
        "final_result_count": len(formatted),
    }

    logger.info(
        "Search [%s]: strict=%d final=%d fallback=%s",
        matched_stage, strict_result_count, len(formatted), fallback_applied,
    )
    return {"results": formatted, "search_diagnostics": diagnostics}
