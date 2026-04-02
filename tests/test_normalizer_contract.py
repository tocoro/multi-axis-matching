"""Normalizer conversion contract tests.

変換規約を固定し、推測範囲と unknown 範囲を明確にする。
"""

import pytest

from src.normalizers.restaurant_normalizer import (
    _extract_atmosphere_tags,
    _extract_review_summary,
    _extract_source_metadata,
    _normalize_genre,
    _parse_price_level,
    _parse_price_text,
    _resolve_price,
    normalize_restaurant,
)


# ===================================================================
# A. price_level 近似変換
# ===================================================================


class TestPriceLevelContract:
    def test_moderate(self):
        assert _parse_price_level("PRICE_LEVEL_MODERATE") == (1500, 3500)

    def test_inexpensive(self):
        assert _parse_price_level("PRICE_LEVEL_INEXPENSIVE") == (500, 1500)

    def test_expensive(self):
        assert _parse_price_level("PRICE_LEVEL_EXPENSIVE") == (3500, 8000)

    def test_free(self):
        assert _parse_price_level("PRICE_LEVEL_FREE") == (0, 0)

    def test_unknown_enum(self):
        assert _parse_price_level("PRICE_LEVEL_UNKNOWN") == (None, None)

    def test_none(self):
        assert _parse_price_level(None) == (None, None)

    def test_resolve_prefers_price_text(self):
        """price_text と price_level が両方あれば price_text が優先。"""
        raw = {"price_text": "￥2,000〜￥3,000", "price_level": "PRICE_LEVEL_EXPENSIVE"}
        assert _resolve_price(raw) == (2000, 3000)

    def test_resolve_falls_back_to_price_level(self):
        raw = {"price_level": "PRICE_LEVEL_MODERATE"}
        assert _resolve_price(raw) == (1500, 3500)


# ===================================================================
# B. editorial_summary の扱い
# ===================================================================


class TestEditorialSummaryContract:
    def test_review_summary_from_editorial(self):
        raw = {"editorial_summary": "落ち着いた雰囲気の本格イタリアン"}
        assert _extract_review_summary(raw) == "落ち着いた雰囲気の本格イタリアン"

    def test_review_summary_from_mock(self):
        raw = {"review_summary": "会話しやすい"}
        assert _extract_review_summary(raw) == "会話しやすい"

    def test_mock_review_takes_precedence(self):
        """review_summary (mock) が editorial_summary より優先。"""
        raw = {"review_summary": "mock review", "editorial_summary": "google review"}
        assert _extract_review_summary(raw) == "mock review"

    def test_atmosphere_tags_from_editorial_with_keyword(self):
        raw = {"editorial_summary": "落ち着いた雰囲気の本格イタリアン"}
        tags = _extract_atmosphere_tags(raw)
        assert tags is not None
        assert "quiet" in tags

    def test_atmosphere_tags_none_without_keyword(self):
        """語彙ヒットなし → None (空リストではない)。"""
        raw = {"editorial_summary": "美味しいイタリアン"}
        tags = _extract_atmosphere_tags(raw)
        assert tags is None

    def test_atmosphere_tags_none_without_text(self):
        raw = {}
        assert _extract_atmosphere_tags(raw) is None

    def test_atmosphere_from_atmosphere_text(self):
        raw = {"atmosphere_text": "静かで落ち着いた雰囲気"}
        tags = _extract_atmosphere_tags(raw)
        assert "quiet" in tags

    def test_atmosphere_combines_both_sources(self):
        """atmosphere_text と editorial_summary の両方を見る。"""
        raw = {"atmosphere_text": "カジュアル", "editorial_summary": "静かなお店"}
        tags = _extract_atmosphere_tags(raw)
        assert "casual" in tags
        assert "quiet" in tags


# ===================================================================
# C. nearest_station を推測しない
# ===================================================================


class TestNearestStationContract:
    def test_google_raw_no_nearest_station(self):
        """Google raw_record に nearest_station がない → 設定しない。"""
        retrieved = {
            "source": "google_places",
            "source_id": "ChIJ_x",
            "raw_record": {
                "name": "Test",
                "address": "東京都渋谷区恵比寿1-2-3",
                "category": "italian_restaurant",
            },
        }
        c = normalize_restaurant(retrieved)
        assert "nearest_station" not in c["structured_attributes"]

    def test_mock_raw_with_nearest_station(self):
        """mock raw_record に nearest_station がある → 設定する。"""
        retrieved = {
            "source": "place_search",
            "source_id": "p1",
            "raw_record": {
                "name": "Test",
                "nearest_station": "恵比寿",
            },
        }
        c = normalize_restaurant(retrieved)
        assert c["structured_attributes"]["nearest_station"] == "恵比寿"


