"""Restaurant pipeline: query → search → retrieve → normalize → evaluate."""

import logging

from src.evaluator import evaluate
from src.normalizers.restaurant_normalizer import normalize_restaurant
from src.retrievers.place_retriever import retrieve_place
from src.searchers.place_searcher import search_places
from src.services.infer_search_conditions import infer_search_conditions

logger = logging.getLogger(__name__)


def run_restaurant_pipeline(request_id: str, user_query: str) -> dict:
    """Restaurant パイプラインを実行する。

    Args:
        request_id: リクエスト識別子
        user_query: ユーザーの自然文クエリ

    Returns:
        evaluate() の response schema に準拠した dict。
    """
    logger.info("=== Pipeline started: %s ===", request_id)

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
        search_results = search_places(conditions)
    except Exception:
        logger.exception("Failed at stage 2: search")
        raise
    logger.info("  found %d candidates", len(search_results))

    # --- Stage 3: retrieve ---
    logger.info("[3/5] Retrieve")
    retrieved = []
    for sr in search_results:
        try:
            detail = retrieve_place(sr["source"], sr["source_id"])
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

    logger.info("=== Pipeline complete: %d candidates ranked ===",
                len(response["ranking"]))
    return response
