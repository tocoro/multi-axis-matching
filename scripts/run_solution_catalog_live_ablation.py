#!/usr/bin/env python3
"""Solution Catalog live ablation: catalog on/off を live LLM で比較実行する。

Usage:
    python scripts/run_solution_catalog_live_ablation.py \
      --query "恵比寿で静かに話せるイタリアン。予算は3000円以内" \
      --model gemini-2.5-flash \
      --out artifacts/live_ablation_case1.json
"""

import argparse
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.experiments.catalog_ablation import _compute_diff  # noqa: E402
from src.pipeline.restaurant_pipeline import run_restaurant_pipeline  # noqa: E402

logger = logging.getLogger(__name__)


def run_live_ablation(
    query: str,
    model: str,
    request_id: str = "live-abl",
) -> dict:
    """Live LLM で catalog on/off を比較実行する。"""
    orig_model = os.environ.get("EVAL_MODEL")
    os.environ["EVAL_MODEL"] = model

    try:
        # Condition A: with catalog (default path)
        logger.info("Running WITH catalog...")
        with_result = run_restaurant_pipeline(f"{request_id}-with", query)

        # Condition B: without catalog
        logger.info("Running WITHOUT catalog...")
        without_result = run_restaurant_pipeline(
            f"{request_id}-without", query,
            catalog_path="/nonexistent/__no_catalog__.json",
        )
    finally:
        if orig_model is not None:
            os.environ["EVAL_MODEL"] = orig_model
        elif "EVAL_MODEL" in os.environ:
            del os.environ["EVAL_MODEL"]

    diff = _compute_diff(with_result, without_result)

    from src.experiments.review_summary import build_review_summary
    review = build_review_summary(with_result, without_result, diff)

    ts = datetime.now(timezone.utc).isoformat()

    return {
        "query": query,
        "model": model,
        "timestamp": ts,
        "with_catalog": with_result,
        "without_catalog": without_result,
        "diff_summary": diff,
        "review_summary": review,
        "run_metadata": {
            "query": query,
            "model": model,
            "timestamp": ts,
            "catalog_mode": "with_vs_without",
            "candidate_source": "unknown",
            "is_live_llm": True,
            "review_summary_version": 1,
        },
        "notes": {
            "run_purpose": "catalog live ablation",
            "interpretation_caution": "single run is not conclusive",
        },
    }


def build_artifact_index(result: dict, artifact_path: str = "") -> dict:
    """Full result から比較に必要な最小情報だけを抜き出した index を作る。"""
    with_ranking = result.get("with_catalog", {}).get("ranking", [])
    without_ranking = result.get("without_catalog", {}).get("ranking", [])

    return {
        "query": result.get("query", ""),
        "model": result.get("model", ""),
        "timestamp": result.get("timestamp", ""),
        "artifact_path": artifact_path,
        "catalog_mode": result.get("run_metadata", {}).get("catalog_mode", "with_vs_without"),
        "quick_verdict": result.get("review_summary", {}).get("quick_verdict", {}),
        "top_candidates": {
            "with_catalog": [e["candidate_id"] for e in with_ranking[:3]],
            "without_catalog": [e["candidate_id"] for e in without_ranking[:3]],
        },
    }


def build_artifact_directory_summary(index_items: list[dict]) -> dict:
    """複数の index dict から最小一覧 summary を作る。"""
    models = sorted(set(idx.get("model", "") for idx in index_items))
    queries_seen: list[str] = []
    for idx in index_items:
        q = idx.get("query", "")
        if q and q not in queries_seen:
            queries_seen.append(q)

    verdict_keys = [
        "reason_changed", "score_changed", "confidence_changed",
        "ranking_changed", "unknown_reduced", "disqualified_changed",
    ]
    verdict_counts = {k: 0 for k in verdict_keys}
    for idx in index_items:
        qv = idx.get("quick_verdict", {})
        for k in verdict_keys:
            if qv.get(k):
                verdict_counts[k] += 1

    artifacts = [
        {
            "artifact_path": idx.get("artifact_path", ""),
            "query": idx.get("query", ""),
            "model": idx.get("model", ""),
            "timestamp": idx.get("timestamp", ""),
            "quick_verdict": idx.get("quick_verdict", {}),
        }
        for idx in index_items
    ]

    # Trend summary
    dominant = sorted(
        [k for k in verdict_keys if verdict_counts[k] > 0],
        key=lambda k: (-verdict_counts[k], k),
    )
    stable = [k for k in verdict_keys if verdict_counts[k] == 0]

    return {
        "total_runs": len(index_items),
        "models": models,
        "queries": queries_seen,
        "verdict_counts": verdict_counts,
        "artifacts": artifacts,
        "trend_summary": {
            "dominant_changes": dominant,
            "stable_signals": stable,
            "run_coverage": dict(verdict_counts),
        },
        "anomaly_flags": _build_anomaly_flags(verdict_counts),
    }


