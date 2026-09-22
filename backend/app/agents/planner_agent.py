from typing import Dict, Any, List

def run_planner_agent(user_goal: str, intent_data: Dict[str, Any]) -> Dict[str, Any]:
    """Agent 2 — Planning Agent.

    Constructs a structured, dynamic execution plan based on user intent, extracted entities,
    and business domain rules.
    """
    intent = intent_data.get("intent", "general_inquiry")
    entities = intent_data.get("entities", {})
    order_id = entities.get("order_id")

    steps: List[str] = []

    if intent == "refund_request":
        if order_id:
            steps = [
                f"Validate customer authentication and retrieve status for order {order_id}",
                "Retrieve applicable corporate refund and delay policies via RAG",
                f"Evaluate refund eligibility for {order_id} using Eligibility Tool",
                "Execute financial refund transaction if verified eligible",
                "Verify refund transaction receipt and update persistent memory",
                "Validate comprehensive resolution with Critic Agent",
                "Synthesize final customer response"
            ]
        else:
            steps = [
                "Prompt customer for missing Order ID",
                "Retrieve general refund and return policy terms",
                "Awaiting customer clarification"
            ]

    elif intent == "order_status_inquiry":
        steps = [
            f"Retrieve live tracking and carrier telemetry for order {order_id}",
            "Retrieve shipping SLAs and transit policy guidelines",
            "Assess delivery health and delay diagnostics",
            "Validate status accuracy with Critic Agent",
            "Format customer shipment update"
        ]

    elif intent == "policy_inquiry":
        steps = [
            "Perform semantic RAG retrieval across corporate knowledge documents",
            "Ground policy conditions against customer context",
            "Validate policy compliance with Critic Agent",
            "Synthesize comprehensive policy answer"
        ]

    elif intent == "human_escalation":
        steps = [
            "Compile historical context, customer tier, and reason for transfer",
            "Generate formal Escalation Dossier with action/tool audit trail",
            "Create high-priority support ticket in Human Support Queue",
            "Deliver reassurance and ticket ID to customer"
        ]

    elif intent == "cancellation_request":
        steps = [
            f"Retrieve order {order_id} fulfillment status",
            "Check cancellation policy cutoff window (< 60 minutes)",
            "Execute cancellation reversal if pre-fulfillment",
            "Validate cancellation with Critic Agent",
            "Confirm cancellation receipt with customer"
        ]

    else:
        steps = [
            "Analyze customer inquiry and retrieve relevant knowledge",
            "Synthesize helpful response grounded in NovaCart guidelines",
            "Validate output with Critic Agent"
        ]

    return {
        "goal": user_goal,
        "steps": steps,
        "confidence": 0.93
    }
