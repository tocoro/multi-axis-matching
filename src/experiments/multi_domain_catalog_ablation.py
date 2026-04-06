"""Multi-domain solution catalog ablation: restaurant + clinic を同一形式で比較する。"""

import logging
from unittest.mock import patch

from src.experiments.catalog_ablation import _compute_diff
from src.pipeline.clinic_pipeline import run_clinic_pipeline
from src.pipeline.restaurant_pipeline import run_restaurant_pipeline

logger = logging.getLogger(__name__)


def run_multi_domain_ablation(
    cases: list[dict],
    *,
    llm_mock_fn,
) -> dict:
    """複数ドメインの catalog on/off を比較する。

    Args:
        cases: [{"domain": "restaurant", "query": "...", "request_id": "..."}, ...]
        llm_mock_fn: LLM mock side_effect 関数

    Returns:
        {"runs": [...], "cross_domain_summary": {...}}
    """
    runs = []

    for case in cases:
        domain = case["domain"]
        query = case["query"]
        rid = case.get("request_id", f"md-{domain}")

        pipeline_fn = {
            "restaurant": run_restaurant_pipeline,
            "clinic": run_clinic_pipeline,
        }.get(domain)

        if pipeline_fn is None:
            logger.warning("Unknown domain: %s, skipping", domain)
            continue

        # With catalog
        with patch("src.evaluator.call_llm", side_effect=llm_mock_fn):
            with_result = pipeline_fn(f"{rid}-with", query)

        # Without catalog
        with patch("src.evaluator.call_llm", side_effect=llm_mock_fn):
            without_result = pipeline_fn(
                f"{rid}-without", query,
                catalog_path="/nonexistent/__no_catalog__.json",
            )

        diff = _compute_diff(with_result, without_result)

        runs.append({
            "domain": domain,
            "query": query,
            "with_catalog": with_result,
            "without_catalog": without_result,
            "diff_summary": diff,
        })

    # Cross-domain summary
    cross = _build_cross_domain_summary(runs)

    return {"runs": runs, "cross_domain_summary": cross}


def _build_cross_domain_summary(runs: list[dict]) -> dict:
    domains = [r["domain"] for r in runs]
    ranking_changed = [r["domain"] for r in runs if r["diff_summary"]["ranking_changed"]]
    reason_changed = [
        r["domain"] for r in runs if r["diff_summary"]["reason_changes"]
    ]
    score_changed = [
        r["domain"] for r in runs if r["diff_summary"]["score_changes"]
    ]
    unknown_reduced = [
        r["domain"] for r in runs
        if any(
            v.get("with", 0) < v.get("without", 0)
            for v in r["diff_summary"]["unknown_changes"].values()
        )
    ]

    return {
        "domains_compared": domains,
        "ranking_changed_domains": ranking_changed,
        "reason_changed_domains": reason_changed,
        "score_changed_domains": score_changed,
        "unknown_reduced_domains": unknown_reduced,
    }
