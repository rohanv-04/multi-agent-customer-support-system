import datetime
from typing import Dict, Any, List

def format_final_customer_response(
    intent_data: Dict[str, Any],
    observations: List[Dict[str, Any]],
    tool_calls: List[Dict[str, Any]],
    rag_data: Dict[str, Any] = None,
    escalation_dossier: Dict[str, Any] = None
) -> str:
    """Synthesizes a helpful, accurate, natural, policy-grounded final response for the customer."""
    intent = intent_data.get("intent")
    entities = intent_data.get("entities", {})
    order_id = entities.get("order_id")

    # 1. Human Escalation (only when explicitly requested or flagged by risk/policy)
    if escalation_dossier:
        ticket_id = escalation_dossier.get("ticket_id")
        reason = escalation_dossier.get("reason", "Human support transfer requested")
        if "explicit" in reason.lower() or "customer requested" in reason.lower():
            return (
                f"I've transferred your case to our human support desk (**Ticket #{ticket_id}**). "
                f"You can click **👤 Talk to a Human** in the corner to see your assigned specialist and call directly."
            )
        else:
            return (
                f"I've reviewed your request and forwarded your case for human review (**Ticket #{ticket_id}**) "
                f"to ensure your issue is resolved accurately."
            )

    if intent == "human_escalation":
        return (
            "I'd be happy to connect you with our human support team. "
            "You can use the **👤 Talk to a Human** action in the corner anytime to connect with an assigned specialist."
        )

    # 2. Refund Request
    if intent == "refund_request":
        if not order_id:
            return "I can certainly check whether your order qualifies for a refund. Could you please share your order number?"

        refund_call = next((tc for tc in tool_calls if tc.get("tool_name") == "process_refund" and tc.get("status") == "success"), None)
        eligibility_call = next((tc for tc in tool_calls if tc.get("tool_name") == "check_refund_eligibility"), None)

        if refund_call:
            res = refund_call.get("result", {})
            refund_id = res.get("refund_id", "REF-PROCESSED")
            amount = res.get("refund_amount", 0.0)
            return (
                f"I've verified your order **{order_id}** and confirmed that it qualifies for a refund under NovaCart's delivery delay policy.\n\n"
                f"I have initiated a full refund of **${amount:.2f} USD** to your original payment method (Reference: `{refund_id}`). "
                f"You should see the funds reflected on your bank statement within 3–5 business days. "
                f"If the package still arrives, please keep it as our courtesy gift for the delay."
            )
        elif eligibility_call:
            el_res = eligibility_call.get("result", {})
            reason = el_res.get("reason", "Ineligible under current policy conditions.")
            policy_name = el_res.get("policy_applied", "NovaCart Refund Policy")
            if el_res.get("eligible"):
                amount = el_res.get("refund_amount", 0.0)
                return (
                    f"Good news! I checked your order **{order_id}** and it is eligible for a refund of **${amount:.2f} USD** per {policy_name} ({reason}). "
                    f"Would you like me to process this refund for you right now?"
                )
            else:
                return (
                    f"I checked the details for order **{order_id}**, but according to {policy_name}, "
                    f"it doesn't currently meet the criteria for an immediate refund: {reason}. "
                    f"Let me know if you would like me to check tracking updates or explore alternative solutions."
                )
        else:
            return (
                f"I've analyzed the refund request for order **{order_id}**. "
                f"Let me know if you'd like me to look into specific delivery or product details for you."
            )

    # 3. Order Status Inquiry
    if intent == "order_status_inquiry":
        if not order_id:
            return "I can help you check that. Could you share your order number?"

        order_call = next((tc for tc in tool_calls if tc.get("tool_name") == "get_order_status"), None)
        if order_call and order_call.get("status") == "success":
            res = order_call.get("result", {})
            carrier = res.get("carrier") or "NovaExpress"
            tracking = res.get("tracking_number") or "N/A"
            status = res.get("status") or "In Transit"
            delay = res.get("delay_reason")

            if delay or "delay" in status.lower():
                return (
                    f"Thanks for waiting. I checked order **{order_id}**. "
                    f"Your package was shipped via {carrier} (Tracking: `{tracking}`), but is currently delayed in transit. "
                    f"Reason: {delay or 'Carrier transit delay'}. "
                    f"Let me know if you'd like me to check whether this qualifies for a refund or replacement."
                )
            else:
                return (
                    f"I checked your order **{order_id}**. "
                    f"It is currently **{status}** with {carrier} (Tracking: `{tracking}`). "
                    f"Everything is on schedule. Let me know if you have any other questions!"
                )
        else:
            return (
                f"I looked up order **{order_id}**. The shipment is being processed by our logistics partner. "
                f"Let me know if you need additional assistance."
            )

    # 4. Cancellation Request
    if intent == "cancellation_request":
        if not order_id:
            return "I can help cancel your order if it hasn't shipped yet. Could you please provide the order number?"

        cancel_call = next((tc for tc in tool_calls if tc.get("tool_name") == "cancel_order"), None)
        if cancel_call and cancel_call.get("status") == "success":
            return (
                f"I've cancelled order **{order_id}** as requested. "
                f"A cancellation confirmation has been recorded and any pending authorizations have been released."
            )

    # 5. Policy Inquiry
    if intent == "policy_inquiry" and rag_data:
        citations = rag_data.get("citations", [])
        citation_str = ", ".join([f"{c['category']}" for c in citations[:2]]) if citations else "NovaCart Guidelines"
        context_summary = rag_data.get("context", "").strip()
        return (
            f"Here is what our policy states regarding your question:\n\n"
            f"{context_summary}\n\n"
            f"Feel free to let me know if you'd like me to look up a specific order or check eligibility!"
        )

    # 6. General Conversational / Fallback Response
    if observations:
        obs_text = observations[-1].get("observation", "")
        if obs_text:
            return f"I've investigated your inquiry. {obs_text} Please let me know how else I can assist you."

    return "I'm here to help with your orders, shipments, returns, and policy questions. How can I assist you today?"