# ===================================================================
# D. genre 正規化
# ===================================================================


class TestGenreContract:
    def test_japanese_genre(self):
        assert _normalize_genre("イタリアン") == "italian"

    def test_google_primary_type(self):
        assert _normalize_genre("italian_restaurant") == "italian"

    def test_google_type_without_restaurant_suffix(self):
        assert _normalize_genre("cafe") == "cafe"

    def test_unknown_type_low_processing(self):
        """未知 type は過剰変換せず、低加工で残す。"""
        assert _normalize_genre("ramen_restaurant") == "ramen"

    def test_unknown_type_with_underscore(self):
        assert _normalize_genre("sea_food") == "sea food"

    def test_none(self):
        assert _normalize_genre(None) is None


# ===================================================================
# E. source_metadata 追跡
# ===================================================================


class TestSourceMetadataContract:
    def test_google_source_metadata(self):
        raw = {
            "category": "italian_restaurant",
            "price_level": "PRICE_LEVEL_MODERATE",
            "editorial_summary": "落ち着いた雰囲気",
            "website_url": "https://example.com",
            "maps_url": "https://maps.google.com/x",
        }
        meta = _extract_source_metadata(raw, "google_places")
        assert meta["raw_source"] == "google_places"
        assert meta["place_category_raw"] == "italian_restaurant"
        assert meta["price_level_raw"] == "PRICE_LEVEL_MODERATE"
        assert meta["editorial_summary_raw"] == "落ち着いた雰囲気"
        assert meta["website_url"] == "https://example.com"
        assert meta["google_maps_url"] == "https://maps.google.com/x"

    def test_mock_source_metadata(self):
        raw = {
            "category": "イタリアン",
            "price_text": "￥2,000〜￥3,000",
        }
        meta = _extract_source_metadata(raw, "place_search")
        assert meta["raw_source"] == "place_search"
        assert meta["place_category_raw"] == "イタリアン"
        assert meta["price_text_raw"] == "￥2,000〜￥3,000"
        assert "price_level_raw" not in meta
        assert "editorial_summary_raw" not in meta

    def test_minimal_metadata(self):
        meta = _extract_source_metadata({}, "place_search")
        assert meta == {"raw_source": "place_search"}


# ===================================================================
# F. mock path を壊さない (integration)
# ===================================================================


class TestMockPathIntact:
    def test_full_mock_record(self):
        retrieved = {
            "source": "place_search",
            "source_id": "place_1",
            "raw_record": {
                "name": "Trattoria A",
                "address": "東京都渋谷区恵比寿南1-2-3",
                "nearest_station": "恵比寿",
                "price_text": "￥2,000〜￥3,000",
                "category": "イタリアン",
                "atmosphere_text": "静かで落ち着いた雰囲気",
                "review_summary": "会話しやすい",
            },
        }
        c = normalize_restaurant(retrieved)
        attrs = c["structured_attributes"]
        assert attrs["genre"] == "italian"
        assert attrs["nearest_station"] == "恵比寿"
        assert attrs["price_min"] == 2000
        assert attrs["price_max"] == 3000
        assert "quiet" in attrs["atmosphere_tags"]
        assert attrs["review_summary"] == "会話しやすい"

    def test_google_record(self):
        retrieved = {
            "source": "google_places",
            "source_id": "ChIJ_abc",
            "raw_record": {
                "name": "Trattoria Real",
                "address": "東京都渋谷区恵比寿1-2-3",
                "category": "italian_restaurant",
                "price_level": "PRICE_LEVEL_MODERATE",
                "rating": 4.2,
                "user_rating_count": 128,
                "editorial_summary": "落ち着いた雰囲気の本格イタリアン",
                "website_url": "https://example.com",
                "maps_url": "https://maps.google.com/x",
            },
        }
        c = normalize_restaurant(retrieved)
        attrs = c["structured_attributes"]
        assert attrs["genre"] == "italian"
        assert "nearest_station" not in attrs  # Google path: 推測しない
        assert attrs["price_min"] == 1500
        assert attrs["price_max"] == 3500
        assert "quiet" in attrs["atmosphere_tags"]
        assert attrs["review_summary"] == "落ち着いた雰囲気の本格イタリアン"
        assert attrs["rating"] == 4.2
        # source_metadata に raw 追跡
        meta = c["source_metadata"]
        assert meta["place_category_raw"] == "italian_restaurant"
        assert meta["price_level_raw"] == "PRICE_LEVEL_MODERATE"
