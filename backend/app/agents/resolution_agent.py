from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from ..tools import execute_tool
from ..schemas.action_gateway import ActionRequest, ActionResult, ActionStatus
from ..services.action_gateway import ActionGateway
from ..database.database import SessionLocal


def run_resolution_agent(
    current_step: str,
    task_id: str,
    intent_data: Dict[str, Any],
    order_data: Dict[str, Any] = None,
    eligibility_data: Dict[str, Any] = None,
    policy_context: str = "",
    case_id: Optional[str] = None,
    risk_evaluation: Optional[Dict[str, Any]] = None,
    db: Optional[Session] = None
) -> Dict[str, Any]:
    """Agent: Resolution / Action Agent.

    Executes domain actions, invokes tools, routes sensitive business operations
    through the secure Action Gateway, and verifies database state.
    """
    step_lower = current_step.lower()
    entities = intent_data.get("entities", {})
    order_id = entities.get("order_id")
    customer_id = entities.get("customer_id", "CUST1002")

    tool_used = None
    tool_output = None
    action_result = None
    observation = ""
    success = True
    confidence = 0.95

    close_db_local = False
    if db is None:
        db = SessionLocal()
        close_db_local = True

    try:
        # Sensitive Operation 1: Refund Execution through Action Gateway
        if ("execute" in step_lower or "process" in step_lower) and "refund" in step_lower:
            if eligibility_data and eligibility_data.get("eligible"):
                tool_used = "process_refund"
                amount = float(eligibility_data.get("refund_amount", 0.0))
                reason = eligibility_data.get("reason", "Customer delay compensation")

                action_req = ActionRequest(
                    case_id=case_id,
                    action_type="refund",
                    requested_by="Resolution Agent",
                    parameters={
                        "order_id": order_id,
                        "refund_amount": amount,
                        "reason": reason,
                        "customer_id": customer_id
                    },
                    justification=f"Automated resolution for eligible order {order_id}",
                    risk_result=risk_evaluation,
                    task_id=task_id,
                    actor_role="agent"
                )

                res = ActionGateway.execute_action(db=db, request=action_req)
                action_result = res.model_dump(mode="json")
                tool_output = res.result

                if res.status == ActionStatus.VERIFIED.value:
                    observation = (
                        f"Financial refund executed and VERIFIED! Refund ID: {res.external_reference}. "
                        f"Amount: ${amount:.2f}. Status: {res.status}. Database mutation confirmed."
                    )
                    success = True
                elif res.status == ActionStatus.APPROVAL_PENDING.value:
                    observation = (
                        f"Refund of ${amount:.2f} requires human authorization ({res.result.get('required_approval')}). "
                        f"Request placed in APPROVAL_PENDING."
                    )
                    success = True
                else:
                    success = False
                    observation = f"Refund action gateway blocked/failed: {res.error or 'Execution not verified'}"
            else:
                tool_used = None
                success = True
                observation = f"Order {order_id} is evaluated as ineligible for refund under corporate policy. Transaction execution safely bypassed."

        # Read-only Diagnostic Tools
        elif "order" in step_lower and ("status" in step_lower or "retrieve" in step_lower or "validate" in step_lower):
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

        # Sensitive Operation 2: Order Cancellation through Action Gateway
        elif "cancel" in step_lower:
            tool_used = "cancel_order"
            action_req = ActionRequest(
                case_id=case_id,
                action_type="cancellation",
                requested_by="Resolution Agent",
                parameters={"order_id": order_id, "customer_id": customer_id},
                justification=f"Customer cancellation request for {order_id}",
                risk_result=risk_evaluation,
                task_id=task_id,
                actor_role="agent"
            )
            res = ActionGateway.execute_action(db=db, request=action_req)
            action_result = res.model_dump(mode="json")
            tool_output = res.result
            if res.status == ActionStatus.VERIFIED.value:
                observation = f"Order {order_id} cancellation executed and VERIFIED in database."
                success = True
            else:
                success = False
                observation = f"Order cancellation failed/blocked: {res.error}"

        # Sensitive Operation 3: Replacement / Reshipment
        elif "replacement" in step_lower or "replace" in step_lower:
            tool_used = "create_replacement"
            action_req = ActionRequest(
                case_id=case_id,
                action_type="replacement",
                requested_by="Resolution Agent",
                parameters={"order_id": order_id, "customer_id": customer_id},
                justification=f"Item replacement for order {order_id}",
                risk_result=risk_evaluation,
                task_id=task_id,
                actor_role="agent"
            )
            res = ActionGateway.execute_action(db=db, request=action_req)
            action_result = res.model_dump(mode="json")
            tool_output = res.result
            if res.status == ActionStatus.VERIFIED.value:
                observation = f"Replacement order created and VERIFIED (Ref: {res.external_reference})."
                success = True
            else:
                success = False
                observation = f"Replacement creation failed: {res.error}"

        else:
            observation = "Analyzed inquiry context and gathered information for resolution."

    finally:
        if close_db_local:
            db.close()

    return {
        "agent": "Resolution Agent",
        "step": current_step,
        "tool_used": tool_used,
        "tool_output": tool_output,
        "action_result": action_result,
        "observation": observation,
        "success": success,
        "confidence": confidence
    }
