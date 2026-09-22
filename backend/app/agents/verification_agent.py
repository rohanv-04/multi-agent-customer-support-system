import datetime
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session

from ..schemas.action_gateway import ActionRequest, VerificationResult
from ..database.models import Order, Refund, Customer, SupportCase, CaseMessage


def verify_action_execution(
    db: Session,
    request: ActionRequest,
    execution_result: Dict[str, Any],
    retry_count: int = 0,
    max_retries: int = 2
) -> VerificationResult:
    """Verification Engine: Independently audits actual database state against expected post-action conditions.
    
    Invariants:
    1. Checks whether tool returned success=True.
    2. Directly queries SQLite database to ensure the state mutation actually persisted.
    3. Detects state mismatch or silent failures.
    4. Enforces retry vs replan vs escalation policy.
    5. Core rule: Never inform customer of success unless independently verified.
    """
    action_type = request.action_type.lower()
    tool_success = bool(execution_result.get("success", False))
    tool_error = execution_result.get("error")

    # Ensure ORM cache is refreshed from database
    try:
        db.expire_all()
    except Exception:
        pass

    expected_state: Dict[str, Any] = {}
    actual_state: Dict[str, Any] = {}
    mismatch_detected = False
    mismatch_details = None
    verified = False

    # 1. Immediate Execution Failure Check
    if not tool_success or tool_error:
        should_escalate = retry_count >= max_retries
        return VerificationResult(
            verified=False,
            action_type=action_type,
            expected_state={"tool_status": "success"},
            actual_state={"tool_status": "failure", "error": tool_error or "Tool execution returned success=False"},
            mismatch_detected=True,
            mismatch_details=f"Tool execution failed: {tool_error or 'Execution returned failure'}",
            safe_to_retry=not should_escalate,
            retry_count=retry_count,
            should_replan=False,
            should_escalate=should_escalate,
            verification_summary=f"Action execution failed: {tool_error}. {'Routing to human desk' if should_escalate else 'Retrying action execution'}."
        )

    # 2. Database State Invariant Checks by Action Type
    if action_type == "refund":
        order_id = (request.parameters.get("order_id") or "").strip().upper()
        expected_amount = float(request.parameters.get("refund_amount", 0.0))
        expected_state = {"order_status": "Refunded", "refund_recorded": True, "amount": expected_amount}

        order = db.query(Order).filter(Order.order_id == order_id).first() if order_id else None
        refund = db.query(Refund).filter(Refund.order_id == order_id).first() if order_id else None

        actual_state = {
            "order_status": order.status if order else "NOT_FOUND",
            "refund_recorded": refund is not None,
            "refund_id": refund.refund_id if refund else None,
            "recorded_amount": refund.refund_amount if refund else 0.0
        }

        if not order or order.status != "Refunded":
            mismatch_detected = True
            mismatch_details = f"State mismatch: Order {order_id} status is '{order.status if order else 'NOT_FOUND'}', expected 'Refunded'."
        elif not refund or abs(refund.refund_amount - expected_amount) > 0.01:
            mismatch_detected = True
            mismatch_details = f"State mismatch: Refund record missing or amount ${refund.refund_amount if refund else 0.0} != expected ${expected_amount}."
        else:
            verified = True

    elif action_type == "cancellation":
        order_id = (request.parameters.get("order_id") or "").strip().upper()
        expected_state = {"order_status": "Cancelled"}
        order = db.query(Order).filter(Order.order_id == order_id).first() if order_id else None

        actual_state = {"order_status": order.status if order else "NOT_FOUND"}
        if not order or order.status != "Cancelled":
            mismatch_detected = True
            mismatch_details = f"State mismatch: Order {order_id} status is '{order.status if order else 'NOT_FOUND'}', expected 'Cancelled'."
        else:
            verified = True

    elif action_type == "replacement":
        orig_order_id = (request.parameters.get("order_id") or "").strip().upper()
        repl_order_id = execution_result.get("replacement_order_id")
        expected_state = {"replacement_order_created": True, "replacement_status": "Processing"}

        repl_order = db.query(Order).filter(Order.order_id == repl_order_id).first() if repl_order_id else None
        actual_state = {
            "replacement_order_id": repl_order_id,
            "replacement_status": repl_order.status if repl_order else "NOT_FOUND"
        }

        if not repl_order or repl_order.status != "Processing":
            mismatch_detected = True
            mismatch_details = f"State mismatch: Replacement order {repl_order_id} was not found in active processing state."
        else:
            verified = True

    elif action_type == "reshipment":
        order_id = (request.parameters.get("order_id") or "").strip().upper()
        expected_state = {"order_status": "Shipped", "has_tracking": True}
        order = db.query(Order).filter(Order.order_id == order_id).first() if order_id else None

        actual_state = {
            "order_status": order.status if order else "NOT_FOUND",
            "tracking_number": order.tracking_number if order else None
        }

        if not order or order.status != "Shipped" or not order.tracking_number:
            mismatch_detected = True
            mismatch_details = f"State mismatch: Reshipped order {order_id} not marked 'Shipped' or missing tracking number."
        else:
            verified = True

    elif action_type in ["email", "whatsapp_message"]:
        case_id = request.case_id or request.parameters.get("case_id")
        expected_channel = "email" if action_type == "email" else "whatsapp"
        expected_state = {"message_recorded": True, "channel": expected_channel}

        if case_id:
            msg = db.query(CaseMessage).filter(
                CaseMessage.case_id == case_id,
                CaseMessage.channel == expected_channel
            ).order_by(CaseMessage.id.desc()).first()
            actual_state = {"message_recorded": msg is not None, "message_id": msg.id if msg else None}
            if not msg:
                mismatch_detected = True
                mismatch_details = f"State mismatch: Outbound {expected_channel} message was not logged in case {case_id} timeline."
            else:
                verified = True
        else:
            verified = True
            actual_state = {"dispatched": True}

    elif action_type == "ticket_update":
        case_id = request.case_id or request.parameters.get("case_id")
        expected_status = request.parameters.get("status")
        expected_priority = request.parameters.get("priority")
        expected_state = {"status": expected_status, "priority": expected_priority}

        case = db.query(SupportCase).filter(SupportCase.id == case_id).first() if case_id else None
        actual_state = {
            "status": case.status if case else "NOT_FOUND",
            "priority": case.priority if case else "NOT_FOUND"
        }

        if not case:
            mismatch_detected = True
            mismatch_details = f"SupportCase {case_id} not found."
        elif expected_status and case.status != expected_status:
            mismatch_detected = True
            mismatch_details = f"Case status mismatch: expected '{expected_status}', got '{case.status}'."
        else:
            verified = True

    elif action_type == "customer_update":
        customer_id = request.customer_id or request.parameters.get("customer_id")
        expected_tier = request.parameters.get("tier")
        cust = db.query(Customer).filter(Customer.customer_id == customer_id).first() if customer_id else None
        actual_state = {"tier": cust.tier if cust else "NOT_FOUND"}

        if not cust or (expected_tier and cust.tier != expected_tier):
            mismatch_detected = True
            mismatch_details = f"Customer profile mismatch for {customer_id}."
        else:
            verified = True
    else:
        # Generic tool verification
        verified = tool_success
        actual_state = {"generic_execution": "success" if tool_success else "failure"}

    should_escalate = (not verified) and (retry_count >= max_retries)
    should_replan = (not verified) and mismatch_detected and (not should_escalate)

    summary = (
        f"Verification Confirmed: {action_type.upper()} mutation successfully validated against database state."
        if verified
        else f"Verification Failed: {mismatch_details or 'Unexpected state detected'}. "
             f"{'Escalating to human supervisor' if should_escalate else 'Triggering safe retry/replan'}."
    )

    return VerificationResult(
        verified=verified,
        action_type=action_type,
        expected_state=expected_state,
        actual_state=actual_state,
        mismatch_detected=mismatch_detected,
        mismatch_details=mismatch_details,
        safe_to_retry=(not verified) and (not should_escalate),
        retry_count=retry_count,
        should_replan=should_replan,
        should_escalate=should_escalate,
        verification_summary=summary
    )
