"""Mock place search: 検索条件から候補サマリを返す。"""

import logging

logger = logging.getLogger(__name__)

# 固定の候補プール。条件に応じてフィルタして返す。
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


def search_places(conditions: dict) -> list[dict]:
    """Mock search: 条件に基づいて候補サマリを返す。

    実装は固定プールから全件返す。将来的に API に差し替える想定。
    """
    results = []
    for place in _MOCK_PLACES:
        entry = {
            "source": place["source"],
            "source_id": place["source_id"],
            "title": place["title"],
            "snippet": place["snippet"],
        }
        results.append(entry)

    logger.info("Search returned %d candidates", len(results))
    return results
