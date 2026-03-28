"""Multi-axis matching evaluator.

LLMベースの問題解決マッチング評価パイプライン。
ユーザーの問題記述と候補を多軸評価し、理由付きランキングを返す。
"""

import json
import logging
import os
from pathlib import Path

import anthropic
import jsonschema

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent
PROMPTS_DIR = BASE_DIR / "prompts"
SCHEMAS_DIR = BASE_DIR / "schemas"

# Problem type → evaluation axes with weights
AXES_BY_TYPE: dict[str, list[dict]] = {
    "entertainment.music": [
        {"axis": "genre_match", "weight": 0.3},
        {"axis": "mood_match", "weight": 0.25},
        {"axis": "tempo_match", "weight": 0.15},
        {"axis": "popularity", "weight": 0.15},
        {"axis": "freshness", "weight": 0.15},
    ],
    "local.restaurant": [
        {"axis": "cuisine_match", "weight": 0.25},
        {"axis": "budget_match", "weight": 0.25},
        {"axis": "atmosphere_match", "weight": 0.2},
        {"axis": "location_match", "weight": 0.2},
        {"axis": "rating", "weight": 0.1},
    ],
    "local.clinic": [
        {"axis": "specialty_match", "weight": 0.3},
        {"axis": "accessibility", "weight": 0.2},
        {"axis": "reputation", "weight": 0.2},
        {"axis": "availability", "weight": 0.15},
        {"axis": "location_match", "weight": 0.15},
    ],
    "professional.legal": [
        {"axis": "expertise_match", "weight": 0.35},
        {"axis": "track_record", "weight": 0.25},
        {"axis": "cost_match", "weight": 0.2},
        {"axis": "accessibility", "weight": 0.1},
        {"axis": "communication", "weight": 0.1},
    ],
    "commerce.product": [
        {"axis": "feature_match", "weight": 0.3},
        {"axis": "price_match", "weight": 0.25},
        {"axis": "quality", "weight": 0.2},
        {"axis": "brand_trust", "weight": 0.15},
        {"axis": "availability", "weight": 0.1},
    ],
}

HIGH_RISK_TYPES = {"local.clinic", "professional.legal"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_prompt(name: str) -> str:
    return (PROMPTS_DIR / name).read_text(encoding="utf-8")


def _load_schema(name: str) -> dict:
    return json.loads((SCHEMAS_DIR / name).read_text(encoding="utf-8"))


def _parse_json_from_llm(raw: str) -> dict:
    """Extract and parse JSON from LLM response text."""
    text = raw.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1]).strip()
    return json.loads(text)


def call_llm(system_prompt: str, user_message: str) -> dict:
    """Call LLM and parse the JSON response."""
    client = anthropic.Anthropic()
    model = os.environ.get("EVAL_MODEL", "claude-sonnet-4-20250514")

    logger.info("LLM call start  model=%s", model)
    logger.debug("  system: %s", system_prompt[:80])
    logger.debug("  user:   %s", user_message[:120])

    response = client.messages.create(
        model=model,
        max_tokens=2048,
        system=system_prompt,
        messages=[{"role": "user", "content": user_message}],
    )

    raw = response.content[0].text
    logger.debug("LLM raw response: %s", raw)

    result = _parse_json_from_llm(raw)
    logger.info("LLM call done — parsed OK")
    return result


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate_request(request: dict) -> None:
    schema = _load_schema("request.schema.json")
    jsonschema.validate(instance=request, schema=schema)


def validate_response(response: dict) -> None:
    schema = _load_schema("response.schema.json")
    jsonschema.validate(instance=response, schema=schema)


# ---------------------------------------------------------------------------
# Pipeline steps
# ---------------------------------------------------------------------------

def infer_problem_type(user_query: str, given_type: str | None = None) -> dict:
    """Step 1: problem type を推定する。明示されていればそのまま返す。"""
    if given_type:
        logger.info("Problem type provided explicitly: %s", given_type)
        return {
            "inferred_problem_type": given_type,
            "confidence": 1.0,
            "reason": "Explicitly provided in request",
        }
    prompt = _load_prompt("infer_problem_type.txt")
    return call_llm(prompt, user_query)


def extract_constraints(user_query: str, given_constraints: dict | None = None) -> dict:
    """Step 2: ユーザー文からハード制約・ソフト選好を抽出する。"""
    if given_constraints and (
        given_constraints.get("hard_constraints") or given_constraints.get("soft_preferences")
    ):
        logger.info("Using constraints provided in request")
        return {
            "hard_constraints": given_constraints.get("hard_constraints", {}),
            "soft_preferences": given_constraints.get("soft_preferences", {}),
            "notes": [],
        }
    prompt = _load_prompt("extract_constraints.txt")
    return call_llm(prompt, user_query)


def get_axes_for_type(problem_type: str) -> list[dict]:
    """problem_type に対応する評価軸リストを返す。"""
    axes = AXES_BY_TYPE.get(problem_type)
    if axes is None:
        logger.warning("Unknown problem type '%s' — falling back to generic axes", problem_type)
        return [
            {"axis": "relevance", "weight": 0.4},
            {"axis": "quality", "weight": 0.3},
            {"axis": "feasibility", "weight": 0.3},
        ]
    return [dict(a) for a in axes]  # shallow copy


def evaluate_candidate(
    candidate: dict,
    user_query: str,
    problem_type: str,
    axes: list[dict],
    constraints: dict,
) -> dict:
    """Step 3: 候補を各軸で評価する。"""
    prompt = _load_prompt("evaluate_candidate.txt")
    user_message = json.dumps(
        {
            "user_query": user_query,
            "problem_type": problem_type,
            "axes": [a["axis"] for a in axes],
            "hard_constraints": constraints.get("hard_constraints", {}),
            "soft_preferences": constraints.get("soft_preferences", {}),
            "candidate": candidate,
        },
        ensure_ascii=False,
    )
    return call_llm(prompt, user_message)


