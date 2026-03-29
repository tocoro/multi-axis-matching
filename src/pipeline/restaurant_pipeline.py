"""Restaurant pipeline: query → search → retrieve → normalize → evaluate."""

from __future__ import annotations

import logging

from src.adapters.places.base import PlaceRetriever, PlaceSearcher
from src.adapters.places.mock_places import MockPlaceRetriever, MockPlaceSearcher
from src.evaluator import evaluate
from src.normalizers.restaurant_normalizer import normalize_restaurant
from src.services.infer_search_conditions import infer_search_conditions

logger = logging.getLogger(__name__)


def run_restaurant_pipeline(
    request_id: str,
    user_query: str,
    *,
    enable_fallback: bool = True,
    place_searcher: PlaceSearcher | None = None,
    place_retriever: PlaceRetriever | None = None,
) -> dict:
    """Restaurant パイプラインを実行する。

    Args:
        request_id: リクエスト識別子
        user_query: ユーザーの自然文クエリ
        enable_fallback: False で strict 検索 (fallback なし)
        place_searcher: 検索 adapter (None で MockPlaceSearcher)
        place_retriever: 詳細取得 adapter (None で MockPlaceRetriever)

    Returns:
        evaluate() の response に search_diagnostics を付加した dict。
    """
    searcher = place_searcher or MockPlaceSearcher()
    retriever = place_retriever or MockPlaceRetriever()

    logger.info("=== Pipeline started: %s (fallback=%s) ===",
                request_id, enable_fallback)

    # --- Stage 1: query understanding ---
    logger.info("[1/5] Query understanding")
    try:
        conditions = infer_search_conditions(user_query)
    except Exception:
        logger.exception("Failed at stage 1: query understanding")
        raise
    logger.info("  conditions: %s", conditions)

    # --- Stage 2: search ---
    logger.info("[2/5] Search")
    try:
        search_output = searcher.search_places(
            conditions, enable_fallback=enable_fallback)
    except Exception:
        logger.exception("Failed at stage 2: search")
        raise
    search_results = search_output["results"]
    search_diagnostics = search_output["search_diagnostics"]
    logger.info("  found %d candidates (stage=%s, fallback=%s)",
                len(search_results),
                search_diagnostics["matched_stage"],
                search_diagnostics["fallback_applied"])

    if not search_results:
        logger.warning("Search returned 0 candidates — returning empty response")
        return {
            "request_id": request_id,
            "search_diagnostics": search_diagnostics,
            "ranking": [],
        }

    # --- Stage 3: retrieve ---
    logger.info("[3/5] Retrieve")
    retrieved = []
    for sr in search_results:
        try:
            detail = retriever.retrieve_place(sr["source"], sr["source_id"])
            retrieved.append(detail)
        except Exception:
            logger.exception("Failed at stage 3: retrieve %s", sr["source_id"])
            raise
    logger.info("  retrieved %d details", len(retrieved))

    # --- Stage 4: normalize ---
    logger.info("[4/5] Normalize")
    candidates = []
    for detail in retrieved:
        try:
            candidate = normalize_restaurant(detail)
            candidates.append(candidate)
        except Exception:
            logger.exception("Failed at stage 4: normalize %s", detail["source_id"])
            raise
    logger.info("  normalized %d candidates", len(candidates))

    # --- Stage 5: evaluate ---
    logger.info("[5/5] Evaluate")
    eval_request = {
        "request_id": request_id,
        "user_query": user_query,
        "candidates": candidates,
    }
    try:
        response = evaluate(eval_request)
    except Exception:
        logger.exception("Failed at stage 5: evaluate")
        raise

    response["search_diagnostics"] = search_diagnostics

    logger.info("=== Pipeline complete: %d candidates ranked ===",
                len(response["ranking"]))
    return response
