from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database.database import get_db
from ..database.models import SupportCase
from ..schemas.differentiation import (
    CustomerFrictionProfile,
    CaseDNA,
    NextBestActionResponse,
    SimilarCaseResult,
    AgentDebateRecord,
    RootCauseItem,
    KnowledgeGapResponse,
    SimulationRunRequest,
    SimulationRunResult,
    OperationalInsightResponse
)
from ..services.customer_friction_service import CustomerFrictionService
from ..services.case_dna_service import CaseDNAService
from ..services.next_best_action_service import NextBestActionEngine
from ..services.case_similarity_service import CaseSimilarityService
from ..services.root_cause_service import RootCauseService
from ..services.knowledge_gap_service import KnowledgeGapService
from ..services.simulation_service import SimulationService
from ..services.operational_intelligence_service import OperationalIntelligenceService
from ..agents.agent_debate import AgentDebateEngine
from ..agents.intake_agent import run_intake_agent
from ..services.customer_intelligence_service import CustomerIntelligenceService


router = APIRouter(tags=["SupportOS AI V2 Differentiation"])


# 1. Customer Friction Score
@router.get("/customers/{customer_id}/friction", response_model=CustomerFrictionProfile)
def get_customer_friction(customer_id: str, db: Session = Depends(get_db)):
    """Calculate and return real-time explainable customer friction profile."""
    return CustomerFrictionService.calculate_friction(db, customer_id)


# 2. Case DNA Fingerprint
@router.get("/cases/{case_id}/dna", response_model=CaseDNA)
def get_case_dna(case_id: str, db: Session = Depends(get_db)):
    """Retrieve or compute Case DNA fingerprint for capability-based orchestration."""
    case = db.query(SupportCase).filter(SupportCase.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail=f"Case {case_id} not found.")

    intake = run_intake_agent(case.subject, customer_id=case.customer_id)
    c360 = CustomerIntelligenceService.get_customer_360(db, case.customer_id)
    return CaseDNAService.generate_case_dna(db, case, intake, c360)


# 3. Next-Best-Action Engine
@router.get("/cases/{case_id}/next-action", response_model=NextBestActionResponse)
def get_next_best_action(case_id: str, db: Session = Depends(get_db)):
    """Evaluate multidimensional case state to formulate the next operational best action."""
    case = db.query(SupportCase).filter(SupportCase.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail=f"Case {case_id} not found.")

    intake = run_intake_agent(case.subject, customer_id=case.customer_id)
    c360 = CustomerIntelligenceService.get_customer_360(db, case.customer_id)
    dna = CaseDNAService.generate_case_dna(db, case, intake, c360)
    friction = CustomerFrictionService.calculate_friction(db, case.customer_id)

    return NextBestActionEngine.evaluate_next_best_action(
        db=db,
        case=case,
        case_dna=dna,
        friction_profile=friction
    )


# 4. Similar Cases / Historical Learning
@router.get("/cases/{case_id}/similar", response_model=List[SimilarCaseResult])
def get_similar_cases(case_id: str, limit: int = 5, db: Session = Depends(get_db)):
    """Retrieve top similar resolved historical cases as decision support evidence."""
    case = db.query(SupportCase).filter(SupportCase.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail=f"Case {case_id} not found.")

    intake = run_intake_agent(case.subject, customer_id=case.customer_id)
    c360 = CustomerIntelligenceService.get_customer_360(db, case.customer_id)
    dna = CaseDNAService.generate_case_dna(db, case, intake, c360)

    return CaseSimilarityService.find_similar_cases(db, case, dna, limit=limit)


# 5. Agent Conflicts & Debate
@router.get("/cases/{case_id}/conflicts", response_model=Optional[AgentDebateRecord])
def get_case_conflicts(case_id: str, db: Session = Depends(get_db)):
    """Retrieve specialist agent debate positions and arbitrated resolution for a case."""
    case = db.query(SupportCase).filter(SupportCase.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail=f"Case {case_id} not found.")

    # Return structured debate record if applicable
    return AgentDebateEngine.evaluate_and_resolve_conflict(db, case)


# 6. Root Cause Intelligence
@router.get("/root-causes", response_model=List[RootCauseItem])
def get_root_causes(db: Session = Depends(get_db)):
    """List detected patterns and confirmed systemic root causes."""
    return RootCauseService.get_all(db)


@router.get("/root-causes/{root_cause_id}", response_model=RootCauseItem)
def get_root_cause_by_id(root_cause_id: str, db: Session = Depends(get_db)):
    """Retrieve single root cause cluster with full evidence and linked cases."""
    rc = RootCauseService.get_by_id(db, root_cause_id)
    if not rc:
        raise HTTPException(status_code=404, detail=f"Root cause {root_cause_id} not found.")
    return rc


# 7. Knowledge Gaps
@router.get("/knowledge-gaps", response_model=List[KnowledgeGapResponse])
def get_knowledge_gaps(db: Session = Depends(get_db)):
    """List cataloged policy gaps and documentation blindspots."""
    return KnowledgeGapService.get_all(db)


# 8. AI Simulation Lab
@router.get("/simulations/scenarios")
def get_simulation_scenarios(db: Session = Depends(get_db)):
    """List pre-configured test scenarios for AI Simulation Lab."""
    return SimulationService.get_preconfigured_scenarios(db)


@router.post("/simulations", response_model=SimulationRunResult)
def run_simulation(request: SimulationRunRequest, db: Session = Depends(get_db)):
    """Execute a fully sandboxed multi-agent simulation with zero real business mutations."""
    return SimulationService.run_simulation(db, request)


@router.get("/simulations/{run_id}", response_model=SimulationRunResult)
def get_simulation_run(run_id: str, db: Session = Depends(get_db)):
    """Retrieve execution trace and outcome of a simulation run."""
    run = SimulationService.get_run_by_id(db, run_id)
    if not run:
        raise HTTPException(status_code=404, detail=f"Simulation run {run_id} not found.")
    return run


# 9. Operations Intelligence
@router.get("/operations/insights", response_model=List[OperationalInsightResponse])
def get_operational_insights(db: Session = Depends(get_db)):
    """Retrieve real-time operational findings, bottlenecks, and efficiency metrics."""
    return OperationalIntelligenceService.generate_insights(db)
