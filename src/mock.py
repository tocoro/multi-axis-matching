"""Deterministic mock for restaurant example evaluation.

LLM を呼ばず固定値を返す。テストおよび --mock 実行で使用。
毎回同一の結果を返すことを保証する。
"""

import json

MOCK_AXES = [
    {"axis": "cuisine", "weight": 0.25},
    {"axis": "budget", "weight": 0.25},
    {"axis": "atmosphere", "weight": 0.2},
    {"axis": "location", "weight": 0.2},
    {"axis": "rating", "weight": 0.1},
]

_CANDIDATE_EVALS: dict[str, dict] = {
    "r1": {
        "axis_scores": [
            {"axis": "cuisine", "score": 0.8, "status": "supported",
             "reason": "Italian restaurant matches query",
             "hard_constraint_violation": False},
            {"axis": "budget", "score": 0.9, "status": "supported",
             "reason": "Average 2500 yen within 3000 yen budget",
             "hard_constraint_violation": False},
            {"axis": "atmosphere", "score": 0.85, "status": "supported",
             "reason": "Described as quiet and calm",
             "hard_constraint_violation": False},
            {"axis": "location", "score": 0.0, "status": "unknown",
             "reason": "No address information provided"},
            {"axis": "rating", "score": 0.6, "status": "supported",
             "reason": "No explicit rating data, moderate default",
             "hard_constraint_violation": False},
        ],
        "strengths": [
            "Quiet atmosphere matches preference",
            "Within budget",
        ],
        "weaknesses": ["No location details"],
        "missing_information": ["Exact address", "Business hours"],
        "risk_notes": [],
        "summary_reason": "Good match: quiet Italian within budget, but location unknown",
    },
    "r2": {
        "axis_scores": [
            {"axis": "cuisine", "score": 0.5, "status": "supported",
             "reason": "Bar, not specifically Italian",
             "hard_constraint_violation": False},
            {"axis": "budget", "score": 0.95, "status": "supported",
             "reason": "Average 2000 yen, well within 3000 yen budget",
             "hard_constraint_violation": False},
            {"axis": "atmosphere", "score": 0.2, "status": "conflict",
             "reason": "Described as lively/noisy, user prefers quiet",
             "hard_constraint_violation": False},
            {"axis": "location", "score": 0.0, "status": "unknown",
             "reason": "No address information provided"},
            {"axis": "rating", "score": 0.5, "status": "supported",
             "reason": "No explicit rating data",
             "hard_constraint_violation": False},
        ],
        "strengths": ["Very affordable"],
        "weaknesses": [
            "Noisy atmosphere conflicts with quiet preference",
            "Not specifically Italian",
        ],
        "missing_information": ["Exact address", "Business hours"],
        "risk_notes": [],
        "summary_reason":
            "Budget-friendly but atmosphere mismatch: noisy vs quiet preference",
    },
}


def mock_restaurant_dispatch(system_prompt: str, user_message: str) -> dict:
    """Deterministic mock for restaurant example.

    プロンプト内容に基づいてパイプラインの各ステップに適切な固定値を返す。
    """
    # Step 1: problem type inference
    if "前処理" in system_prompt:
        return {
            "inferred_problem_type": "local.restaurant",
            "confidence": 0.92,
            "reason": "Query mentions area and restaurant type with budget",
        }

    # Step 2: constraint extraction
    if "制約を抽出" in system_prompt:
        return {
            "hard_constraints": {"budget_max": 3000},
            "soft_preferences": {"atmosphere": "quiet"},
            "notes": [],
        }

    # Step 3: axis selection
    if "評価軸選択" in system_prompt:
        return {
            "axes": MOCK_AXES,
            "reason": "Restaurant: cuisine, budget, atmosphere, location, rating",
        }

    # Step 4: candidate evaluation
    parsed = json.loads(user_message)
    cid = parsed["candidate"]["candidate_id"]
    scores = _CANDIDATE_EVALS.get(cid)
    if scores is None:
        raise ValueError(f"No mock data for candidate_id={cid!r}")
    return {"candidate_id": cid, **scores}
