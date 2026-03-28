#!/usr/bin/env python3
"""Run restaurant example through the evaluator.

Usage:
    python scripts/run_restaurant_example.py --mock   # deterministic, no API key
    python scripts/run_restaurant_example.py --live   # real LLM, requires ANTHROPIC_API_KEY
"""

import argparse
import json
import logging
import sys
from pathlib import Path
from unittest.mock import patch

# Project root on sys.path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.evaluator import evaluate  # noqa: E402
from src.mock import mock_restaurant_dispatch  # noqa: E402

logger = logging.getLogger(__name__)

EXAMPLE_PATH = ROOT / "examples" / "restaurant.json"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run restaurant example evaluation",
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--mock", action="store_true",
        help="Use deterministic mock — no API key required (default)",
    )
    group.add_argument(
        "--live", action="store_true",
        help="Use real LLM — requires ANTHROPIC_API_KEY",
    )
    parser.add_argument(
        "--log-level", default="WARNING",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Log verbosity (default: WARNING)",
    )
    args = parser.parse_args()

    # Configure logging to stderr so stdout stays clean for JSON
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        stream=sys.stderr,
    )

    # Load request
    if not EXAMPLE_PATH.exists():
        print(f"Error: Example file not found: {EXAMPLE_PATH}", file=sys.stderr)
        return 1

    request = json.loads(EXAMPLE_PATH.read_text(encoding="utf-8"))
    logger.info("Loaded request: %s", request["request_id"])

    # Run evaluation
    if args.live:
        logger.info("Running in LIVE mode")
        response = evaluate(request)
    else:
        logger.info("Running in MOCK mode")
        with patch("src.evaluator.call_llm", side_effect=mock_restaurant_dispatch):
            response = evaluate(request)

    # Output
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
