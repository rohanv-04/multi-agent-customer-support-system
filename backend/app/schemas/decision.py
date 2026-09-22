from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class DecisionType(str, Enum):
    RESOLVE = "resolve"
    REFUND = "refund"
    REPLACEMENT = "replacement"
    RESHIP = "reship"
    CANCELLATION = "cancellation"
    INFORMATION_REQUEST = "information_request"
    MONITOR = "monitor"
    ESCALATION = "escalation"


class DecisionResult(BaseModel):
    decision_type: DecisionType
    target_entity_id: Optional[str] = None
    parameters: Dict[str, Any] = Field(default_factory=dict)
    rationale: str
    policy_reference: Optional[str] = None
    evidence_summary: List[str] = Field(default_factory=list)
    recommended_action_name: str
    confidence: float = 0.95
