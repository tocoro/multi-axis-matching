"""Clinic normalizer: raw_record → evaluate() 用 candidate 変換。

NOTE: demo 用の最小実装。本格医療検索を目的としていません。
不明な情報は埋めない。
"""

import logging

logger = logging.getLogger(__name__)


def _build_description(raw: dict) -> str:
    parts = []
    if raw.get("nearest_station"):
        parts.append(f"{raw['nearest_station']}駅")
    if raw.get("specialties"):
        parts.append("・".join(raw["specialties"]))
    if raw.get("hours_text"):
        parts.append(raw["hours_text"])
    if raw.get("accepts_insurance") is True:
        parts.append("保険適用")
    name = raw.get("name", "")
    if parts:
        return f"{name}。{'。'.join(parts)}。"
    return name


def normalize_clinic(retrieved: dict) -> dict:
    """retrieve 結果を evaluate() の candidate 形式に変換する。"""
    raw = retrieved["raw_record"]
    source_id = retrieved["source_id"]

    attrs: dict = {"domain": "clinic", "source": retrieved["source"]}

    if raw.get("specialties"):
        attrs["specialties"] = raw["specialties"]
    if raw.get("nearest_station"):
        attrs["nearest_station"] = raw["nearest_station"]
    if raw.get("hours_text"):
        attrs["hours_text"] = raw["hours_text"]
    if raw.get("accepts_insurance") is not None:
        attrs["accepts_insurance"] = raw["accepts_insurance"]
    if raw.get("same_day_available") is not None:
        attrs["same_day_available"] = raw["same_day_available"]
    if raw.get("review_summary"):
        attrs["review_summary"] = raw["review_summary"]

    candidate = {
        "candidate_id": source_id,
        "title": raw.get("name", source_id),
        "description": _build_description(raw),
        "structured_attributes": attrs,
        "source_metadata": {"raw_source": retrieved["source"]},
    }

    logger.info("Normalized clinic %s: %d attrs", source_id, len(attrs))
    return candidate
