import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict, Field


class ToolCallTrace(BaseModel):
    """Execution telemetry for a single tool call."""
    id: Optional[int] = None
    tool_name: str
    input_params: Dict[str, Any] = Field(default_factory=dict)
    output_result: Dict[str, Any] = Field(default_factory=dict)
    status: str = "success"  # success, failure
    duration_ms: int = 0
    error_message: Optional[str] = None
    timestamp: datetime.datetime = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None))


class TokenCostMetadata(BaseModel):
    """Estimated token count and inference cost."""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cost_usd: float = 0.0


class AgentRunTraceNode(BaseModel):
    """
    Detailed hierarchical trace node for a specialist agent run.
    Stores concise reasoning summaries and evidence only (never raw chain-of-thought).
    """
    id: Optional[int] = None
    agent_name: str
    agent_type: str  # intake, customer_intelligence, investigation, policy, decision, risk, action, verification, communication
    started_at: datetime.datetime
    ended_at: Optional[datetime.datetime] = None
    latency_ms: int = 0
    status: str = "completed"  # running, completed, failed, skipped
    confidence: Optional[float] = None
    input_metadata: Dict[str, Any] = Field(default_factory=dict)
    output_summary: Optional[str] = None
    evidence_summary: Optional[str] = None
    retry_count: int = 0
    error: Optional[str] = None
    tool_calls: List[ToolCallTrace] = Field(default_factory=list)
    token_usage: TokenCostMetadata = Field(default_factory=TokenCostMetadata)


class CaseExecutionTrace(BaseModel):
    """
    Full hierarchical execution tree for a SupportCase.
    Tree structure:
    Case
    ├── Intake Agent
    ├── Customer Intelligence
    ├── Investigation
    │   ├── tool call
    │   ├── tool call
    │   └── tool call
    ├── Policy Agent
    ├── Decision Agent
    ├── Risk Agent
    ├── Action Agent
    ├── Verification Agent
    └── Communication Agent
    """
    case_id: str
    task_id: Optional[str] = None
    customer_id: str
    subject: str
    channel: str
    priority: str
    status: str
    total_latency_ms: int = 0
    total_cost_usd: float = 0.0
    created_at: datetime.datetime
    tree_nodes: List[AgentRunTraceNode] = Field(default_factory=list)


class AgentPerformanceMetrics(BaseModel):
    """Aggregated performance metrics for an individual specialist agent."""
    agent_name: str
    total_runs: int
    success_count: int
    failure_count: int
    success_rate: float
    avg_latency_ms: float
    avg_confidence: float
    avg_cost_usd: float
    total_retries: int


class ToolPerformanceMetrics(BaseModel):
    """Aggregated operational metrics for an individual tool."""
    tool_name: str
    total_calls: int
    success_count: int
    failure_count: int
    success_rate: float
    avg_duration_ms: float
    last_called_at: Optional[datetime.datetime] = None


class FailureAnalysisReport(BaseModel):
    """Breakdown of system exceptions, replan loops, and escalation triggers."""
    total_cases_analyzed: int
    failed_cases_count: int
    escalated_cases_count: int
    replan_loop_count: int
    common_errors: List[Dict[str, Any]] = Field(default_factory=list)
    agent_failure_distribution: Dict[str, int] = Field(default_factory=dict)
    tool_failure_distribution: Dict[str, int] = Field(default_factory=dict)


class AuditLogFilter(BaseModel):
    """Query parameters for searchable enterprise audit ledger."""
    organization_id: Optional[str] = None
    case_id: Optional[str] = None
    entity_type: Optional[str] = None
    action: Optional[str] = None
    actor_type: Optional[str] = None
    search: Optional[str] = None
    from_date: Optional[datetime.datetime] = None
    to_date: Optional[datetime.datetime] = None
    limit: int = 50
    offset: int = 0
