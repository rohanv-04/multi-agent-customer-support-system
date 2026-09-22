from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class RiskDecision(str, Enum):
    AUTO_APPROVE = "AUTO_APPROVE"
    HUMAN_REVIEW = "HUMAN_REVIEW"
    BLOCK = "BLOCK"


class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class RiskFactor(BaseModel):
    factor_name: str
    score: float  # 0.0 to 1.0
    risk_contribution: str  # low, medium, high, critical
    evidence: str


class RiskEvaluationResult(BaseModel):
    risk_level: RiskLevel
    decision: RiskDecision
    reasons: List[str] = Field(default_factory=list)
    required_approval: str = "none"  # none, tier_1_lead, finance_specialist, fraud_operations
    factors: List[RiskFactor] = Field(default_factory=list)
    authorization_limit: float = 500.0
    confidence: float = 0.98
