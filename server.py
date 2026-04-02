"""Multi-axis matching API server.

Usage:
    uv run server.py                    # mock mode (default)
    uv run server.py --live             # real LLM
    uv run server.py --port 8080        # custom port
"""

import argparse
import json
import logging
import os
import sys
import traceback
from contextlib import asynccontextmanager
from pathlib import Path
from unittest.mock import patch

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.evaluator import evaluate  # noqa: E402
from src.mock import mock_restaurant_dispatch, MOCK_AXES  # noqa: E402
from src.pipeline.restaurant_pipeline import run_restaurant_pipeline  # noqa: E402

logger = logging.getLogger(__name__)

# --- Global state ---
_use_live = False
_request_counter = 0


# --- Request/Response models ---

class PipelineRequest(BaseModel):
    query: str
    enable_fallback: bool = True
    use_google_places: bool = False
    live: bool = False
    model: str | None = None


class EvaluateRequest(BaseModel):
    request_id: str
    user_query: str
    candidates: list[dict]
    live: bool = False


# --- Mock LLM for pipeline ---

_CANDIDATE_EVALS = {
    "place_1": {
        "axis_scores": [
            {"axis": "cuisine", "score": 0.85, "status": "supported",
             "reason": "Italian restaurant", "hard_constraint_violation": False},
            {"axis": "budget", "score": 0.9, "status": "supported",
             "reason": "2500 avg within 3000", "hard_constraint_violation": False},
            {"axis": "atmosphere", "score": 0.85, "status": "supported",
             "reason": "Quiet and calm", "hard_constraint_violation": False},
            {"axis": "location", "score": 0.9, "status": "supported",
             "reason": "In Ebisu, 5 min walk", "hard_constraint_violation": False},
            {"axis": "rating", "score": 0.7, "status": "supported",
             "reason": "Good reviews", "hard_constraint_violation": False},
        ],
        "strengths": ["Quiet Italian in Ebisu", "Within budget"],
        "weaknesses": [],
        "missing_information": [],
        "risk_notes": [],
        "summary_reason": "Strong match: quiet Italian in Ebisu, well within budget",
    },
    "place_2": {
        "axis_scores": [
            {"axis": "cuisine", "score": 0.3, "status": "conflict",
             "reason": "Bar, not Italian", "hard_constraint_violation": False},
            {"axis": "budget", "score": 0.95, "status": "supported",
             "reason": "Very affordable at 1500 avg", "hard_constraint_violation": False},
            {"axis": "atmosphere", "score": 0.2, "status": "conflict",
             "reason": "Lively/noisy, user wants quiet",
             "hard_constraint_violation": False},
            {"axis": "location", "score": 0.8, "status": "supported",
             "reason": "In Ebisu", "hard_constraint_violation": False},
            {"axis": "rating", "score": 0.5, "status": "supported",
             "reason": "Average reviews", "hard_constraint_violation": False},
        ],
        "strengths": ["Very affordable"],
        "weaknesses": ["Not Italian", "Noisy atmosphere"],
        "missing_information": [],
        "risk_notes": [],
        "summary_reason": "Budget-friendly but wrong genre and noisy",
    },
    "place_3": {
        "axis_scores": [
            {"axis": "cuisine", "score": 0.8, "status": "supported",
             "reason": "Italian restaurant", "hard_constraint_violation": False},
            {"axis": "budget", "score": 0.9, "status": "supported",
             "reason": "2000 avg within 3000", "hard_constraint_violation": False},
            {"axis": "atmosphere", "score": 0.8, "status": "supported",
             "reason": "Quiet hideaway", "hard_constraint_violation": False},
            {"axis": "location", "score": 0.2, "status": "conflict",
             "reason": "Nakameguro, not Ebisu as requested",
             "hard_constraint_violation": False},
            {"axis": "rating", "score": 0.75, "status": "supported",
             "reason": "High quality food", "hard_constraint_violation": False},
        ],
        "strengths": ["Quality Italian", "Very quiet", "Affordable"],
        "weaknesses": ["Not in Ebisu (Nakameguro)"],
        "missing_information": [],
        "risk_notes": [],
        "summary_reason": "Great Italian hideaway but located in Nakameguro, not Ebisu",
    },
    "place_4": {
        "axis_scores": [
            {"axis": "cuisine", "score": 0.0, "status": "unknown",
             "reason": "No cuisine information"},
            {"axis": "budget", "score": 0.0, "status": "unknown",
             "reason": "No price information"},
            {"axis": "atmosphere", "score": 0.6, "status": "supported",
             "reason": "Described as calm atmosphere",
             "hard_constraint_violation": False},
            {"axis": "location", "score": 0.0, "status": "unknown",
             "reason": "No address provided"},
            {"axis": "rating", "score": 0.0, "status": "unknown",
             "reason": "No rating data"},
        ],
        "strengths": ["Seems to have calm atmosphere"],
        "weaknesses": ["Very little information available"],
        "missing_information": ["Cuisine type", "Price range", "Address", "Rating"],
        "risk_notes": ["Insufficient data to evaluate most axes"],
        "summary_reason": "Only atmosphere is evaluable; critical info missing",
    },
}

