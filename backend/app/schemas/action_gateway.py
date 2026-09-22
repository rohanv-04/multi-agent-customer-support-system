import datetime
from enum import Enum
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field


class ActionType(str, Enum):
    REFUND = "refund"
    CANCELLATION = "cancellation"
    REPLACEMENT = "replacement"
    RESHIPMENT = "reshipment"
    TICKET_UPDATE = "ticket_update"
    CUSTOMER_UPDATE = "customer_update"
    EMAIL = "email"
    WHATSAPP_MESSAGE = "whatsapp_message"


class ActionStatus(str, Enum):
    EXECUTED = "EXECUTED"
    APPROVAL_PENDING = "APPROVAL_PENDING"
    BLOCKED = "BLOCKED"
    FAILED = "FAILED"
    VERIFIED = "VERIFIED"
    RETRYING = "RETRYING"


class ActionRequest(BaseModel):
    case_id: Optional[str] = None
    action_type: str
    requested_by: str = "Resolution Agent"
    parameters: Dict[str, Any] = Field(default_factory=dict)
    justification: str = ""
    risk_result: Optional[Dict[str, Any]] = None
    approval_required: bool = False
    customer_id: Optional[str] = None
    task_id: Optional[str] = None
    actor_role: Optional[str] = "agent"  # agent, supervisor, admin, system


class VerificationResult(BaseModel):
    verified: bool
    action_type: str
    expected_state: Dict[str, Any] = Field(default_factory=dict)
    actual_state: Dict[str, Any] = Field(default_factory=dict)
    mismatch_detected: bool = False
    mismatch_details: Optional[str] = None
    safe_to_retry: bool = False
    retry_count: int = 0
    should_replan: bool = False
    should_escalate: bool = False
    verification_summary: str = ""


class ActionResult(BaseModel):
    action_id: str
    status: str  # EXECUTED, APPROVAL_PENDING, BLOCKED, FAILED, VERIFIED
    external_reference: Optional[str] = None
    result: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None
    timestamp: datetime.datetime = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None))
    verification: Optional[VerificationResult] = None
    audit_id: Optional[int] = None
