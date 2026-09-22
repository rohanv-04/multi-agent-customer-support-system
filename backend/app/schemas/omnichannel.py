import datetime
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict, Field


class ChannelType(str, Enum):
    WEB_CHAT = "web_chat"
    EMAIL = "email"
    WHATSAPP = "whatsapp"
    API = "api"
    SUPPORT_FORM = "support_form"


class SupportRequest(BaseModel):
    """
    Normalized omnichannel support request ingested from any source channel.
    Business agents process this standard representation without hardcoded channel logic.
    """
    request_id: str = Field(description="Unique message/event ID or idempotency key for deduplication")
    channel: ChannelType = Field(description="Originating communication channel")
    customer_id: Optional[str] = Field(default=None, description="Known customer ID if pre-authenticated")
    sender_identifier: str = Field(description="Email, phone number, API client ID, or user handle")
    sender_name: Optional[str] = Field(default=None, description="Sender display name if available")
    subject: Optional[str] = Field(default=None, description="Inquiry subject line")
    body: str = Field(description="Normalized textual inquiry/message content")
    conversation_id: Optional[str] = Field(default=None, description="Existing conversation/thread ID if continuing a session")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Channel metadata e.g. headers, form fields, attachments")
    timestamp: datetime.datetime = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None))


class InboundProcessingResult(BaseModel):
    """Result of normalizing and ingesting an inbound support message."""
    request_id: str
    channel: str
    is_duplicate: bool
    customer_id: str
    case_id: Optional[str] = None
    status: str
    message: str
    ai_response: Optional[str] = None


class ProviderMessageResponse(BaseModel):
    """Result of dispatching an outbound communication through a channel provider."""
    provider_name: str
    channel: ChannelType
    recipient: str
    message_id: str
    status: str  # sent, queued, failed
    delivered_at: datetime.datetime
    details: Optional[Dict[str, Any]] = None


# ----------------- PROACTIVE SUPPORT SCHEMAS -----------------

class BusinessEventType(str, Enum):
    SHIPMENT_DELAY = "shipment_delay"
    PAYMENT_FAILURE = "payment_failure"
    REPEATED_FAILED_DELIVERY = "repeated_failed_delivery"
    PRODUCT_ISSUE = "product_issue"
    ABNORMAL_SUPPORT_ACTIVITY = "abnormal_support_activity"
    SLA_RISK = "sla_risk"


class BusinessEventPayload(BaseModel):
    """Standardized event emitted by external operational or logistics systems."""
    event_id: str
    event_type: BusinessEventType
    customer_id: str
    order_id: Optional[str] = None
    severity: str = "medium"  # low, medium, high, critical
    details: Dict[str, Any] = Field(default_factory=dict)
    source_system: str = "LogisticsEngine"
    timestamp: datetime.datetime = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None))


class ProactiveImpactResult(BaseModel):
    """Impact assessment and proactive resolution recommendation."""
    event_id: str
    event_type: str
    customer_id: str
    impact_level: str  # low, medium, high, severe
    case_created: bool
    case_id: Optional[str] = None
    action_taken: str
    outreach_channel: str
    outreach_message: str
    compensation_granted: Optional[str] = None
    reasoning: str


# ----------------- SLA ENGINE SCHEMAS -----------------

class SLABreachStatus(str, Enum):
    OK = "OK"
    APPROACHING_BREACH = "APPROACHING_BREACH"
    BREACHED = "BREACHED"


class SLAPolicyConfig(BaseModel):
    priority: str
    standard_target_hours: float
    vip_target_hours: float
    warning_threshold_ratio: float = 0.20  # Warn when 20% or less time remaining


class SLACheckResult(BaseModel):
    case_id: str
    priority: str
    customer_tier: str
    sla_deadline: datetime.datetime
    remaining_minutes: float
    breach_status: SLABreachStatus
    is_breached: bool
    is_approaching_breach: bool
    auto_escalated: bool = False
    escalation_reason: Optional[str] = None
