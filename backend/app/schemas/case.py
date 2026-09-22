import datetime
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict, Field


class CaseStatus(str, Enum):
    NEW = "NEW"
    TRIAGING = "TRIAGING"
    INVESTIGATING = "INVESTIGATING"
    DECISION_PENDING = "DECISION_PENDING"
    ACTION_PENDING = "ACTION_PENDING"
    HUMAN_REVIEW = "HUMAN_REVIEW"
    VERIFYING = "VERIFYING"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"
    ESCALATED = "ESCALATED"


class CasePriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class CaseChannel(str, Enum):
    WEB_CHAT = "web_chat"
    EMAIL = "email"
    API = "api"
    PORTAL = "portal"


class MessageDirection(str, Enum):
    INBOUND = "inbound"
    OUTBOUND = "outbound"


class SenderType(str, Enum):
    CUSTOMER = "customer"
    AGENT = "agent"
    SUPERVISOR = "supervisor"
    SYSTEM = "system"


class EventType(str, Enum):
    CASE_CREATED = "case_created"
    STATUS_CHANGED = "status_changed"
    AGENT_STARTED = "agent_started"
    AGENT_COMPLETED = "agent_completed"
    TOOL_EXECUTED = "tool_executed"
    ESCALATION = "escalation"
    APPROVAL = "approval"
    RESOLUTION = "resolution"
    FAILURE = "failure"


# ----------------- REQUEST SCHEMAS -----------------

class CaseCreate(BaseModel):
    customer_id: str
    subject: str
    description: Optional[str] = None
    channel: Optional[str] = "web_chat"
    priority: Optional[str] = "medium"
    intent: Optional[str] = None
    organization_id: Optional[str] = "ORG-NOVACART"
    initial_message: Optional[str] = None
    conversation_id: Optional[str] = None


class CaseUpdate(BaseModel):
    status: Optional[str] = None
    priority: Optional[str] = None
    subject: Optional[str] = None
    description: Optional[str] = None
    intent: Optional[str] = None
    sentiment: Optional[str] = None
    actor: Optional[str] = "system"
    reason: Optional[str] = None


class CaseMessageCreate(BaseModel):
    body: str
    direction: Optional[str] = "outbound"
    channel: Optional[str] = "web_chat"
    sender_type: Optional[str] = "agent"
    sender_id: Optional[str] = None
    metadata_json: Optional[str] = None


# ----------------- RESPONSE SCHEMAS -----------------

class CaseMessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    case_id: str
    direction: str
    channel: str
    sender_type: str
    sender_id: Optional[str] = None
    body: str
    metadata_json: Optional[str] = None
    created_at: datetime.datetime


class CaseEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    case_id: str
    event_type: str
    from_status: Optional[str] = None
    to_status: Optional[str] = None
    actor: str
    summary: str
    details_json: Optional[str] = None
    created_at: datetime.datetime


class AgentRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    case_id: str
    task_id: Optional[str] = None
    agent_name: str
    started_at: datetime.datetime
    ended_at: Optional[datetime.datetime] = None
    status: str
    output_summary: Optional[str] = None
    confidence: Optional[float] = None
    error_info: Optional[str] = None
    created_at: datetime.datetime


class AgentActionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    case_id: Optional[str] = None
    task_id: Optional[str] = None
    agent_name: str
    action_type: str
    requested_by: Optional[str] = None
    status: str
    input_summary: Optional[str] = None
    output_summary: Optional[str] = None
    confidence: float
    duration_ms: int
    created_at: datetime.datetime


class AuditLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    case_id: Optional[str] = None
    entity_type: str
    entity_id: str
    action: str
    actor_type: str
    actor_id: str
    details_json: Optional[str] = None
    created_at: datetime.datetime


class TimelineItemResponse(BaseModel):
    id: str
    item_type: str  # message, event, agent_run, action, escalation, audit
    timestamp: datetime.datetime
    title: str
    description: str
    actor: str
    badge: Optional[str] = None
    status: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class CaseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: str
    customer_id: str
    conversation_id: Optional[str] = None
    channel: str
    subject: str
    description: Optional[str] = None
    intent: Optional[str] = None
    sentiment: str
    priority: str
    status: str
    sla_deadline: Optional[datetime.datetime] = None
    created_at: datetime.datetime
    updated_at: datetime.datetime
    resolved_at: Optional[datetime.datetime] = None


class CaseDetailResponse(CaseResponse):
    customer_name: Optional[str] = None
    customer_email: Optional[str] = None
    customer_tier: Optional[str] = None
    message_count: int = 0
    event_count: int = 0
    agent_run_count: int = 0
    action_count: int = 0
    is_sla_breached: bool = False
    sla_minutes_remaining: Optional[float] = None