_DEFAULT_EVAL = {
    "axis_scores": [
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
    ],
    "strengths": [], "weaknesses": [], "missing_information": [],
    "risk_notes": [], "summary_reason": "Default evaluation",
}


def _pipeline_mock(system_prompt: str, user_message: str) -> dict:
    if "前処理" in system_prompt:
        return {
            "inferred_problem_type": "local.restaurant",
            "confidence": 0.92,
            "reason": "Restaurant query",
        }
    if "制約を抽出" in system_prompt:
        # user_message からクエリを見て制約を動的に返す
        constraints: dict = {"hard_constraints": {}, "soft_preferences": {}, "notes": []}
        if "3000" in user_message or "３０００" in user_message:
            constraints["hard_constraints"]["budget_max"] = 3000
        if "静か" in user_message or "話せる" in user_message:
            constraints["soft_preferences"]["atmosphere"] = "quiet"
        return constraints
    if "評価軸選択" in system_prompt:
        return {"axes": MOCK_AXES, "reason": "Restaurant axes"}

    # evaluate_candidate — query の制約に応じて動的に評価
    parsed = json.loads(user_message)
    cid = parsed["candidate"]["candidate_id"]
    hard = parsed.get("hard_constraints", {})
    soft = parsed.get("soft_preferences", {})
    user_query = parsed.get("user_query", "")

    # location 要求があるかどうかで評価を分岐
    location_requested = hard.get("location") or any(
        loc in user_query for loc in ("恵比寿", "渋谷", "新宿", "六本木", "銀座")
    )

    import copy
    data = copy.deepcopy(_CANDIDATE_EVALS.get(cid, _DEFAULT_EVAL))

    # location 要求がない場合、location 軸を中立にする
    if not location_requested:
        for axis in data["axis_scores"]:
            if axis["axis"] == "location":
                if axis["status"] == "conflict":
                    axis["status"] = "supported"
                    axis["score"] = 0.6
                    axis["reason"] = "No specific location requested"
                    axis["hard_constraint_violation"] = False
        # strengths/weaknesses からも location 言及を除去
        data["weaknesses"] = [w for w in data.get("weaknesses", [])
                              if "Ebisu" not in w and "恵比寿" not in w]
        if "not Ebisu" in data.get("summary_reason", ""):
            data["summary_reason"] = data["summary_reason"].replace(
                "but located in Nakameguro, not Ebisu", "in Nakameguro")

    # atmosphere 要求がない場合、atmosphere conflict を中立にする
    if not soft.get("atmosphere"):
        for axis in data["axis_scores"]:
            if axis["axis"] == "atmosphere" and axis["status"] == "conflict":
                axis["status"] = "supported"
                axis["score"] = 0.5
                axis["reason"] = "No specific atmosphere preference"

    return {"candidate_id": cid, **data}


# --- App ---

app = FastAPI(title="Multi-Axis Matching", version="0.1.0")
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def index():
    return FileResponse("static/index.html")


@app.post("/api/pipeline")
async def api_pipeline(req: PipelineRequest):
    global _request_counter
    _request_counter += 1
    request_id = f"web-{_request_counter}"

    kwargs = dict(
        request_id=request_id,
        user_query=req.query,
        enable_fallback=req.enable_fallback,
    )

    if req.use_google_places:
        from src.adapters.places.google_places import GooglePlacesSearcher
        kwargs["place_searcher"] = GooglePlacesSearcher()

    use_live = req.live or _use_live

    # Model override per request
    orig_model = os.environ.get("EVAL_MODEL")
    if req.model and use_live:
        os.environ["EVAL_MODEL"] = req.model

    try:
        if use_live:
            response = run_restaurant_pipeline(**kwargs)
        else:
            with patch("src.evaluator.call_llm", side_effect=_pipeline_mock):
                response = run_restaurant_pipeline(**kwargs)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Pipeline failed")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if orig_model is not None:
            os.environ["EVAL_MODEL"] = orig_model
        elif "EVAL_MODEL" in os.environ and req.model:
            del os.environ["EVAL_MODEL"]

    response["mode"] = "live" if use_live else "mock"
    if req.model and use_live:
        response["model"] = req.model
    return response


@app.post("/api/evaluate")
async def api_evaluate(req: EvaluateRequest):
    request = {
        "request_id": req.request_id,
        "user_query": req.user_query,
        "candidates": req.candidates,
    }
    use_live = req.live or _use_live

    try:
        if use_live:
            response = evaluate(request)
        else:
            with patch("src.evaluator.call_llm", side_effect=mock_restaurant_dispatch):
                response = evaluate(request)
    except Exception as e:
        logger.exception("Evaluate failed")
        raise HTTPException(status_code=500, detail=str(e))

    return response


def main():
    global _use_live

    parser = argparse.ArgumentParser(description="Multi-Axis Matching API Server")
    parser.add_argument("--live", action="store_true", help="Use real LLM")
    parser.add_argument("--port", type=int, default=3000)
    parser.add_argument("--host", default="0.0.0.0")
    args = parser.parse_args()

    _use_live = args.live

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    mode = "LIVE" if _use_live else "MOCK"
    logger.info("Starting server in %s mode on %s:%d", mode, args.host, args.port)

    import uvicorn
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
