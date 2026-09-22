from typing import Dict, Any, List
from ..tools import execute_tool

def run_resolution_agent(
    current_step: str,
    task_id: str,
    intent_data: Dict[str, Any],
    order_data: Dict[str, Any] = None,
    eligibility_data: Dict[str, Any] = None,
    policy_context: str = ""
) -> Dict[str, Any]:
    """Agent 4 — Resolution / Action Agent.

    Executes domain actions, invokes tools, analyzes output, and formulates structured subtask results.
    """
    step_lower = current_step.lower()
    entities = intent_data.get("entities", {})
    order_id = entities.get("order_id")
    customer_id = entities.get("customer_id", "CUST1002")

    tool_used = None
    tool_output = None
    observation = ""
    success = True
    confidence = 0.92

    if "order" in step_lower and ("status" in step_lower or "retrieve" in step_lower or "validate" in step_lower):
        tool_used = "get_order_status"
        tool_res = execute_tool("get_order_status", {"order_id": order_id}, task_id=task_id)
        tool_output = tool_res["result"]
        if tool_output.get("success"):
            observation = (
                f"Order {order_id} retrieved successfully. Status: {tool_output.get('status')}. "
                f"Carrier: {tool_output.get('carrier')} (Tracking: {tool_output.get('tracking_number')}). "
                f"Delay reason: {tool_output.get('delay_reason')}."
            )
        else:
            success = False
            observation = f"Failed to retrieve order {order_id}: {tool_output.get('error')}"

    elif ("execute" in step_lower or "process" in step_lower) and "refund" in step_lower:
        # Strict tool safety: ensure order is eligible before executing refund
        if eligibility_data and eligibility_data.get("eligible"):
            amount = eligibility_data.get("refund_amount", 0.0)
            reason = eligibility_data.get("reason", "Customer delay compensation")
            tool_used = "process_refund"
            tool_res = execute_tool("process_refund", {
                "order_id": order_id,
                "refund_amount": amount,
                "reason": reason,
                "customer_id": customer_id
            }, task_id=task_id)
            tool_output = tool_res["result"]
            if tool_output.get("success"):
                observation = (
                    f"Financial refund executed successfully! Refund ID: {tool_output.get('refund_id')}. "
                    f"Amount: ${amount:.2f}. Status: {tool_output.get('status')}. "
                    f"Order status updated to Refunded."
                )
            else:
                success = False
                observation = f"Refund transaction failed: {tool_output.get('error')}"
        else:
            success = False
            observation = f"Cannot process refund for {order_id}: Order is not eligible according to company policy."

    elif "eligib" in step_lower or "evaluate" in step_lower:
        tool_used = "check_refund_eligibility"
        tool_res = execute_tool("check_refund_eligibility", {"order_id": order_id, "customer_id": customer_id}, task_id=task_id)
        tool_output = tool_res["result"]
        is_eligible = tool_output.get("eligible", False)
        observation = (
            f"Eligibility evaluated for {order_id}: {'ELIGIBLE' if is_eligible else 'INELIGIBLE'}. "
            f"Refund Amount: ${tool_output.get('refund_amount', 0.0):.2f}. "
            f"Policy basis: {tool_output.get('reason')} ({tool_output.get('policy_applied')})."
        )

    else:
        observation = f"Step '{current_step}' analyzed and synthesized with available context."

    return {
        "agent": "Resolution Agent",
        "step": current_step,
        "tool_used": tool_used,
        "tool_output": tool_output,
        "observation": observation,
        "success": success,
        "confidence": confidence
    }
