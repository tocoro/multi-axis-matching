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

    # Solution Catalog の有無で reason / score を補助的に調整
    has_catalog = "solution_catalog" in parsed
    if has_catalog:
        catalog = parsed["solution_catalog"]
        claim_patterns = {
            c["problem_pattern"] for c in catalog.get("solution_claims", [])
        }
        lim_patterns = {
            l["problem_pattern"] for l in catalog.get("hard_limitations", [])
        }
        for axis in data["axis_scores"]:
            # atmosphere: quiet_conversation claim があれば reason 補強 + 微増
            if axis["axis"] == "atmosphere" and axis["status"] == "supported":
                if "quiet_conversation" in claim_patterns or "quiet_italian" in claim_patterns:
                    axis["score"] = min(axis["score"] + 0.05, 0.95)
                    axis["reason"] += " (catalog: quiet_conversation claim)"
            # location: ebisu_area limitation があれば reason 補強 + 微減
            if axis["axis"] == "location" and axis["status"] == "conflict":
                if "ebisu_area" in lim_patterns:
                    axis["score"] = max(axis["score"] - 0.05, 0.05)
                    axis["reason"] += " (catalog: ebisu_area limitation)"
        data["summary_reason"] += " [catalog referenced]"

    return {"candidate_id": cid, **data}


# --- App ---

app = FastAPI(title="Multi-Axis Matching", version="0.1.0")
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def index():
    return FileResponse("static/index.html")


@app.get("/api/directory-summary")
async def api_directory_summary():
    """artifacts/_index_summary.json を読んで返す。"""
    summary_path = Path("artifacts/_index_summary.json")
    if not summary_path.exists():
        return {"error": "no_summary", "data": None}
    try:
        data = json.loads(summary_path.read_text("utf-8"))
        return {"error": None, "data": data}
    except (json.JSONDecodeError, OSError) as e:
        return {"error": str(e), "data": None}


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
        from src.adapters.places.google_places import GooglePlacesSearcher, GooglePlacesRetriever
        kwargs["place_searcher"] = GooglePlacesSearcher()
        kwargs["place_retriever"] = GooglePlacesRetriever()

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


@app.post("/api/ablation")
async def api_ablation(req: PipelineRequest):
    """Solution Catalog あり/なしの比較実行。"""
    global _request_counter
    _request_counter += 1
    request_id = f"abl-{_request_counter}"

    from src.experiments.catalog_ablation import run_ablation

    use_live = req.live or _use_live
    mock_fn = None if use_live else _pipeline_mock

    orig_model = os.environ.get("EVAL_MODEL")
    if req.model and use_live:
        os.environ["EVAL_MODEL"] = req.model

    try:
        if use_live:
            result = run_ablation(request_id, req.query, llm_mock_fn=_pipeline_mock)
            # For live we can't easily use run_ablation's patching, so run manually
            from src.pipeline.restaurant_pipeline import run_restaurant_pipeline as _run
            with_cat = _run(f"{request_id}-with", req.query)
            without_cat = _run(
                f"{request_id}-without", req.query,
                catalog_path="/nonexistent/__no_catalog__.json")
            from src.experiments.catalog_ablation import _compute_diff
            result = {
                "query": req.query,
                "with_catalog": with_cat,
                "without_catalog": without_cat,
                "diff_summary": _compute_diff(with_cat, without_cat),
            }
        else:
            result = run_ablation(
                request_id, req.query, llm_mock_fn=_pipeline_mock)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Ablation failed")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if orig_model is not None:
            os.environ["EVAL_MODEL"] = orig_model
        elif "EVAL_MODEL" in os.environ and req.model:
            del os.environ["EVAL_MODEL"]

    # Auto-save to artifacts/
    _save_ablation_artifact(request_id, result)

    return result


def _save_ablation_artifact(request_id: str, result: dict) -> None:
    """Ablation 結果を artifacts/ に自動保存し、index と summary を更新する。"""
    try:
        from datetime import datetime, timezone
        from scripts.run_solution_catalog_live_ablation import (
            build_artifact_index,
            build_artifact_directory_summary,
        )

        artifacts_dir = Path("artifacts")
        artifacts_dir.mkdir(exist_ok=True)

        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        filename = f"{request_id}_{ts}"

        # Full JSON
        out_path = artifacts_dir / f"{filename}.json"
        out_path.write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + "\n", "utf-8")

        # Index
        index = build_artifact_index(result, artifact_path=str(out_path))
        index_path = out_path.with_suffix(".index.json")
        index_path.write_text(
            json.dumps(index, ensure_ascii=False, indent=2) + "\n", "utf-8")

        # Directory summary
        index_items = []
        for f in sorted(artifacts_dir.glob("*.index.json")):
            try:
                index_items.append(json.loads(f.read_text("utf-8")))
            except (json.JSONDecodeError, OSError):
                pass
        summary = build_artifact_directory_summary(index_items)
        (artifacts_dir / "_index_summary.json").write_text(
            json.dumps(summary, ensure_ascii=False, indent=2) + "\n", "utf-8")

        logger.info("Saved ablation artifact: %s", out_path)
    except Exception:
        logger.warning("Failed to save ablation artifact", exc_info=True)


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
    uvicorn.run("server:app", host=args.host, port=args.port,
                log_level="info", reload=True)


if __name__ == "__main__":
    main()
