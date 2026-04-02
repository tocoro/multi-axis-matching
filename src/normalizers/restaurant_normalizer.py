"""Restaurant normalizer: raw_record を evaluate() 用の candidate 形式に変換する。

mock raw_record と Google Places raw_record の両方に対応する。
"""

import logging
import re

logger = logging.getLogger(__name__)

_GENRE_MAP = {
    "イタリアン": "italian",
    "イタリア料理": "italian",
    "フレンチ": "french",
    "フランス料理": "french",
    "和食": "japanese",
    "日本料理": "japanese",
    "中華": "chinese",
    "バー": "bar",
    "カフェ": "cafe",
    "居酒屋": "izakaya",
    "ビストロ": "bistro",
}

# Google Places priceLevel → 概算価格レンジ
_PRICE_LEVEL_RANGES: dict[str, tuple[int, int]] = {
    "PRICE_LEVEL_FREE": (0, 0),
    "PRICE_LEVEL_INEXPENSIVE": (500, 1500),
    "PRICE_LEVEL_MODERATE": (1500, 3500),
    "PRICE_LEVEL_EXPENSIVE": (3500, 8000),
    "PRICE_LEVEL_VERY_EXPENSIVE": (8000, 15000),
}


def _parse_price_text(price_text: str | None) -> tuple[int | None, int | None]:
    """価格テキストから (min, max) を抽出する。"""
    if not price_text:
        return None, None
    numbers = re.findall(r"[\d,]+", price_text)
    nums = [int(n.replace(",", "")) for n in numbers]
    if len(nums) >= 2:
        return min(nums), max(nums)
    if len(nums) == 1:
        return None, nums[0]
    return None, None


def _parse_price_level(price_level: str | None) -> tuple[int | None, int | None]:
    """Google Places の priceLevel enum から (min, max) を返す。"""
    if not price_level:
        return None, None
    r = _PRICE_LEVEL_RANGES.get(price_level)
    if r is None:
        return None, None
    return r


def _normalize_genre(category: str | None) -> str | None:
    if not category:
        return None
    # Google Places の primaryType (e.g. "italian_restaurant") → genre
    normalized = category.replace("_restaurant", "").replace("_", " ")
    return _GENRE_MAP.get(category, normalized)


def _build_description(raw: dict) -> str:
    """raw_record から自然文の description を構築する。"""
    parts = []
    if raw.get("nearest_station"):
        parts.append(f"{raw['nearest_station']}駅")
    if raw.get("address"):
        # Google Places は address を持つ
        if not raw.get("nearest_station"):
            parts.append(raw["address"])
    if raw.get("atmosphere_text"):
        parts.append(raw["atmosphere_text"])
    if raw.get("editorial_summary"):
        parts.append(raw["editorial_summary"])
    if raw.get("category"):
        parts.append(raw["category"].replace("_", " "))
    # price_text (mock) or price_level (Google)
    price_min, price_max = _resolve_price(raw)
    if price_min and price_max:
        parts.append(f"平均予算{(price_min + price_max) // 2}円")
    elif price_max:
        parts.append(f"予算{price_max}円程度")
    if raw.get("rating"):
        parts.append(f"rating {raw['rating']}")
    name = raw.get("name", "")
    if parts:
        return f"{name}。{'。'.join(parts)}。"
    return name


def _resolve_price(raw: dict) -> tuple[int | None, int | None]:
    """mock の price_text または Google の price_level から価格レンジを返す。"""
    # mock path
    price_min, price_max = _parse_price_text(raw.get("price_text"))
    if price_min is not None or price_max is not None:
        return price_min, price_max
    # Google Places path
    return _parse_price_level(raw.get("price_level"))


def normalize_restaurant(retrieved: dict) -> dict:
    """retrieve 結果を evaluate() の candidate 形式に変換する。

    不明な情報は埋めない。mock と Google Places の両方の raw_record に対応。
    """
    raw = retrieved["raw_record"]
    source_id = retrieved["source_id"]

    price_min, price_max = _resolve_price(raw)
    genre = _normalize_genre(raw.get("category"))

    # structured_attributes: 値がある項目のみ
    attrs: dict = {"domain": "restaurant", "source": retrieved["source"]}
    if genre:
        attrs["genre"] = genre
    if raw.get("nearest_station"):
        attrs["nearest_station"] = raw["nearest_station"]
    if price_min is not None:
        attrs["price_min"] = price_min
    if price_max is not None:
        attrs["price_max"] = price_max
    if raw.get("atmosphere_text"):
        attrs["atmosphere_tags"] = _infer_atmosphere_tags(raw["atmosphere_text"])
    if raw.get("editorial_summary"):
        attrs["atmosphere_tags"] = _infer_atmosphere_tags(raw["editorial_summary"])
        attrs["review_summary"] = raw["editorial_summary"]
    if raw.get("review_summary"):
        attrs["review_summary"] = raw["review_summary"]
    if raw.get("rating") is not None:
        attrs["rating"] = raw["rating"]
    if raw.get("user_rating_count") is not None:
        attrs["user_rating_count"] = raw["user_rating_count"]
    if raw.get("opening_hours_text"):
        attrs["opening_hours"] = raw["opening_hours_text"]

    source_metadata: dict = {"raw_source": retrieved["source"]}
    if raw.get("website_url"):
        source_metadata["website_url"] = raw["website_url"]
    if raw.get("maps_url"):
        source_metadata["google_maps_url"] = raw["maps_url"]

    candidate = {
        "candidate_id": source_id,
        "title": raw.get("name", source_id),
        "description": _build_description(raw),
        "structured_attributes": attrs,
        "source_metadata": source_metadata,
    }

    logger.info("Normalized %s: %d structured attrs", source_id, len(attrs))
    return candidate


def _infer_atmosphere_tags(text: str) -> list[str]:
    tags = []
    if any(w in text for w in ("静か", "落ち着", "隠れ家", "calm", "quiet")):
        tags.append("quiet")
    if any(w in text for w in ("賑やか", "活気", "ワイワイ", "lively")):
        tags.append("lively")
    if any(w in text for w in ("カジュアル", "casual")):
        tags.append("casual")
    if any(w in text for w in ("おしゃれ", "スタイリッシュ", "stylish")):
        tags.append("stylish")
    return tags
