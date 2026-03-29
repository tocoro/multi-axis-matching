"""Mock place retrieve: source_id から詳細情報を返す。"""

import logging

logger = logging.getLogger(__name__)

# source_id → raw_record のマッピング。情報欠落の候補も含む。
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
        # 情報欠落が多い候補
        "name": "Restaurant D",
        "address": None,
        "nearest_station": None,
        "price_text": None,
        "category": None,
        "atmosphere_text": "落ち着いた雰囲気",
        "review_summary": None,
    },
}


def retrieve_place(source: str, source_id: str) -> dict:
    """Mock retrieve: source_id に対応する詳細レコードを返す。"""
    raw_record = _MOCK_DETAILS.get(source_id)
    if raw_record is None:
        logger.warning("No mock data for source_id=%s", source_id)
        raw_record = {"name": source_id}

    result = {
        "source": source,
        "source_id": source_id,
        "raw_record": raw_record,
    }
    logger.info("Retrieved details for %s: %d fields", source_id,
                sum(1 for v in raw_record.values() if v is not None))
    return result
