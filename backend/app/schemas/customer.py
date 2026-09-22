import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict, Field


class CustomerProfileSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    customer_id: str
    organization_id: str
    name: str
    email: str
    phone: Optional[str] = None
    account_status: str
    created_at: datetime.datetime


class CustomerLoyaltySchema(BaseModel):
    tier: str  # Standard, Silver, Gold, Platinum
    is_vip: bool
    lifetime_spend: float
    currency: str = "USD"
    order_count: int
    tenure_days: int
    perks: List[str] = Field(default_factory=list)


class CustomerOrderItemSchema(BaseModel):
    item_id: str
    name: str
    qty: int
    price: float


class CustomerOrderSummarySchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    order_id: str
    status: str  # Processing, Shipped, Delivered, Delayed, Cancelled, Refunded
    total_amount: float
    currency: str
    carrier: Optional[str] = None
    tracking_number: Optional[str] = None
    order_date: datetime.datetime
    expected_delivery: datetime.datetime
    actual_delivery: Optional[datetime.datetime] = None
    delay_reason: Optional[str] = None
    items: List[CustomerOrderItemSchema] = Field(default_factory=list)


class CustomerPaymentSummarySchema(BaseModel):
    payment_id: str
    order_id: str
    amount: float
    currency: str
    status: str  # paid, refunded, partial_refund, pending
    payment_method: str
    created_at: datetime.datetime


class CustomerRefundSummarySchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    refund_id: str
    order_id: str
    refund_amount: float
    currency: str
    status: str
    reason: str
    refund_method: str
    processed_at: datetime.datetime


class CustomerCaseSummarySchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    channel: str
    subject: str
    priority: str
    status: str
    intent: Optional[str] = None
    sentiment: str
    created_at: datetime.datetime
    resolved_at: Optional[datetime.datetime] = None


class CustomerComplaintSummarySchema(BaseModel):
    complaint_id: str
    source_type: str  # escalation, support_case
    severity: str
    issue: str
    status: str
    created_at: datetime.datetime


class CustomerResolutionSummarySchema(BaseModel):
    resolution_id: str
    case_id: Optional[str] = None
    order_id: Optional[str] = None
    resolution_type: str  # refund_issued, case_resolved, escalation_handled
    outcome_summary: str
    resolved_at: datetime.datetime


class CustomerEscalationSummarySchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    ticket_id: str
    case_id: Optional[str] = None
    summary: str
    reason: str
    status: str
    priority: str
    assigned_to: str
    created_at: datetime.datetime


class CustomerMemoryItemSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    memory_type: str
    key: str
    value: str
    updated_at: datetime.datetime


class CustomerActivityItemSchema(BaseModel):
    id: str
    activity_type: str  # order, case, refund, escalation, memory, payment
    timestamp: datetime.datetime
    title: str
    description: str
    badge: Optional[str] = None
    status: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class Customer360Response(BaseModel):
    profile: CustomerProfileSchema
    account_status: str
    loyalty: CustomerLoyaltySchema
    orders: List[CustomerOrderSummarySchema] = Field(default_factory=list)
    payments: List[CustomerPaymentSummarySchema] = Field(default_factory=list)
    refunds: List[CustomerRefundSummarySchema] = Field(default_factory=list)
    previous_cases: List[CustomerCaseSummarySchema] = Field(default_factory=list)
    cases: List[CustomerCaseSummarySchema] = Field(default_factory=list)  # backward compatible alias
    previous_complaints: List[CustomerComplaintSummarySchema] = Field(default_factory=list)
    previous_resolutions: List[CustomerResolutionSummarySchema] = Field(default_factory=list)
    escalations: List[CustomerEscalationSummarySchema] = Field(default_factory=list)
    memories: List[CustomerMemoryItemSchema] = Field(default_factory=list)
    open_cases_count: int = 0
    risk_assessment: Dict[str, Any] = Field(default_factory=dict)
