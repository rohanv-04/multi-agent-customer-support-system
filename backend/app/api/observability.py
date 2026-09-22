from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database.database import get_db
from ..schemas.observability import (
    CaseExecutionTrace,
    AgentPerformanceMetrics,
    ToolPerformanceMetrics,
    FailureAnalysisReport
)
from ..services.observability_service import observability_service

router = APIRouter(prefix="/api/observability", tags=["observability"])


@router.get("/cases/{case_id}/trace", response_model=CaseExecutionTrace)
def get_case_trace(case_id: str, db: Session = Depends(get_db)):
    """
    Retrieves the hierarchical execution trace for a SupportCase:
    Case -> Intake -> Customer Intelligence -> Investigation (Tools) -> Policy -> Decision -> Risk -> Action -> Verification -> Communication.
    """
    try:
        return observability_service.get_case_execution_trace(db, case_id)
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate case trace: {str(e)}")


@router.get("/agents", response_model=List[AgentPerformanceMetrics])
def get_agent_performance_metrics(db: Session = Depends(get_db)):
    """
    Returns aggregated operational telemetry per specialist agent (success rate, avg latency, avg confidence, retries).
    """
    try:
        return observability_service.get_agent_performance(db)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load agent performance: {str(e)}")


@router.get("/tools", response_model=List[ToolPerformanceMetrics])
def get_tool_performance_metrics(db: Session = Depends(get_db)):
    """
    Returns aggregated execution telemetry for all enterprise database tools.
    """
    try:
        return observability_service.get_tool_performance(db)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load tool performance: {str(e)}")


@router.get("/failures", response_model=FailureAnalysisReport)
def get_failure_analysis_report(db: Session = Depends(get_db)):
    """
    Analyzes system failure loops, replan occurrences, and escalation drivers.
    """
    try:
        return observability_service.get_failure_analysis(db)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to analyze failures: {str(e)}")