def _build_anomaly_flags(verdict_counts: dict) -> dict:
    ranking = verdict_counts.get("ranking_changed", 0) > 0
    unknown = verdict_counts.get("unknown_reduced", 0) > 0
    disq = verdict_counts.get("disqualified_changed", 0) > 0
    conf_no_reason = (
        verdict_counts.get("confidence_changed", 0) > 0
        and verdict_counts.get("reason_changed", 0) == 0
    )
    return {
        "ranking_changed_present": ranking,
        "unknown_reduced_present": unknown,
        "disqualified_changed_present": disq,
        "confidence_changed_without_reason_changed": conf_no_reason,
        "needs_manual_review": ranking or unknown or disq or conf_no_reason,
    }


def print_summary(result: dict) -> None:
    from src.experiments.review_summary import format_review_summary_text
    rs = result.get("review_summary")
    if rs:
        print(format_review_summary_text(
            rs, query=result.get("query", ""), model=result.get("model", "")))
    else:
        # Fallback to old format
        d = result["diff_summary"]
        print(f"Ranking changed: {d['ranking_changed']}")

    if not any([d["score_changes"], d["confidence_changes"],
                d["unknown_changes"], d["reason_changes"]]):
        print("\nNo differences detected")


def main() -> int:
    parser = argparse.ArgumentParser(description="Solution Catalog live ablation")
    parser.add_argument("--query", required=True, help="User query")
    parser.add_argument("--model", default="gemini-2.5-flash", help="LLM model")
    parser.add_argument("--out", type=str, default=None, help="Output JSON path")
    parser.add_argument("--log-level", default="WARNING",
                        choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    args = parser.parse_args()

    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        stream=sys.stderr,
    )

    result = run_live_ablation(args.query, args.model)
    print_summary(result)

    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

        # Index file
        index = build_artifact_index(result, artifact_path=str(out_path))
        index_path = out_path.with_suffix(".index.json")
        index_path.write_text(
            json.dumps(index, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

        # Directory summary
        index_dir = out_path.parent
        index_items = []
        for idx_file in sorted(index_dir.glob("*.index.json")):
            try:
                item = json.loads(idx_file.read_text("utf-8"))
                index_items.append(item)
            except (json.JSONDecodeError, OSError):
                pass
        summary = build_artifact_directory_summary(index_items)
        summary_path = index_dir / "_index_summary.json"
        summary_path.write_text(
            json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

        print(f"\nSaved full result to: {out_path}")
        print(f"Saved index to: {index_path}")
        print(f"Updated directory summary: {summary_path}")

        ts = summary.get("trend_summary", {})
        dom = ",".join(ts.get("dominant_changes", [])) or "none"
        stb = ",".join(ts.get("stable_signals", [])) or "none"
        print(f"Directory trends: dominant={dom} stable={stb}")

        af = summary.get("anomaly_flags", {})
        yn = lambda b: "yes" if b else "no"
        print(
            f"Directory anomaly flags: "
            f"manual_review={yn(af.get('needs_manual_review'))} "
            f"ranking_changed={yn(af.get('ranking_changed_present'))} "
            f"unknown_reduced={yn(af.get('unknown_reduced_present'))} "
            f"disqualified_changed={yn(af.get('disqualified_changed_present'))} "
            f"confidence_without_reason={yn(af.get('confidence_changed_without_reason_changed'))}"
        )

    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
