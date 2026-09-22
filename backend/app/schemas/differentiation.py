import datetime
from typing import Dict, Any, List, Optional
from enum import Enum
from pydantic import BaseModel, Field


class FrictionLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class FrictionFactor(BaseModel):
    factor_type: str  # recent_cases, repeat_contacts, failed_deliveries, delayed_orders, escalations, long_resolution, transfers, unresolved_cases, sla_breaches, refunds, contact_velocity
    label: str
    impact_score: float
    description: str
    raw_signal: Any = None


class CustomerFrictionProfile(BaseModel):
    customer_id: str
    score: float = Field(..., ge=0.0, le=100.0)
    level: FrictionLevel
    contributing_factors: List[FrictionFactor] = Field(default_factory=list)
    recent_trend: str = "stable"  # improving, stable, escalating
    affected_cases: List[str] = Field(default_factory=list)
    calculated_at: datetime.datetime = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None))


class CaseDNA(BaseModel):
    case_id: str
    intent: str
    sub_intent: Optional[str] = None
    severity: str = "medium"  # low, medium, high, critical
    urgency: str = "medium"   # low, medium, high, urgent
    customer_value: str = "Standard"
    operational_risk: str = "low"  # low, medium, high, critical
    policy_complexity: str = "standard"  # simple, standard, complex, ambiguous
    sla_risk: str = "low"  # low, elevated, high, breached
    fraud_risk_score: float = 0.0
    channel: str = "web_chat"
    affected_business_area: str = "logistics"  # logistics, billing, hardware, policy, security
    required_capabilities: List[str] = Field(default_factory=list)
    fingerprint_hash: Optional[str] = None
    created_at: datetime.datetime = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None))


class RootCauseStatus(str, Enum):
    DETECTED_PATTERN = "DETECTED_PATTERN"
    CONFIRMED_ROOT_CAUSE = "CONFIRMED_ROOT_CAUSE"
    MITIGATED = "MITIGATED"
    RESOLVED = "RESOLVED"


class RootCauseEvidenceItem(BaseModel):
    evidence_type: str
    description: str
    raw_data: Optional[Dict[str, Any]] = None
    confidence: float = 1.0


class RootCauseItem(BaseModel):
    id: str
    category: str
    title: str
    description: str
    confidence: float
    status: RootCauseStatus
    affected_cases_count: int = 0
    affected_customers_count: int = 0
    evidence: List[RootCauseEvidenceItem] = Field(default_factory=list)
    first_detected: datetime.datetime
    last_detected: datetime.datetime


class NextBestActionAlternative(BaseModel):
    action_type: str
    label: str
    confidence: float
    reason: str
    risk_level: str = "low"


class NextBestActionResponse(BaseModel):
    case_id: str
    recommended_action: str
    action_type: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    justification: str
    alternatives: List[NextBestActionAlternative] = Field(default_factory=list)
    evidence: List[str] = Field(default_factory=list)
    policy_basis: str
    risk_level: str = "low"
    requires_approval: bool = False
    required_role: str = "agent"


class SelfHealingReport(BaseModel):
    case_id: Optional[str] = None
    task_id: Optional[str] = None
    failure_type: str
    error_message: str
    recovery_attempted: str
    retry_count: int = 1
    recovery_successful: bool = False
    final_disposition: str = "resolved"
    details: Optional[Dict[str, Any]] = None


class ConversationIntegrityResult(BaseModel):
    is_approved: bool
    issues_detected: List[str] = Field(default_factory=list)
    fact_check_passed: bool = True
    policy_check_passed: bool = True
    action_status_verified: bool = True
    revised_content: Optional[str] = None
    requires_human_escalation: bool = False
    audit_notes: str = ""


class KnowledgeGapResponse(BaseModel):
    id: str
    topic: str
    occurrences: int
    affected_cases: List[str] = Field(default_factory=list)
    evidence: List[str] = Field(default_factory=list)
    severity: str = "medium"
    status: str = "OPEN"
    suggested_documentation_topic: Optional[str] = None
    detected_at: datetime.datetime


class SimulationScenarioCreate(BaseModel):
    name: str
    description: str
    customer_profile: Dict[str, Any]
    issue_description: str
    system_conditions: Dict[str, Any] = Field(default_factory=dict)


class SimulationRunRequest(BaseModel):
    scenario_id: Optional[str] = None
    customer_id: Optional[str] = "CUST1002"
    customer_tier: Optional[str] = "Enterprise VIP"
    issue_description: str
    system_conditions: Dict[str, Any] = Field(default_factory=dict)  # e.g. {"carrier_api_down": True, "refund_limit": 300}


class SimulationRunResult(BaseModel):
    run_id: str
    scenario_id: Optional[str] = None
    status: str
    started_at: datetime.datetime
    completed_at: Optional[datetime.datetime] = None
    total_duration_ms: int = 0
    safety_verified: bool = True  # Guarantees no real financial or state mutations occurred
    case_dna: Optional[Dict[str, Any]] = None
    friction_profile: Optional[Dict[str, Any]] = None
    execution_trace: List[Dict[str, Any]] = Field(default_factory=list)
    agent_outputs: List[Dict[str, Any]] = Field(default_factory=list)
    simulated_tool_calls: List[Dict[str, Any]] = Field(default_factory=list)
    final_outcome: Dict[str, Any] = Field(default_factory=dict)


class AgentPosition(BaseModel):
    agent_name: str
    conclusion: str
    evidence: List[str] = Field(default_factory=list)
    confidence: float
    concerns: List[str] = Field(default_factory=list)
    recommended_action: str


class AgentDebateRecord(BaseModel):
    case_id: str
    positions: Dict[str, AgentPosition] = Field(default_factory=dict)
    conflicting_points: List[str] = Field(default_factory=list)
    resolution_rationale: str
    final_action_chosen: str
    resolved_by: str = "Decision Agent"
    timestamp: datetime.datetime = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None))


class SimilarCaseResult(BaseModel):
    case_id: str
    similarity_score: float
    intent: str
    subject: str
    resolution_summary: str
    outcome: str
    was_escalated: bool
    channel: str


class OperationalInsightResponse(BaseModel):
    id: str
    category: str
    title: str
    observation: str
    severity: str  # info, warning, critical
    metrics: Dict[str, Any] = Field(default_factory=dict)
    generated_at: datetime.datetime
