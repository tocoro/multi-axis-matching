"""Mock place search: 検索条件から候補サマリを返す。

フィルタ方針:
  Hard filter — genre, location が明確に不一致なら除外
  Soft filter — max_price は優先度付けに使用 (除外しない)
  Fallback   — 0 件時は段階的に条件緩和
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
    """genre が一致するか。unknown タグは不一致扱い。"""
    if genre is None:
        return True
    tag_genre = tags.get("genre", "unknown")
    if tag_genre == "unknown":
        return False
    return tag_genre == genre


def _matches_location(tags: dict, location: str | None) -> bool:
    """location が一致 or 近隣エリアか。unknown タグは不一致扱い。"""
    if location is None:
        return True
    tag_loc = tags.get("location", "unknown")
    if tag_loc == "unknown":
        return False
    if tag_loc == location:
        return True
    # 近隣エリアチェック
    neighbors = _STATION_GROUPS.get(location, set())
    return tag_loc in neighbors


def _within_budget(tags: dict, max_price: int | None) -> bool:
    """price_level が予算内か。unknown は判定不能 → True (除外しない)。"""
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


def search_places(conditions: dict) -> list[dict]:
    """Mock search: 条件に基づいて候補を絞り込んで返す。

    Filtering strategy:
      1. genre + location (hard) で絞る
      2. 0 件なら genre のみで絞る
      3. 0 件なら location のみで絞る
      4. 0 件なら全件返す

    max_price は hard filter ではなく、結果内のソート優先度に使う。
    """
    genre = conditions.get("genre")
    location = conditions.get("location")
    max_price = conditions.get("max_price")

    # --- Stage 1: genre + location ---
    results = [
        p for p in _MOCK_PLACES
        if _matches_genre(p["_tags"], genre) and _matches_location(p["_tags"], location)
    ]
    filter_desc = f"genre={genre} + location={location}"

    # --- Fallback stages ---
    if not results and genre:
        results = [p for p in _MOCK_PLACES if _matches_genre(p["_tags"], genre)]
        filter_desc = f"genre={genre} only (location relaxed)"

    if not results and location:
        results = [p for p in _MOCK_PLACES if _matches_location(p["_tags"], location)]
        filter_desc = f"location={location} only (genre relaxed)"

    if not results:
        results = list(_MOCK_PLACES)
        filter_desc = "fallback: all candidates"

    # --- Soft sort: budget-friendly first ---
    if max_price is not None:
        results.sort(key=lambda p: (
            0 if _within_budget(p["_tags"], max_price) else 1
        ))

    formatted = [_format_result(p) for p in results]
    logger.info("Search [%s]: %d candidates", filter_desc, len(formatted))
    return formatted