def aggregate_scores(
    axis_scores: list[dict],
    axes: list[dict],
    is_high_risk: bool,
) -> tuple[float, float]:
    """Step 4: 軸別スコアから総合スコアを算出する。

    total_score = Σ(weight × score) / Σ(valid_weight)
    unknown 軸は分母・分子の両方から除外する。

    高リスク領域で confidence が低い場合はペナルティを適用。

    Returns:
        (total_score, confidence)
    """
    weight_map = {a["axis"]: a["weight"] for a in axes}
    total_weight = sum(a["weight"] for a in axes)

    weighted_sum = 0.0
    valid_weight = 0.0

    for entry in axis_scores:
        axis = entry["axis"]
        status = entry["status"]
        score = float(entry["score"])
        w = weight_map.get(axis, 0.0)

        if status == "unknown":
            # unknown は分母から除外
            continue

        weighted_sum += w * score
        valid_weight += w

    if valid_weight == 0:
        return 0.0, 0.0

    total_score = weighted_sum / valid_weight
    confidence = valid_weight / total_weight if total_weight > 0 else 0.0

    # 高リスク領域: confidence が低いとき保守的にスコアを下げる
    if is_high_risk and confidence < 0.7:
        logger.info(
            "High-risk penalty: score %.4f × confidence %.4f", total_score, confidence
        )
        total_score *= confidence

    return round(total_score, 4), round(confidence, 4)


def check_disqualification(axis_scores: list[dict]) -> tuple[bool, list[str]]:
    """ハード制約違反 (conflict) があれば disqualified にする。"""
    reasons = []
    for entry in axis_scores:
        if entry["status"] == "conflict":
            reasons.append(
                f"Conflict on '{entry['axis']}': {entry.get('reason', 'N/A')}"
            )
    return bool(reasons), reasons


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def evaluate(request: dict) -> dict:
    """評価パイプライン本体。

    1. problem type 推定
    2. 制約抽出
    3. 候補ごとの軸別評価
    4. 総合スコア集約
    5. ランキング生成
    """
    logging.basicConfig(
        level=os.environ.get("LOG_LEVEL", "INFO"),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    logger.info("=== Evaluation started: request_id=%s ===", request.get("request_id"))

    # Input validation
    validate_request(request)
    logger.info("Request schema validated")

    request_id = request["request_id"]
    user_query = request["user_query"]
    candidates = request["candidates"]

    # Step 1: problem type
    type_result = infer_problem_type(user_query, request.get("problem_type"))
    problem_type = type_result["inferred_problem_type"]
    type_confidence = type_result["confidence"]
    logger.info("Problem type: %s (confidence=%.2f)", problem_type, type_confidence)

    is_high_risk = problem_type in HIGH_RISK_TYPES
    if is_high_risk:
        logger.warning("HIGH-RISK domain detected: %s", problem_type)

    # Step 2: constraints
    constraint_result = extract_constraints(user_query, request.get("constraints"))
    hard_constraints = constraint_result.get("hard_constraints", {})
    logger.info(
        "Constraints: hard=%d, soft=%d",
        len(hard_constraints),
        len(constraint_result.get("soft_preferences", {})),
    )

    # Axes
    axes = get_axes_for_type(problem_type)
    logger.info("Selected %d evaluation axes", len(axes))

    # Step 3 & 4: evaluate + aggregate per candidate
    ranking_entries: list[dict] = []

    for candidate in candidates:
        cid = candidate["candidate_id"]
        logger.info("--- Evaluating candidate: %s ---", cid)

        eval_result = evaluate_candidate(
            candidate, user_query, problem_type, axes, constraint_result
        )
        axis_scores = eval_result.get("axis_scores", [])

        total_score, confidence = aggregate_scores(axis_scores, axes, is_high_risk)
        disqualified, disq_reasons = check_disqualification(axis_scores)

        if disqualified:
            logger.warning("Candidate %s DISQUALIFIED: %s", cid, disq_reasons)

        entry: dict = {
            "rank": 0,
            "candidate_id": cid,
            "total_score": total_score,
            "confidence": confidence,
            "disqualified": disqualified,
            "axis_scores": axis_scores,
            "strengths": eval_result.get("strengths", []),
            "weaknesses": eval_result.get("weaknesses", []),
            "missing_information": eval_result.get("missing_information", []),
            "risk_notes": eval_result.get("risk_notes", []),
            "summary_reason": eval_result.get("summary_reason", ""),
        }
        if disqualified:
            entry["disqualification_reasons"] = disq_reasons

        ranking_entries.append(entry)

    # Step 5: rank — disqualified を末尾、同グループ内は total_score 降順
    ranking_entries.sort(
        key=lambda e: (not e.get("disqualified", False), e["total_score"]),
        reverse=True,
    )
    for i, entry in enumerate(ranking_entries, 1):
        entry["rank"] = i

    # Collect global missing information
    global_missing: list[str] = []
    for entry in ranking_entries:
        for info in entry.get("missing_information", []):
            if info not in global_missing:
                global_missing.append(info)

    # Build response
    response: dict = {
        "request_id": request_id,
        "inferred_problem_type": problem_type,
        "problem_type_confidence": type_confidence,
        "extracted_constraints": constraint_result,
        "selected_axes": axes,
        "ranking": ranking_entries,
        "needs_human_review": is_high_risk or type_confidence < 0.5,
    }
    if global_missing:
        response["global_missing_information"] = global_missing

    # Output validation
    validate_response(response)
    logger.info("=== Evaluation complete: %d candidates ranked ===", len(ranking_entries))

    return response
