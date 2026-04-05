"""Clinic pipeline: query → search → retrieve → normalize → evaluate.

NOTE: 2ドメイン目の demo 用最小実装。本格医療検索を目的としていません。
共通 evaluator / aggregation カーネルの再利用を示すための実装です。
"""

from __future__ import annotations

import logging

from src.adapters.clinic.mock_clinic import MockClinicRetriever, MockClinicSearcher
from src.evaluator import evaluate
from src.normalizers.clinic_normalizer import normalize_clinic

logger = logging.getLogger(__name__)

DEFAULT_MAX_RETRIEVE = 4


def run_clinic_pipeline(
    request_id: str,
    user_query: str,
    *,
    enable_fallback: bool = True,
    place_searcher=None,
    place_retriever=None,
    max_retrieve: int = DEFAULT_MAX_RETRIEVE,
) -> dict:
    """Clinic パイプラインを実行する。

    共通 evaluator を再利用し、clinic ドメインの candidate を評価する。
    """
    searcher = place_searcher or MockClinicSearcher()
    retriever = place_retriever or MockClinicRetriever()

    from src.domain.profiles import get_domain_profile
    profile = get_domain_profile("clinic")
    logger.info("=== Clinic pipeline started: %s (domain=%s, risk=%s) ===",
                request_id,
                profile.domain_name if profile else "unknown",
                profile.default_problem_type.risk_level if profile else "unknown")

    # --- Stage 1: query understanding (LLM に任せる、条件抽出は最小) ---
    conditions: dict = {}
    logger.info("[1/5] Query understanding (minimal)")

    # --- Stage 2: search ---
    logger.info("[2/5] Search")
    search_output = searcher.search_places(conditions, enable_fallback=enable_fallback)
    search_results = search_output["results"]
    search_diagnostics = search_output["search_diagnostics"]
    logger.info("  found %d candidates", len(search_results))

    if not search_results:
        return {
            "request_id": request_id,
            "search_diagnostics": search_diagnostics,
            "ranking": [],
        }

    # --- Stage 3: retrieve ---
    targets = search_results[:max_retrieve]
    logger.info("[3/5] Retrieve (top %d)", len(targets))
    retrieved = []
    for sr in targets:
        try:
            detail = retriever.retrieve_place(sr["source"], sr["source_id"])
            retrieved.append(detail)
        except Exception:
            logger.warning("Retrieve failed for %s, skipping", sr["source_id"],
                           exc_info=True)

    if not retrieved:
        return {
            "request_id": request_id,
            "search_diagnostics": search_diagnostics,
            "ranking": [],
        }

    # --- Stage 4: normalize ---
    logger.info("[4/5] Normalize")
    candidates = []
    for detail in retrieved:
        candidate = normalize_clinic(detail)
        candidates.append(candidate)
    logger.info("  normalized %d candidates", len(candidates))

    # --- Stage 5: evaluate (共通カーネル再利用) ---
    logger.info("[5/5] Evaluate")
    eval_request = {
        "request_id": request_id,
        "user_query": user_query,
        "candidates": candidates,
    }
    response = evaluate(eval_request)

    response["search_diagnostics"] = search_diagnostics
    response["candidate_sources"] = {c["candidate_id"]: c for c in candidates}

    if profile:
        response["domain_profile"] = {
            "domain": profile.domain_name,
            "risk_level": profile.default_problem_type.risk_level,
            "example_axes": profile.default_problem_type.example_axes,
        }

    logger.info("=== Clinic pipeline complete: %d ranked ===",
                len(response["ranking"]))
    return response
