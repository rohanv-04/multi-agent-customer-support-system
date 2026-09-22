from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from ..schemas.evaluation import (
    EvaluationBenchmarkCase,
    EvaluationRunSchema,
    EvaluationCategory
)
from ..services.evaluation_engine import evaluation_engine
from ..services.evaluation_dataset import get_benchmarks

router = APIRouter(prefix="/api/evaluations", tags=["evaluations"])


class RunEvaluationRequest(BaseModel):
    name: Optional[str] = None
    categories: Optional[List[str]] = None
    max_cases: Optional[int] = None


@router.get("/benchmarks", response_model=List[EvaluationBenchmarkCase])
def list_benchmark_cases(category: Optional[str] = None):
    """
    List standardized benchmark test cases across the 8 evaluation categories.
    """
    return get_benchmarks(category)


@router.post("/run", response_model=EvaluationRunSchema)
def trigger_evaluation_run(req: RunEvaluationRequest):
    """
    Executes an evaluation benchmark suite, calculating intent, policy, decision, tool, verification, escalation accuracy, hallucination rate, latency, and cost.
    """
    try:
        return evaluation_engine.run_suite(
            name=req.name,
            categories=req.categories,
            max_cases=req.max_cases
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Evaluation run failed: {str(e)}")


@router.get("/runs", response_model=List[EvaluationRunSchema])
def list_evaluation_runs():
    """Returns all previous evaluation run dossiers."""
    return evaluation_engine.list_runs()


@router.get("/runs/{run_id}", response_model=EvaluationRunSchema)
def get_evaluation_run_detail(run_id: str):
    """Retrieves full evaluation run breakdown by benchmark case."""
    run = evaluation_engine.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail=f"Evaluation run '{run_id}' not found.")
    return run
