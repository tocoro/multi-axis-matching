"""Solution Catalog ablation: catalog あり / なしの評価差分を比較する。"""

import json
import logging
from pathlib import Path
from unittest.mock import patch

from src.pipeline.restaurant_pipeline import run_restaurant_pipeline

logger = logging.getLogger(__name__)


def run_ablation(
    request_id: str,
    user_query: str,
    *,
    llm_mock_fn,
    catalog_path: str | Path | None = None,
    no_catalog_path: str = "/nonexistent/__no_catalog__.json",
    **pipeline_kwargs,
) -> dict:
    """同一条件で catalog あり / なしの評価を並行実行し差分を返す。

    Args:
        llm_mock_fn: LLM mock side_effect 関数
        catalog_path: catalog あり時のパス (None でデフォルト)
        no_catalog_path: catalog なし時のパス (存在しないパス)
    """
    # Condition A: with catalog
    with patch("src.evaluator.call_llm", side_effect=llm_mock_fn):
        result_with = run_restaurant_pipeline(
            f"{request_id}-with",
            user_query,
            catalog_path=catalog_path,
            **pipeline_kwargs,
        )

    # Condition B: without catalog
    with patch("src.evaluator.call_llm", side_effect=llm_mock_fn):
        result_without = run_restaurant_pipeline(
            f"{request_id}-without",
            user_query,
            catalog_path=no_catalog_path,
            **pipeline_kwargs,
        )

    diff = _compute_diff(result_with, result_without)

    return {
        "query": user_query,
        "with_catalog": result_with,
        "without_catalog": result_without,
        "diff_summary": diff,
    }


def _compute_diff(with_cat: dict, without_cat: dict) -> dict:
    """2つの結果から差分サマリーを構築する。"""
    ranking_with = {e["candidate_id"]: e for e in with_cat.get("ranking", [])}
    ranking_without = {e["candidate_id"]: e for e in without_cat.get("ranking", [])}

    order_with = [e["candidate_id"] for e in with_cat.get("ranking", [])]
    order_without = [e["candidate_id"] for e in without_cat.get("ranking", [])]

    confidence_changes = {}
    score_changes = {}
    unknown_changes = {}
    reason_changes = {}

    all_ids = set(ranking_with.keys()) | set(ranking_without.keys())

    for cid in all_ids:
        w = ranking_with.get(cid, {})
        wo = ranking_without.get(cid, {})

        # confidence
        conf_w = w.get("confidence")
        conf_wo = wo.get("confidence")
        if conf_w != conf_wo:
            confidence_changes[cid] = {"with": conf_w, "without": conf_wo}

        # total_score
        score_w = w.get("total_score")
        score_wo = wo.get("total_score")
        if score_w != score_wo:
            score_changes[cid] = {"with": score_w, "without": score_wo}

        # unknown count
        unk_w = sum(1 for a in w.get("axis_scores", []) if a.get("status") == "unknown")
        unk_wo = sum(1 for a in wo.get("axis_scores", []) if a.get("status") == "unknown")
        if unk_w != unk_wo:
            unknown_changes[cid] = {"with": unk_w, "without": unk_wo}

        # reason changes (axes where reason text differs)
        axes_w = {a["axis"]: a.get("reason", "") for a in w.get("axis_scores", [])}
        axes_wo = {a["axis"]: a.get("reason", "") for a in wo.get("axis_scores", [])}
        changed_axes = [
            axis for axis in set(axes_w) & set(axes_wo)
            if axes_w[axis] != axes_wo[axis]
        ]
        if changed_axes:
            reason_changes[cid] = changed_axes

    return {
        "ranking_changed": order_with != order_without,
        "score_changes": score_changes,
        "confidence_changes": confidence_changes,
        "unknown_changes": unknown_changes,
        "reason_changes": reason_changes,
    }
