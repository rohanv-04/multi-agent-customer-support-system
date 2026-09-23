from typing import Dict, Any, Optional, List
from .intake_agent import run_intake_agent
from ..schemas.intake import IntakeExtractionResult

def run_intent_agent(
    user_goal: str,
    customer_id: str = "CUST1002",
    conversation_history: Optional[List[Dict[str, Any]]] = None,
    case_context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Agent 1 — Intent & Goal Extraction (Evolved with structured Intake Extraction).

    Returns backward-compatible dictionary while enforcing typed extraction underneath.
    """
    intake = run_intake_agent(
        user_goal=user_goal,
        customer_id=customer_id,
        conversation_history=conversation_history,
        case_context=case_context
    )

    required_actions = []
    if intake.intent == "human_escalation":
        required_actions = ["prepare_escalation_dossier", "create_support_ticket", "transfer_to_human"]
    elif intake.intent == "policy_inquiry":
        required_actions = ["retrieve_knowledge", "format_policy_response"]
    elif intake.intent == "refund_request":
        required_actions = [
            "validate_order",
            "retrieve_order_status",
            "retrieve_refund_policy",
            "check_refund_eligibility",
            "execute_refund",
            "verify_refund",
            "update_customer_memory"
        ]
    elif intake.intent == "order_status_inquiry":
        required_actions = ["retrieve_order_status", "evaluate_shipment_status"]
    elif intake.intent == "cancellation_request":
        required_actions = ["validate_order", "check_cancellation_policy", "cancel_order"]
    else:
        required_actions = ["retrieve_knowledge", "general_assistance"]

    return {
        "intent": intake.intent,
        "sub_intent": intake.sub_intent,
        "product": intake.product,
        "requested_action": intake.requested_action,
        "sentiment": intake.sentiment,
        "priority_indicators": intake.priority_indicators,
        "entities": intake.relevant_entities,
        "required_actions": required_actions,
        "urgency": intake.urgency,
        "confidence": intake.confidence,
        "_intake_model": intake.model_dump()
    }
