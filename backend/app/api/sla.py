from typing import Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database.database import get_db
from ..services.sla_engine import sla_engine

router = APIRouter(prefix="/api/sla", tags=["sla"])


@router.get("/policies")
def get_sla_policies():
    """Returns the active enterprise SLA policy configurations across priority tiers."""
    return {
        "policies": {k: v.model_dump() for k, v in sla_engine.policies.items()}
    }


@router.get("/status")
def get_sla_status_dashboard(db: Session = Depends(get_db)):
    """
    Evaluates all active support cases and returns live SLA compliance and breach metrics.
    """
    try:
        return sla_engine.evaluate_all_active_cases(db)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to evaluate SLA statuses: {str(e)}")


@router.post("/evaluate")
def evaluate_and_escalate_sla(db: Session = Depends(get_db)):
    """
    Triggers an on-demand audit cycle across all active cases, auto-escalating any breached cases.
    """
    try:
        return sla_engine.evaluate_all_active_cases(db)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"SLA audit execution failed: {str(e)}")
