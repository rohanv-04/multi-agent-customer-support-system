from typing import Dict, Any, List

def run_critic_agent(
    task_goal: str,
    intent_data: Dict[str, Any],
    plan: List[str],
    completed_steps: List[str],
    observations: List[Dict[str, Any]],
    tool_calls: List[Dict[str, Any]],
    rag_data: Dict[str, Any] = None,
    replan_count: int = 0
) -> Dict[str, Any]:
    """Agent 5 — Critic / Validation Agent.

    Strictly audits all agent actions, tool results, and policy grounding before final response delivery.
    """
    issues: List[str] = []
    confidence = 0.95
    recommended_action = "complete"

    # 1. Check if intent is human escalation
    if intent_data.get("intent") == "human_escalation":
        return {
            "valid": True,
            "confidence": 0.98,
            "issues": [],
            "recommended_action": "escalate",
            "audit_summary": "Customer explicitly requested human specialist handoff. Escalation authorized."
        }

    # 2. Check tool execution consistency
    failed_tools = [tc for tc in tool_calls if tc.get("status") == "failure"]
    if failed_tools:
        for ft in failed_tools:
            issues.append(f"Tool failure detected: {ft.get('tool_name')} failed with error '{ft.get('error_message')}'")
        if replan_count < 3:
            recommended_action = "replan"
            confidence = 0.65
        else:
            recommended_action = "escalate"
            confidence = 0.50

    # 3. Check for missing entities (e.g. order_id in refund or tracking intent)
    intent = intent_data.get("intent")
    order_id = intent_data.get("entities", {}).get("order_id")
    if intent in ["refund_request", "order_status_inquiry"] and not order_id:
        issues.append("Missing required Order ID for transaction verification.")
        confidence = 0.70
        recommended_action = "complete"  # Prompts user for order_id

    # 4. Check policy compliance for refunds
    if intent == "refund_request" and order_id:
        # Check if refund was processed without eligibility check
        has_eligibility = any("check_refund_eligibility" in str(tc.get("tool_name")) for tc in tool_calls)
        has_refund = any("process_refund" in str(tc.get("tool_name")) for tc in tool_calls)

        if has_refund and not has_eligibility:
            issues.append("Policy violation: Refund executed without prior eligibility validation.")
            recommended_action = "escalate"
            confidence = 0.40

    # 5. Check RAG grounding
    if intent == "policy_inquiry" and rag_data:
        if not rag_data.get("found"):
            issues.append("Low RAG grounding: No matching policy documents found for customer inquiry.")
            confidence = 0.60
            if replan_count < 2:
                recommended_action = "replan"
            else:
                recommended_action = "escalate"

    # Determine validity based on issues and confidence
    is_valid = len(issues) == 0 or (recommended_action == "complete" and confidence >= 0.70)

    audit_summary = (
        f"Validation passed with {confidence * 100:.0f}% confidence. All actions policy compliant."
        if is_valid
        else f"Validation flagged {len(issues)} issue(s). Action: {recommended_action.upper()}."
    )

    return {
        "valid": is_valid,
        "confidence": round(confidence, 2),
        "issues": issues,
        "recommended_action": recommended_action,
        "audit_summary": audit_summary
    }
