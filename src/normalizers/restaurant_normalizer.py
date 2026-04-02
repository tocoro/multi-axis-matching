"""Restaurant normalizer: raw_record → evaluate() 用 candidate 変換。

mock raw_record と Google Places raw_record の両方に対応する。

## 変換規約 (Conversion Contract)

### Direct mapping (直接転写)
  raw.name           → title
  raw.review_summary → structured_attributes.review_summary  (mock path)
  raw.editorial_summary → structured_attributes.review_summary  (Google path)
  raw.nearest_station → structured_attributes.nearest_station  (mock path のみ)
  raw.rating         → structured_attributes.rating
  raw.user_rating_count → structured_attributes.user_rating_count
  raw.opening_hours_text → structured_attributes.opening_hours
  raw.website_url    → source_metadata.website_url
  raw.maps_url       → source_metadata.google_maps_url

### Approximate mapping (近似変換)
  raw.price_text     → (price_min, price_max)  正規表現で数値抽出
  raw.price_level    → (price_min, price_max)  enum → 概算レンジ (厳密価格ではない)
  raw.category       → genre  日本語ジャンル名 or primaryType の軽い正規化

### Lexical inference (語彙ベース推定)
  raw.atmosphere_text    → atmosphere_tags  明示語ヒット時のみ
  raw.editorial_summary  → atmosphere_tags  明示語ヒット時のみ
  ※語彙がなければ atmosphere_tags は設定しない (空リストも設定しない)

### Unknown / not inferred (推測しない)
  nearest_station  Google Places からは取得不可。推測しない。未設定。
  atmosphere_tags  語彙ヒットがなければ未設定
  genre            未知の primaryType はそのまま低加工で残す (過剰変換しない)
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

# Google Places priceLevel → 概算価格レンジ (厳密価格ではない)
_PRICE_LEVEL_RANGES: dict[str, tuple[int, int]] = {
    "PRICE_LEVEL_FREE": (0, 0),
    "PRICE_LEVEL_INEXPENSIVE": (500, 1500),
    "PRICE_LEVEL_MODERATE": (1500, 3500),
    "PRICE_LEVEL_EXPENSIVE": (3500, 8000),
    "PRICE_LEVEL_VERY_EXPENSIVE": (8000, 15000),
}

_ATMOSPHERE_KEYWORDS: dict[str, list[str]] = {
    "quiet": ["静か", "落ち着", "隠れ家", "calm", "quiet"],
    "lively": ["賑やか", "活気", "ワイワイ", "lively"],
    "casual": ["カジュアル", "casual"],
    "stylish": ["おしゃれ", "スタイリッシュ", "stylish"],
}


# ---------------------------------------------------------------------------
# Price helpers
# ---------------------------------------------------------------------------

def _parse_price_text(price_text: str | None) -> tuple[int | None, int | None]:
    """mock path: 価格テキストから (min, max) を抽出する。"""
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
    """Google path: priceLevel enum → 概算 (min, max)。未知 enum は (None, None)。"""
    if not price_level:
        return None, None
    r = _PRICE_LEVEL_RANGES.get(price_level)
    if r is None:
        return None, None
    return r


def _resolve_price(raw: dict) -> tuple[int | None, int | None]:
    """mock の price_text → Google の price_level の順で解決する。"""
    price_min, price_max = _parse_price_text(raw.get("price_text"))
    if price_min is not None or price_max is not None:
        return price_min, price_max
    return _parse_price_level(raw.get("price_level"))


# ---------------------------------------------------------------------------
# Genre helper
# ---------------------------------------------------------------------------

def _normalize_genre(category: str | None) -> str | None:
    """category → genre。未知の type はそのまま低加工で残す。"""
    if not category:
        return None
    if category in _GENRE_MAP:
        return _GENRE_MAP[category]
    # Google Places primaryType: "italian_restaurant" → "italian"
    normalized = category.replace("_restaurant", "").replace("_", " ")
    return normalized


# ---------------------------------------------------------------------------
# Atmosphere helper
# ---------------------------------------------------------------------------

def _infer_atmosphere_tags(text: str) -> list[str]:
    """明示語ヒット時のみタグを返す。語彙がなければ空リスト。"""
    tags = []
    for tag, keywords in _ATMOSPHERE_KEYWORDS.items():
        if any(w in text for w in keywords):
            tags.append(tag)
    return tags


def _extract_atmosphere_tags(raw: dict) -> list[str] | None:
    """atmosphere_text / editorial_summary から atmosphere_tags を推定する。

    語彙ヒットがなければ None を返す (空リストではなく設定しない)。
    """
    texts = []
    if raw.get("atmosphere_text"):
        texts.append(raw["atmosphere_text"])
    if raw.get("editorial_summary"):
        texts.append(raw["editorial_summary"])
    if not texts:
        return None
    tags = _infer_atmosphere_tags(" ".join(texts))
    return tags if tags else None


# ---------------------------------------------------------------------------
# Review summary helper
# ---------------------------------------------------------------------------

def _extract_review_summary(raw: dict) -> str | None:
    """review_summary (mock) or editorial_summary (Google) を返す。"""
    if raw.get("review_summary"):
        return raw["review_summary"]
    if raw.get("editorial_summary"):
        return raw["editorial_summary"]
    return None


# ---------------------------------------------------------------------------
# Source metadata helper
# ---------------------------------------------------------------------------

def _extract_source_metadata(raw: dict, source: str) -> dict:
    """source_metadata を構築する。raw 由来の追跡情報を含む。"""
    meta: dict = {"raw_source": source}
    if raw.get("website_url"):
        meta["website_url"] = raw["website_url"]
    if raw.get("maps_url"):
        meta["google_maps_url"] = raw["maps_url"]
    # raw 追跡: normalized candidate が何を元に作られたか辿るための情報
    if raw.get("category"):
        meta["place_category_raw"] = raw["category"]
    if raw.get("price_level"):
        meta["price_level_raw"] = raw["price_level"]
    if raw.get("price_text"):
        meta["price_text_raw"] = raw["price_text"]
    if raw.get("editorial_summary"):
        meta["editorial_summary_raw"] = raw["editorial_summary"]
    return meta


# ---------------------------------------------------------------------------
# Description builder
# ---------------------------------------------------------------------------

def _build_description(raw: dict) -> str:
    """raw_record から自然文の description を構築する。"""
    parts = []
    if raw.get("nearest_station"):
        parts.append(f"{raw['nearest_station']}駅")
    elif raw.get("address"):
        parts.append(raw["address"])
    if raw.get("atmosphere_text"):
        parts.append(raw["atmosphere_text"])
    if raw.get("editorial_summary"):
        parts.append(raw["editorial_summary"])
    if raw.get("category"):
        parts.append(raw["category"].replace("_", " "))
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


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def normalize_restaurant(retrieved: dict) -> dict:
    """retrieve 結果を evaluate() の candidate 形式に変換する。

    不明な情報は埋めない。mock と Google Places の両方の raw_record に対応。
    変換規約はモジュール docstring を参照。
    """
    raw = retrieved["raw_record"]
    source_id = retrieved["source_id"]
    source = retrieved["source"]

    price_min, price_max = _resolve_price(raw)
    genre = _normalize_genre(raw.get("category"))

    # structured_attributes: 値がある項目のみ設定
    attrs: dict = {"domain": "restaurant", "source": source}
    if genre:
        attrs["genre"] = genre
    # nearest_station: mock path のみ。Google Places からは取得不可、推測しない。
    if raw.get("nearest_station"):
        attrs["nearest_station"] = raw["nearest_station"]
    if price_min is not None:
        attrs["price_min"] = price_min
    if price_max is not None:
        attrs["price_max"] = price_max
    # atmosphere_tags: 語彙ヒット時のみ設定
    atmo_tags = _extract_atmosphere_tags(raw)
    if atmo_tags:
        attrs["atmosphere_tags"] = atmo_tags
    # review_summary: direct transcription
    review = _extract_review_summary(raw)
    if review:
        attrs["review_summary"] = review
    if raw.get("rating") is not None:
        attrs["rating"] = raw["rating"]
    if raw.get("user_rating_count") is not None:
        attrs["user_rating_count"] = raw["user_rating_count"]
    if raw.get("opening_hours_text"):
        attrs["opening_hours"] = raw["opening_hours_text"]

    candidate = {
        "candidate_id": source_id,
        "title": raw.get("name", source_id),
        "description": _build_description(raw),
        "structured_attributes": attrs,
        "source_metadata": _extract_source_metadata(raw, source),
    }

    logger.info("Normalized %s: %d structured attrs", source_id, len(attrs))
    return candidate
