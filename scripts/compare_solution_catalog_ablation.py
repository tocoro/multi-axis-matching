#!/usr/bin/env python3
"""Solution Catalog ablation comparison.

Usage:
    python scripts/compare_solution_catalog_ablation.py
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tests.test_solution_catalog_ablation import _ablation_llm_mock  # noqa: E402
from src.experiments.catalog_ablation import run_ablation  # noqa: E402

QUERY = "恵比寿で静かに話せるイタリアン。予算は3000円以内"


def main():
    result = run_ablation("ablation-demo", QUERY, llm_mock_fn=_ablation_llm_mock)

    # Print diff summary
    print("=== Ablation: Solution Catalog On/Off ===")
    print(f"Query: {result['query']}")
    print()

    d = result["diff_summary"]
    print(f"Ranking changed: {d['ranking_changed']}")
    print()

    if d["score_changes"]:
        print("Score changes:")
        for cid, v in d["score_changes"].items():
            print(f"  {cid}: {v['without']} → {v['with']}")
    else:
        print("Score changes: (none)")
    print()

    if d["confidence_changes"]:
        print("Confidence changes:")
        for cid, v in d["confidence_changes"].items():
            print(f"  {cid}: {v['without']} → {v['with']}")
    else:
        print("Confidence changes: (none)")
    print()

    if d["reason_changes"]:
        print("Reason changes (axes with different text):")
        for cid, axes in d["reason_changes"].items():
            print(f"  {cid}: {', '.join(axes)}")
    else:
        print("Reason changes: (none)")
    print()

    if d["unknown_changes"]:
        print("Unknown changes:")
        for cid, v in d["unknown_changes"].items():
            print(f"  {cid}: {v['without']} → {v['with']}")
    else:
        print("Unknown changes: (none)")
    print()

    # Full JSON
    print("=== Full diff_summary JSON ===")
    print(json.dumps(d, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
