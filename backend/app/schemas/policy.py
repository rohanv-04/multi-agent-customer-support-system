from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class PolicyCondition(BaseModel):
    name: str
    met: bool
    details: str
    clause_reference: Optional[str] = None


class PolicyException(BaseModel):
    name: str
    applies: bool
    reason: str


class PolicyEvidenceItem(BaseModel):
    source_document: str
    section: str
    text: str
    relevance_score: float = 0.95


class PolicyEvaluationResult(BaseModel):
    policy_name: str
    applicable: bool
    eligibility: bool
    conditions: List[PolicyCondition] = Field(default_factory=list)
    exceptions: List[PolicyException] = Field(default_factory=list)
    evidence: List[PolicyEvidenceItem] = Field(default_factory=list)
    confidence: float = 0.95
    requires_human_review: bool = False
    unresolved_conflicts: List[str] = Field(default_factory=list)
