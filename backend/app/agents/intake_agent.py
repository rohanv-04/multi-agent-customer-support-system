import re
from typing import Optional, List, Dict, Any
from ..schemas.intake import IntakeExtractionResult

CATALOG_PRODUCTS = {
    "headphones": "Sony WH-1000XM5 Wireless Headphones",
    "sony": "Sony WH-1000XM5 Wireless Headphones",
    "ipad": "Apple iPad Pro 11-inch M4 256GB",
    "apple": "Apple iPad Pro 11-inch M4 256GB",
    "keyboard": "Mechanical Gaming Keyboard RGB",
    "chair": "Ergonomic Mesh Executive Chair",
    "monitor": "Ultra-wide Curved Gaming Monitor 34-inch"
}

def run_intake_agent(
    user_goal: str,
    customer_id: str = "CUST1002",
    conversation_history: Optional[List[Dict[str, Any]]] = None,
    case_context: Optional[Dict[str, Any]] = None
) -> IntakeExtractionResult:
    """Agent 1 — Intake & Intent Agent.

    Extracts structured intent, sub-intent, order IDs, product mentions,
    requested actions, urgency, sentiment, priority indicators, and entities into a Pydantic model.
    Maintains multi-turn context across conversational turns.
    """
    clean_goal = user_goal.strip()
    goal_lower = clean_goal.lower()

    # 1. Extract Order ID from current user message
    order_match = re.search(r"\b(ORD-?\d{4,6})\b", clean_goal, re.IGNORECASE)
    if not order_match:
        # Check for standalone numbers like "10291" or "10002" if preceded by "it's", "order", "number", "#"
        standalone_match = re.search(r"(?:order|it's|is|#)\s*[:#-]?\s*(\d{4,6})\b", clean_goal, re.IGNORECASE)
        if standalone_match:
            extracted_order = f"ORD{standalone_match.group(1)}"
        else:
            extracted_order = None
    else:
        extracted_order = order_match.group(1).upper().replace("-", "")

    # Multi-turn context memory: inherit order ID from prior conversation turns if not provided
    if not extracted_order and conversation_history:
        for msg in reversed(conversation_history):
            content = msg.get("content", "") or ""
            prior_match = re.search(r"\b(ORD-?\d{4,6})\b", content, re.IGNORECASE)
            if prior_match:
                extracted_order = prior_match.group(1).upper().replace("-", "")
                break
            prior_standalone = re.search(r"(?:order|it's|is|#)\s*[:#-]?\s*(\d{4,6})\b", content, re.IGNORECASE)
            if prior_standalone:
                extracted_order = f"ORD{prior_standalone.group(1)}"
                break

    # 2. Extract Customer ID
    cust_match = re.search(r"\b(CUST-?\d{4})\b", clean_goal, re.IGNORECASE)
    extracted_cust = cust_match.group(1).upper().replace("-", "") if cust_match else customer_id

    # 3. Detect Product
    detected_product = None
    for keyword, product_name in CATALOG_PRODUCTS.items():
        if keyword in goal_lower:
            detected_product = product_name
            break

    # 4. Detect Intent & Sub-intent & Requested Action
    priority_indicators: List[str] = []
    entities: Dict[str, Any] = {
        "order_id": extracted_order,
        "customer_id": extracted_cust,
        "product": detected_product,
        "raw_text": clean_goal
    }

    # Sentiment analysis
    frustrated_terms = ["ridiculous", "terrible", "unacceptable", "angry", "furious", "worst", "fraud", "scam", "overdue", "still waiting", "stole"]
    negative_terms = ["delayed", "late", "broken", "issue", "problem", "missing", "cancel", "wrong", "lost", "hasn't arrived", "has not arrived", "haven't arrived"]
    positive_terms = ["thank", "great", "appreciate", "helpful", "good", "pleased", "fast"]

    if any(term in goal_lower for term in frustrated_terms):
        sentiment = "frustrated"
        priority_indicators.append("frustrated_customer_sentiment")
    elif any(term in goal_lower for term in negative_terms):
        sentiment = "negative"
        priority_indicators.append("negative_customer_sentiment")
    elif any(term in goal_lower for term in positive_terms):
        sentiment = "positive"
    else:
        sentiment = "neutral"

    # Intent Classification
    human_phrases = [
        "human", "agent", "representative", "speak to a person", "speak with someone",
        "talk to a human", "speak with a human", "speak to a human", "customer support",
        "transfer me to a human", "talk to the bot", "talk to a person", "talk to someone",
        "operator", "supervisor", "real person", "live person", "connect me"
    ]

    # Check if the user is replying with an order ID to a previous prompt
    is_order_response = False
    if extracted_order and len(clean_goal.split()) <= 4 and not any(k in goal_lower for k in ["refund", "cancel", "policy"]):
        is_order_response = True

    if any(phrase in goal_lower for phrase in human_phrases):
        intent = "human_escalation"
        sub_intent = "live_agent_handoff"
        requested_action = "escalate_to_human"
        urgency = "high"
        confidence = 0.98
        priority_indicators.append("explicit_human_agent_request")

    elif "policy" in goal_lower or (any(phrase in goal_lower for phrase in ["what is", "how do i", "rules", "warranty", "shipping time"]) and not any(a in goal_lower for a in ["refund me", "refund it", "process refund"])):
        intent = "policy_inquiry"
        if "warranty" in goal_lower:
            sub_intent = "warranty_coverage_query"
        elif "shipping" in goal_lower:
            sub_intent = "shipping_transit_query"
        elif "cancel" in goal_lower:
            sub_intent = "cancellation_policy_query"
        else:
            sub_intent = "refund_policy_query"
        requested_action = "explain_policy"
        urgency = "low"
        confidence = 0.95

    elif any(phrase in goal_lower for phrase in ["refund", "money back", "credit"]):
        intent = "refund_request"
        if "delayed" in goal_lower or "late" in goal_lower:
            sub_intent = "severe_delay_refund"
            priority_indicators.append("delivery_delay_monetary_remedy")
        elif "damage" in goal_lower or "broken" in goal_lower:
            sub_intent = "damaged_item_refund"
            priority_indicators.append("damaged_goods_remedy")
        else:
            sub_intent = "standard_order_refund"

        requested_action = "issue_refund"
        urgency = "high" if "delayed" in goal_lower or "urgent" in goal_lower or sentiment == "frustrated" else "medium"
        confidence = 0.96
        priority_indicators.append("monetary_transaction_requested")

    elif any(phrase in goal_lower for phrase in ["cancel", "stop order"]):
        intent = "cancellation_request"
        sub_intent = "pre_fulfillment_cancellation"
        requested_action = "cancel_order"
        urgency = "high"
        confidence = 0.94
        priority_indicators.append("order_cancellation_requested")

    elif any(phrase in goal_lower for phrase in [
        "where is", "track", "status", "shipping", "delivery", "arrive", "hasn't arrived", "has not arrived", "late", "delayed", "package"
    ]) or is_order_response:
        intent = "order_status_inquiry"
        sub_intent = "tracking_lookup"
        requested_action = "track_shipment"
        urgency = "medium"
        confidence = 0.95
        if "delayed" in goal_lower or "late" in goal_lower or "hasn't arrived" in goal_lower:
            priority_indicators.append("delayed_shipment_inquiry")

    else:
        intent = "general_inquiry"
        sub_intent = "general_assistance"
        requested_action = "general_assist"
        urgency = "low"
        confidence = 0.85

        # If general inquiry and cloud is enabled, allow Gemini to classify subtle phrasing
        if len(clean_goal.split()) > 3:
            try:
                from .llm_client import llm_client
                if llm_client.is_cloud_enabled():
                    classified = llm_client.generate_json_sync(
                        system_prompt=(
                            "You are an intent triage specialist for NovaCart e-commerce support. "
                            "Classify the customer message into one of these intents: "
                            "['order_status_inquiry', 'refund_request', 'cancellation_request', 'policy_inquiry', 'human_escalation', 'general_inquiry']. "
                            "Also extract sentiment: ['positive', 'neutral', 'negative', 'frustrated'], "
                            "and urgency: ['low', 'medium', 'high', 'urgent']. "
                            "Output JSON with keys: intent, sentiment, urgency."
                        ),
                        user_prompt=clean_goal,
                        temperature=0.1
                    )
                    if classified and isinstance(classified, dict):
                        valid_intents = [
                            "order_status_inquiry", "refund_request", "cancellation_request",
                            "policy_inquiry", "human_escalation", "general_inquiry"
                        ]
                        if classified.get("intent") in valid_intents:
                            intent = classified["intent"]
                            if intent == "order_status_inquiry":
                                sub_intent = "tracking_lookup"
                                requested_action = "track_shipment"
                            elif intent == "refund_request":
                                sub_intent = "standard_order_refund"
                                requested_action = "issue_refund"
                            elif intent == "policy_inquiry":
                                sub_intent = "policy_guidance"
                                requested_action = "explain_policy"
                            elif intent == "human_escalation":
                                sub_intent = "live_agent_handoff"
                                requested_action = "escalate_to_human"
                        if classified.get("sentiment"):
                            sentiment = classified["sentiment"]
                        if classified.get("urgency"):
                            urgency = classified["urgency"]
            except Exception:
                pass

    if extracted_order:
        priority_indicators.append(f"order_entity_{extracted_order}")

    return IntakeExtractionResult(
        intent=intent,
        sub_intent=sub_intent,
        order_id=extracted_order,
        customer_id=extracted_cust,
        product=detected_product,
        requested_action=requested_action,
        urgency=urgency,
        sentiment=sentiment,
        priority_indicators=priority_indicators,
        relevant_entities=entities,
        confidence=confidence
    )
