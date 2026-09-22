import datetime
from typing import Dict, Any, List

def format_final_customer_response(
    intent_data: Dict[str, Any],
    observations: List[Dict[str, Any]],
    tool_calls: List[Dict[str, Any]],
    rag_data: Dict[str, Any] = None,
    escalation_dossier: Dict[str, Any] = None
) -> str:
    """Synthesizes a helpful, accurate, policy-grounded final response for the customer."""
    intent = intent_data.get("intent")
    entities = intent_data.get("entities", {})
    order_id = entities.get("order_id")

    if escalation_dossier:
        ticket_id = escalation_dossier.get("ticket_id")
        return (
            f"I have connected your request with our NovaCart Human Support Desk. "
            f"Your support ticket has been registered under **Ticket #{ticket_id}** with High Priority. "
            f"A human specialist is reviewing your order details and will take over shortly. "
            f"Thank you for your patience!"
        )

    if intent == "refund_request":
        # Look for refund tool result
        refund_call = next((tc for tc in tool_calls if tc.get("tool_name") == "process_refund" and tc.get("status") == "success"), None)
        eligibility_call = next((tc for tc in tool_calls if tc.get("tool_name") == "check_refund_eligibility"), None)

        if refund_call:
            res = refund_call.get("result", {})
            refund_id = res.get("refund_id", "REF-PROCESSED")
            amount = res.get("refund_amount", 0.0)
            return (
                f"Good news! I have verified your order **{order_id}** and confirmed that it meets NovaCart's "
                f"Severe Delivery Delay threshold (> 3 days past scheduled delivery date).\n\n"
                f"✓ **Refund Initiated**: **${amount:.2f} USD** has been credited to your original payment method.\n"
                f"✓ **Transaction Receipt**: `{refund_id}`\n"
                f"✓ **Timeline**: Funds typically reflect on your bank statement within 3–5 business days.\n\n"
                f"Should the package still arrive, please accept it as our courtesy gift for the inconvenience caused."
            )
        elif eligibility_call:
            el_res = eligibility_call.get("result", {})
            reason = el_res.get("reason", "Ineligible per policy terms.")
            return (
                f"I reviewed your order **{order_id}**, but according to NovaCart's policy, it is currently "
                f"not eligible for an immediate full refund:\n\n"
                f"• **Reason**: {reason}\n"
                f"• **Policy Applied**: {el_res.get('policy_applied', 'Standard Order Policy')}\n\n"
                f"If you believe this is in error or require additional assistance, I can escalate your request to a human specialist."
            )
        else:
            return (
                f"I have analyzed your refund inquiry for order **{order_id}**. "
                f"Please let me know if you would like me to review eligibility or if you have further details to provide."
            )

    if intent == "order_status_inquiry":
        order_call = next((tc for tc in tool_calls if tc.get("tool_name") == "get_order_status"), None)
        if order_call and order_call.get("status") == "success":
            res = order_call.get("result", {})
            return (
                f"Here is the live update for order **{order_id}**:\n\n"
                f"• **Status**: {res.get('status')}\n"
                f"• **Carrier**: {res.get('carrier')} (Tracking: `{res.get('tracking_number')}`)\n"
                f"• **Details**: {res.get('delay_reason') or 'In transit on regular schedule'}\n\n"
                f"If you need to request a refund or modify shipping arrangements, feel free to ask!"
            )

    if intent == "policy_inquiry" and rag_data:
        citations = rag_data.get("citations", [])
        citation_str = ", ".join([f"{c['category']} ({c['section']})" for c in citations[:2]])
        return (
            f"Based on **NovaCart Corporate Policies** ({citation_str}):\n\n"
            f"{rag_data.get('context')}\n\n"
            f"Let me know if you have any questions regarding your specific order or policy terms!"
        )

    # General fallback response based on observations
    obs_text = " ".join([o.get("observation", "") for o in observations[-2:]])
    return (
        f"Thank you for contacting NovaCart Support. {obs_text or 'Your request has been processed successfully.'} "
        f"Please let me know how else I can assist you today."
    )
