"""Query understanding: ユーザーの自然文から検索条件を抽出する。"""

import json
import logging
import re

logger = logging.getLogger(__name__)


def infer_search_conditions(query: str) -> dict:
    """Restaurant 用検索条件を抽出する。

    簡易ルールベース実装。不明な項目は含めない。

    Returns:
        {"location": ..., "genre": ..., "max_price": ..., "atmosphere": ...}
        各キーは推定できた場合のみ存在する。
    """
    conditions: dict = {}

    # --- location ---
    # 「〜で」「〜の」「〜周辺」「〜エリア」「〜駅」パターン
    loc_match = re.search(
        r"([\u4e00-\u9fff\u3040-\u309f\u30a0-\u30ffA-Za-z]+)"
        r"(?:駅|エリア|周辺|付近)?で",
        query,
    )
    if loc_match:
        conditions["location"] = loc_match.group(1)

    # --- genre ---
    genre_map = {
        "イタリアン": "italian",
        "イタリア料理": "italian",
        "フレンチ": "french",
        "フランス料理": "french",
        "和食": "japanese",
        "日本料理": "japanese",
        "中華": "chinese",
        "中国料理": "chinese",
        "寿司": "sushi",
        "鮨": "sushi",
        "焼肉": "yakiniku",
        "ラーメン": "ramen",
        "居酒屋": "izakaya",
        "カフェ": "cafe",
        "ビストロ": "bistro",
    }
    for keyword, genre in genre_map.items():
        if keyword in query:
            conditions["genre"] = genre
            break

    # --- max_price ---
    price_match = re.search(r"(\d[\d,]*)円以内", query)
    if not price_match:
        price_match = re.search(r"予算[はが]?(\d[\d,]*)円", query)
    if price_match:
        conditions["max_price"] = int(price_match.group(1).replace(",", ""))

    # --- atmosphere ---
    atmosphere_keywords = {
        "静か": "quiet",
        "落ち着": "quiet",
        "おしゃれ": "stylish",
        "カジュアル": "casual",
        "賑やか": "lively",
        "個室": "private_room",
        "デート": "date",
        "話せる": "quiet",
    }
    for keyword, atmo in atmosphere_keywords.items():
        if keyword in query:
            conditions["atmosphere"] = atmo
            break

    logger.info("Inferred search conditions: %s", conditions)
    return conditions
