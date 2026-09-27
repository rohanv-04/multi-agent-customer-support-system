import datetime
import json
from typing import Dict, Any, List, Optional
from .llm_client import llm_client

try:
    from ..services.response_sanitizer import ResponseSanitizer
except (ImportError, ValueError):
    from backend.app.services.response_sanitizer import ResponseSanitizer

def _format_deterministic_fallback(
    intent_data: Dict[str, Any],
    observations: List[Dict[str, Any]],
    tool_calls: List[Dict[str, Any]],
    rag_data: Optional[Dict[str, Any]] = None,
    escalation_dossier: Optional[Dict[str, Any]] = None
) -> str:
    """Deterministic template fallback engine for 100% offline or network fault tolerance."""
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


def _format_gemini_response(
    intent_data: Dict[str, Any],
    observations: List[Dict[str, Any]],
    tool_calls: List[Dict[str, Any]],
    rag_data: Optional[Dict[str, Any]] = None,
    escalation_dossier: Optional[Dict[str, Any]] = None,
    messages: Optional[List[Dict[str, str]]] = None,
    customer_360: Optional[Dict[str, Any]] = None,
    user_goal: Optional[str] = None
) -> Optional[str]:
    """Uses Gemini to synthesize an empathetic, natural, context-grounded response."""
    intent = intent_data.get("intent", "general_inquiry")
    entities = intent_data.get("entities", {})
    order_id = entities.get("order_id")

    # Format multi-agent investigation payload
    investigation_summary = {
        "intent": intent,
        "sub_intent": intent_data.get("sub_intent"),
        "customer": {
            "id": customer_360.get("customer_id") if customer_360 else entities.get("customer_id", "CUST1002"),
            "name": customer_360.get("name") if customer_360 else "Valued Customer",
            "tier": customer_360.get("tier") if customer_360 else "Standard",
        },
        "order_id": order_id,
        "tool_executions": [
            {
                "tool": tc.get("tool_name"),
                "status": tc.get("status"),
                "result": tc.get("result")
            }
            for tc in tool_calls
        ],
        "observations": [o.get("observation") for o in observations if o.get("observation")],
        "policy_context": rag_data.get("context") if rag_data else None,
        "escalation": escalation_dossier
    }

    # Construct the system instruction
    system_instruction = (
        "You are NovaCart's AI Customer Support Specialist (SupportOS). "
        "Your mission is to provide warm, empathetic, realistic, highly professional, and direct assistance. "
        "\n\nCRITICAL CONVERSATIONAL & GROUNDING RULES:\n"
        "1. REALISTIC & NATURAL TONE: Speak like an experienced, caring senior customer care specialist. "
        "Acknowledge customer emotions (frustration, anxiety, appreciation) sincerely and naturally. "
        "NEVER say robotic phrases like 'Please choose an option' or 'Select your issue'.\n"
        "2. STRICT GROUNDING IN FACTS: Every factual statement must come ONLY from the provided investigation context, tools, and policies.\n"
        "   - Missing Order ID: If the customer asks about an order or refund but no order ID is present, kindly and naturally ask them to share their order number.\n"
        "   - Order Status: If order data was retrieved, state the order ID, status, carrier name, tracking number, and delay reason if applicable.\n"
        "   - Refund Executed: If a refund was processed (tool: process_refund), state the exact order ID, refund amount, and refund reference ID (e.g. REF-XXXXX). Mention that funds typically reflect in 3–5 business days.\n"
        "   - Ineligible Refund: If check_refund_eligibility indicates ineligible, explain the policy reason politely and offer alternatives.\n"
        "   - Cancellation: If cancellation was executed, confirm the order ID cancellation.\n"
        "   - Human Escalation: If escalation occurred, provide the support ticket ID (e.g. ESC-XXXX) and reassure the customer a human specialist has been assigned.\n"
        "   - Policy Inquiry: Answer accurately using the policy context provided.\n"
        "3. FORMATTING: Use Markdown styling (bold order numbers, tracking IDs, dollar amounts). Keep paragraphs clean, scannable, and helpful."
    )

    current_goal = user_goal or (messages[-1]["content"] if messages else "General inquiry")
    prompt = (
        f"Customer Message: \"{current_goal}\"\n\n"
        f"Investigation Context & Real Multi-Agent Findings:\n"
        f"{json.dumps(investigation_summary, indent=2)}\n\n"
        f"Generate the final, natural, empathetic customer response adhering strictly to the facts above."
    )

    history = messages[:-1] if messages and len(messages) > 1 else None

    # Request response from Gemini via LLMClient
    response_text = llm_client.generate_text(
        prompt=prompt,
        system_prompt=system_instruction,
        messages=history,
        temperature=0.3
    )

    if response_text and len(response_text.strip()) > 10:
        cleaned_resp = response_text.strip()
        # Verify that if a refund was processed, the response actually mentions refund
        has_refund = any(tc.get("tool_name") == "process_refund" and tc.get("status") == "success" for tc in tool_calls)
        if has_refund and "refund" not in cleaned_resp.lower():
            print("[Supervisor Warning] LLM response omitted critical refund information. Falling back to deterministic template.")
            return None
        return cleaned_resp

    return None


def format_final_customer_response(
    intent_data: Dict[str, Any],
    observations: List[Dict[str, Any]],
    tool_calls: List[Dict[str, Any]],
    rag_data: Optional[Dict[str, Any]] = None,
    escalation_dossier: Optional[Dict[str, Any]] = None,
    messages: Optional[List[Dict[str, str]]] = None,
    customer_360: Optional[Dict[str, Any]] = None,
    user_goal: Optional[str] = None
) -> str:
    """Synthesizes an empathetic, realistic, policy-grounded final response for the customer.
    Uses Gemini when cloud is enabled, with seamless fallback to deterministic template logic.
    Always filters outbound content through ResponseSanitizer.
    """
    context = {"user_goal": user_goal, "customer_id": customer_360.get("customer_id") if customer_360 else None}

    if llm_client.is_cloud_enabled():
        try:
            gemini_response = _format_gemini_response(
                intent_data=intent_data,
                observations=observations,
                tool_calls=tool_calls,
                rag_data=rag_data,
                escalation_dossier=escalation_dossier,
                messages=messages,
                customer_360=customer_360,
                user_goal=user_goal
            )
            if gemini_response and len(gemini_response.strip()) > 10:
                return ResponseSanitizer.sanitize(gemini_response, context=context)
        except Exception as e:
            print(f"[Supervisor Warning] Gemini response synthesis error: {e}. Falling back to deterministic engine.")

    # Fallback to deterministic template engine
    fallback = _format_deterministic_fallback(
        intent_data=intent_data,
        observations=observations,
        tool_calls=tool_calls,
        rag_data=rag_data,
        escalation_dossier=escalation_dossier
    )
    return ResponseSanitizer.sanitize(fallback, context=context)
