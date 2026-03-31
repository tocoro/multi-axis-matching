"""Multi-axis matching API server.

Usage:
    uv run server.py                    # mock mode (default)
    uv run server.py --live             # real LLM
    uv run server.py --port 8080        # custom port
"""

import argparse
import json
import logging
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


class EvaluateRequest(BaseModel):
    request_id: str
    user_query: str
    candidates: list[dict]


# --- Mock LLM for pipeline ---

def _pipeline_mock(system_prompt: str, user_message: str) -> dict:
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
    default = {
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
        "risk_notes": [], "summary_reason": "Default mock",
    }
    return {"candidate_id": cid, **default}


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

    try:
        if _use_live:
            response = run_restaurant_pipeline(**kwargs)
        else:
            with patch("src.evaluator.call_llm", side_effect=_pipeline_mock):
                response = run_restaurant_pipeline(**kwargs)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Pipeline failed")
        raise HTTPException(status_code=500, detail=str(e))

    return response


@app.post("/api/evaluate")
async def api_evaluate(req: EvaluateRequest):
    request = {
        "request_id": req.request_id,
        "user_query": req.user_query,
        "candidates": req.candidates,
    }
    try:
        if _use_live:
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
