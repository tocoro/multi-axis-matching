"""Restaurant normalizer: raw_record を evaluate() 用の candidate 形式に変換する。"""

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


def _normalize_genre(category: str | None) -> str | None:
    if not category:
        return None
    return _GENRE_MAP.get(category, category.lower())


def _build_description(raw: dict) -> str:
    """raw_record から自然文の description を構築する。"""
    parts = []
    if raw.get("nearest_station"):
        parts.append(f"{raw['nearest_station']}駅")
    if raw.get("atmosphere_text"):
        parts.append(raw["atmosphere_text"])
    if raw.get("category"):
        parts.append(raw["category"])
    price_min, price_max = _parse_price_text(raw.get("price_text"))
    if price_min and price_max:
        parts.append(f"平均予算{(price_min + price_max) // 2}円")
    elif price_max:
        parts.append(f"予算{price_max}円程度")
    name = raw.get("name", "")
    if parts:
        return f"{name}。{'。'.join(parts)}。"
    return name


def normalize_restaurant(retrieved: dict) -> dict:
    """retrieve 結果を evaluate() の candidate 形式に変換する。

    不明な情報は埋めない。
    """
    raw = retrieved["raw_record"]
    source_id = retrieved["source_id"]

    price_min, price_max = _parse_price_text(raw.get("price_text"))
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
    if raw.get("review_summary"):
        attrs["review_summary"] = raw["review_summary"]

    candidate = {
        "candidate_id": source_id,
        "title": raw.get("name", source_id),
        "description": _build_description(raw),
        "structured_attributes": attrs,
        "source_metadata": {"raw_source": retrieved["source"]},
    }

    logger.info("Normalized %s: %d structured attrs", source_id, len(attrs))
    return candidate


def _infer_atmosphere_tags(text: str) -> list[str]:
    tags = []
    if any(w in text for w in ("静か", "落ち着", "隠れ家")):
        tags.append("quiet")
    if any(w in text for w in ("賑やか", "活気", "ワイワイ")):
        tags.append("lively")
    if any(w in text for w in ("カジュアル",)):
        tags.append("casual")
    if any(w in text for w in ("おしゃれ", "スタイリッシュ")):
        tags.append("stylish")
    return tags
