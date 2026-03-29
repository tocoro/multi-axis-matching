#!/usr/bin/env python3
"""Run restaurant pipeline end-to-end.

Usage:
    python scripts/run_restaurant_pipeline.py --mock
    python scripts/run_restaurant_pipeline.py --live
    python scripts/run_restaurant_pipeline.py --mock --log-level INFO
"""

import argparse
import json
import logging
import sys
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.pipeline.restaurant_pipeline import run_restaurant_pipeline  # noqa: E402
from src.mock import MOCK_AXES  # noqa: E402

logger = logging.getLogger(__name__)

INPUT_PATH = ROOT / "examples" / "restaurant_pipeline_input.json"


def _pipeline_llm_mock(system_prompt: str, user_message: str) -> dict:
    """Mock LLM for pipeline execution."""
    if "前処理" in system_prompt:
        return {
            "inferred_problem_type": "local.restaurant",
            "confidence": 0.92,
            "reason": "Restaurant query",
        }
    if "制約を抽出" in system_prompt:
        return {
            "hard_constraints": {"budget_max": 3000},
            "soft_preferences": {"atmosphere": "quiet"},
            "notes": [],
        }
    if "評価軸選択" in system_prompt:
        return {"axes": MOCK_AXES, "reason": "Restaurant axes"}

    parsed = json.loads(user_message)
    cid = parsed["candidate"]["candidate_id"]

    default_scores = [
        {"axis": "cuisine", "score": 0.5, "status": "supported",
         "reason": "Generic", "hard_constraint_violation": False},
        {"axis": "budget", "score": 0.7, "status": "supported",
         "reason": "OK", "hard_constraint_violation": False},
        {"axis": "atmosphere", "score": 0.5, "status": "supported",
         "reason": "Average", "hard_constraint_violation": False},
        {"axis": "location", "score": 0.5, "status": "supported",
         "reason": "OK", "hard_constraint_violation": False},
        {"axis": "rating", "score": 0.5, "status": "supported",
         "reason": "Average", "hard_constraint_violation": False},
    ]

    overrides = {
        "place_1": {
            "axis_scores": [
                {"axis": "cuisine", "score": 0.85, "status": "supported",
                 "reason": "Italian", "hard_constraint_violation": False},
                {"axis": "budget", "score": 0.9, "status": "supported",
                 "reason": "2500 avg", "hard_constraint_violation": False},
                {"axis": "atmosphere", "score": 0.85, "status": "supported",
                 "reason": "Quiet", "hard_constraint_violation": False},
                {"axis": "location", "score": 0.9, "status": "supported",
                 "reason": "Ebisu 5min", "hard_constraint_violation": False},
                {"axis": "rating", "score": 0.7, "status": "supported",
                 "reason": "Good", "hard_constraint_violation": False},
            ],
            "strengths": ["Quiet Italian in Ebisu"],
            "weaknesses": [],
            "missing_information": [],
            "risk_notes": [],
            "summary_reason": "Strong match",
        },
        "place_4": {
            "axis_scores": [
                {"axis": "cuisine", "score": 0.0, "status": "unknown",
                 "reason": "No info"},
                {"axis": "budget", "score": 0.0, "status": "unknown",
                 "reason": "No info"},
                {"axis": "atmosphere", "score": 0.6, "status": "supported",
                 "reason": "Seems calm", "hard_constraint_violation": False},
                {"axis": "location", "score": 0.0, "status": "unknown",
                 "reason": "No address"},
                {"axis": "rating", "score": 0.0, "status": "unknown",
                 "reason": "No reviews"},
            ],
            "strengths": [],
            "weaknesses": ["Very little info"],
            "missing_information": ["Cuisine", "Price", "Address", "Reviews"],
            "risk_notes": ["Insufficient data"],
            "summary_reason": "Mostly unknown",
        },
    }

    data = overrides.get(cid, {
        "axis_scores": default_scores,
        "strengths": [],
        "weaknesses": [],
        "missing_information": [],
        "risk_notes": [],
        "summary_reason": "Default mock",
    })
    return {"candidate_id": cid, **data}


def main() -> int:
    parser = argparse.ArgumentParser(description="Run restaurant pipeline")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--mock", action="store_true",
                       help="Use mock LLM (default)")
    group.add_argument("--live", action="store_true",
                       help="Use real LLM (requires API key)")
    parser.add_argument("--strict", action="store_true",
                        help="Disable fallback (strict search only)")
    parser.add_argument("--log-level", default="WARNING",
                        choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    parser.add_argument("--input", type=str, default=None,
                        help="Custom input JSON path")
    args = parser.parse_args()

    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        stream=sys.stderr,
    )

    input_path = Path(args.input) if args.input else INPUT_PATH
    data = json.loads(input_path.read_text(encoding="utf-8"))
    request_id = data["request_id"]
    user_query = data["user_query"]

    enable_fallback = not args.strict

    if args.live:
        response = run_restaurant_pipeline(
            request_id, user_query, enable_fallback=enable_fallback)
    else:
        with patch("src.evaluator.call_llm", side_effect=_pipeline_llm_mock):
            response = run_restaurant_pipeline(
                request_id, user_query, enable_fallback=enable_fallback)

    json.dump(response, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        logging.debug("Traceback:", exc_info=True)
        sys.exit(1)
