from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class InvestigationFinding(BaseModel):
    category: str  # order, shipment, payment, policy, customer_status
    observation: str
    impact: str  # positive, neutral, risk, blocker
    confidence: float = 0.95


class InvestigationEvidence(BaseModel):
    source: str  # database.orders, database.refunds, carrier.tracking, rag.policies, customer.memory
    fact: str
    verified: bool = True
    timestamp: Optional[str] = None


class InvestigationResult(BaseModel):
    case_id: str
    findings: List[InvestigationFinding] = Field(default_factory=list)
    evidence: List[InvestigationEvidence] = Field(default_factory=list)
    data_sources: List[str] = Field(default_factory=list)
    unresolved_questions: List[str] = Field(default_factory=list)
    recommended_next_step: str
    investigation_status: str = "complete"  # complete, partial, needs_customer_input, escalate
