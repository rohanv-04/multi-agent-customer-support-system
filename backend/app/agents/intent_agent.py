import re
from typing import Dict, Any
from .llm_client import llm_client

def run_intent_agent(user_goal: str, customer_id: str = "CUST1002") -> Dict[str, Any]:
    """Agent 1 — Intent & Goal Agent.

    Extracts user intent, entities (order_id, customer_id, reason), required actions, urgency, and confidence.
    """
    clean_goal = user_goal.strip()

    # Extract Order ID (e.g. ORD10001, ORD10002, ORD-10002)
    order_match = re.search(r"\b(ORD-?\d{5})\b", clean_goal, re.IGNORECASE)
    extracted_order = order_match.group(1).upper().replace("-", "") if order_match else None

    # Extract Customer ID if present in text
    cust_match = re.search(r"\b(CUST-?\d{4})\b", clean_goal, re.IGNORECASE)
    extracted_cust = cust_match.group(1).upper().replace("-", "") if cust_match else customer_id

    goal_lower = clean_goal.lower()

    # Determine intent
    intent = "unknown"
    required_actions = []
    urgency = "medium"
    confidence = 0.95

    if any(phrase in goal_lower for phrase in ["human", "agent", "representative", "speak to a person", "operator"]):
        intent = "human_escalation"
        urgency = "high"
        confidence = 0.98
        required_actions = ["prepare_escalation_dossier", "create_support_ticket", "transfer_to_human"]

    elif "policy" in goal_lower or (any(phrase in goal_lower for phrase in ["what is", "how do i", "rules", "warranty", "shipping time"]) and not any(a in goal_lower for a in ["refund me", "refund it", "process refund"])):
        intent = "policy_inquiry"
        urgency = "low"
        confidence = 0.94
        required_actions = ["retrieve_knowledge", "format_policy_response"]

    elif any(phrase in goal_lower for phrase in ["refund", "money back", "credit"]):
        intent = "refund_request"
        urgency = "high" if "delayed" in goal_lower or "urgent" in goal_lower else "medium"
        confidence = 0.96
        required_actions = [
            "validate_order",
            "retrieve_order_status",
            "retrieve_refund_policy",
            "check_refund_eligibility",
            "execute_refund",
            "verify_refund",
            "update_customer_memory"
        ]

    elif any(phrase in goal_lower for phrase in ["where is", "track", "status", "order"]) and extracted_order:
        intent = "order_status_inquiry"
        urgency = "medium"
        confidence = 0.95
        required_actions = ["retrieve_order_status", "evaluate_shipment_status"]

    elif any(phrase in goal_lower for phrase in ["cancel", "stop order"]):
        intent = "cancellation_request"
        urgency = "high"
        confidence = 0.93
        required_actions = ["validate_order", "check_cancellation_policy", "cancel_order"]

    else:
        intent = "general_inquiry"
        urgency = "low"
        confidence = 0.82
        required_actions = ["retrieve_knowledge", "general_assistance"]

    return {
        "intent": intent,
        "entities": {
            "order_id": extracted_order,
            "customer_id": extracted_cust,
            "raw_text": clean_goal
        },
        "required_actions": required_actions,
        "urgency": urgency,
        "confidence": confidence
    }
