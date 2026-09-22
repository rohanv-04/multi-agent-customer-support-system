from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class IntakeExtractionResult(BaseModel):
    intent: str  # refund_request, order_status_inquiry, policy_inquiry, cancellation_request, human_escalation, general_inquiry
    sub_intent: Optional[str] = None  # severe_delay_refund, damaged_item_refund, tracking_lookup, return_window_query, live_agent_handoff
    order_id: Optional[str] = None
    customer_id: Optional[str] = None
    product: Optional[str] = None
    requested_action: str  # issue_refund, track_shipment, cancel_order, explain_policy, escalate_to_human, general_assist
    urgency: str  # low, medium, high, urgent
    sentiment: str  # positive, neutral, negative, frustrated
    priority_indicators: List[str] = Field(default_factory=list)
    relevant_entities: Dict[str, Any] = Field(default_factory=dict)
    confidence: float = 0.95
