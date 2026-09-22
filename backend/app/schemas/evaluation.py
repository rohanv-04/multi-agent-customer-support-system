import datetime
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict, Field


class EvaluationCategory(str, Enum):
    DELIVERY_ISSUES = "delivery_issues"
    REFUNDS = "refunds"
    CANCELLATIONS = "cancellations"
    BILLING = "billing"
    POLICY_QUESTIONS = "policy_questions"
    ESCALATION = "escalation"
    TOOL_FAILURES = "tool_failures"
    AMBIGUOUS_REQUESTS = "ambiguous_requests"


class EvaluationBenchmarkCase(BaseModel):
    """Ground-truth evaluation benchmark item."""
    benchmark_id: str
    category: EvaluationCategory
    title: str
    user_goal: str
    customer_id: str = "CUST1002"
    expected_intent: str
    expected_decision: str
    expected_policy: Optional[str] = None
    expected_escalation: bool = False
    expected_tools: List[str] = Field(default_factory=list)
    description: str = ""


class EvaluationCaseResult(BaseModel):
    """Outcome of evaluating an individual benchmark case against live agent workflow."""
    benchmark_id: str
    category: str
    user_goal: str
    is_passed: bool
    score: float  # 0.0 to 1.0

    # Accuracy dimensions
    intent_match: bool
    policy_match: bool
    decision_match: bool
    tool_match: bool
    verification_match: bool
    escalation_match: bool
    hallucination_detected: bool

    # Actual vs Expected
    expected_intent: str
    actual_intent: Optional[str] = None
    expected_decision: str
    actual_decision: Optional[str] = None
    expected_policy: Optional[str] = None
    actual_policy: Optional[str] = None
    expected_escalation: bool
    actual_escalation: bool

    # Telemetry
    latency_ms: int
    estimated_cost_usd: float
    error: Optional[str] = None
    response_summary: Optional[str] = None


class EvaluationMetricSummary(BaseModel):
    """Aggregated evaluation metrics for a test suite run."""
    intent_accuracy: float = 0.0
    policy_accuracy: float = 0.0
    decision_accuracy: float = 0.0
    tool_execution_accuracy: float = 0.0
    verification_accuracy: float = 0.0
    escalation_accuracy: float = 0.0
    hallucination_rate: float = 0.0
    avg_latency_ms: float = 0.0
    total_cost_usd: float = 0.0


class EvaluationRunSchema(BaseModel):
    """Full evaluation run dossier."""
    run_id: str
    name: str
    dataset_name: str
    status: str  # completed, running, failed
    total_cases: int
    passed_cases: int
    failed_cases: int
    pass_rate: float
    metrics: EvaluationMetricSummary
    cases: List[EvaluationCaseResult] = Field(default_factory=list)
    created_at: datetime.datetime = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None))
