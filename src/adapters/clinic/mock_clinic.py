"""Mock clinic adapter: 固定候補プールによる deterministic 実装。

NOTE: 本格医療検索ではなく、2ドメイン目の demo 用 mock です。
医療助言を目的としていません。
"""

import logging

logger = logging.getLogger(__name__)

_MOCK_CLINICS = [
    {
        "source": "clinic_search",
        "source_id": "clinic_1",
        "title": "恵比寿ファミリークリニック",
        "snippet": "内科・一般診療。恵比寿駅徒歩2分。平日20時まで。保険適用",
        "_tags": {"specialty": "internal_medicine", "location": "恵比寿"},
    },
    {
        "source": "clinic_search",
        "source_id": "clinic_2",
        "title": "目黒内科・消化器クリニック",
        "snippet": "内科・消化器内科。目黒駅徒歩10分。平日18時まで",
        "_tags": {"specialty": "gastroenterology", "location": "目黒"},
    },
    {
        "source": "clinic_search",
        "source_id": "clinic_3",
        "title": "渋谷皮膚科クリニック",
        "snippet": "皮膚科専門。渋谷駅徒歩3分。平日19時まで。保険適用",
        "_tags": {"specialty": "dermatology", "location": "渋谷"},
    },
    {
        "source": "clinic_search",
        "source_id": "clinic_4",
        "title": "メディカルセンターD",
        "snippet": "診療所",
        "_tags": {"specialty": "unknown", "location": "unknown"},
    },
]

_MOCK_DETAILS: dict[str, dict] = {
    "clinic_1": {
        "name": "恵比寿ファミリークリニック",
        "address": "東京都渋谷区恵比寿南1-1-1",
        "nearest_station": "恵比寿",
        "specialties": ["internal_medicine", "general_practice"],
        "hours_text": "月-金 9:00-20:00 / 土 9:00-13:00 / 日祝休",
        "accepts_insurance": True,
        "same_day_available": True,
        "review_summary": "待ち時間が短く丁寧な対応",
    },
    "clinic_2": {
        "name": "目黒内科・消化器クリニック",
        "address": "東京都目黒区下目黒2-2-2",
        "nearest_station": "目黒",
        "specialties": ["internal_medicine", "gastroenterology"],
        "hours_text": "月-金 9:00-18:00 / 土日祝休",
        "accepts_insurance": True,
        "same_day_available": False,
        "review_summary": "消化器系に詳しい専門医",
    },
    "clinic_3": {
        "name": "渋谷皮膚科クリニック",
        "address": "東京都渋谷区渋谷3-3-3",
        "nearest_station": "渋谷",
        "specialties": ["dermatology"],
        "hours_text": "月-金 10:00-19:00 / 土 10:00-14:00 / 日祝休",
        "accepts_insurance": True,
        "same_day_available": True,
        "review_summary": "皮膚トラブルに定評あり",
    },
    "clinic_4": {
        "name": "メディカルセンターD",
        "address": None,
        "nearest_station": None,
        "specialties": None,
        "hours_text": None,
        "accepts_insurance": None,
        "same_day_available": None,
        "review_summary": None,
    },
}


class MockClinicSearcher:
    """Mock clinic search adapter."""

    def search_places(self, conditions: dict, *, enable_fallback: bool = True) -> dict:
        results = [
            {
                "source": c["source"],
                "source_id": c["source_id"],
                "title": c["title"],
                "snippet": c["snippet"],
            }
            for c in _MOCK_CLINICS
        ]
        logger.info("MockClinicSearch: %d candidates", len(results))
        return {
            "results": results,
            "search_diagnostics": {
                "strict_conditions": conditions,
                "fallback_enabled": enable_fallback,
                "fallback_applied": False,
                "matched_stage": "all",
                "fallback_steps": [],
                "strict_result_count": len(results),
                "final_result_count": len(results),
            },
        }


class MockClinicRetriever:
    """Mock clinic retrieve adapter."""

    def retrieve_place(self, source: str, source_id: str) -> dict:
        raw = _MOCK_DETAILS.get(source_id)
        if raw is None:
            raw = {"name": source_id}
        logger.info("MockClinicRetrieve %s: %d fields",
                     source_id, sum(1 for v in raw.values() if v is not None))
        return {"source": source, "source_id": source_id, "raw_record": raw}
