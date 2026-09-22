import time
import json
from typing import Dict, Any
from .order_tool import get_order_status
from .customer_tool import get_customer_info
from .eligibility_tool import check_refund_eligibility
from .refund_tool import process_refund
from .order_cancellation_tool import cancel_order
from .replacement_tool import create_replacement
from .reshipment_tool import reship_order
from .communication_tool import send_customer_email, send_whatsapp_message
from .ticket_tool import update_support_ticket, update_customer_profile
from ..database.database import SessionLocal
from ..database.models import ToolCall

AVAILABLE_TOOLS = {
    "get_order_status": {
        "name": "get_order_status",
        "description": "Retrieve status, tracking, carrier, items, and delay reason for a given order_id.",
        "parameters": {"order_id": "string"}
    },
    "get_customer_info": {
        "name": "get_customer_info",
        "description": "Fetch customer profile, VIP tier, account status, and order history.",
        "parameters": {"customer_id": "string"}
    },
    "check_refund_eligibility": {
        "name": "check_refund_eligibility",
        "description": "Evaluate whether an order is eligible for refund based on corporate policies and delivery conditions.",
        "parameters": {"order_id": "string", "customer_id": "string (optional)"}
    },
    "process_refund": {
        "name": "process_refund",
        "description": "Execute a financial refund transaction on a verified eligible order. Requires order_id, refund_amount, and reason.",
        "parameters": {"order_id": "string", "refund_amount": "number", "reason": "string", "customer_id": "string (optional)"}
    },
    "cancel_order": {
        "name": "cancel_order",
        "description": "Execute pre-fulfillment order cancellation.",
        "parameters": {"order_id": "string", "reason": "string (optional)", "customer_id": "string (optional)"}
    },
    "create_replacement": {
        "name": "create_replacement",
        "description": "Generate a zero-cost replacement order for damaged or defective items.",
        "parameters": {"order_id": "string", "reason": "string (optional)", "customer_id": "string (optional)"}
    },
    "reship_order": {
        "name": "reship_order",
        "description": "Re-dispatch an existing order lost or returned in transit.",
        "parameters": {"order_id": "string", "carrier": "string (optional)", "reason": "string (optional)"}
    },
    "send_customer_email": {
        "name": "send_customer_email",
        "description": "Send transactional email to customer.",
        "parameters": {"customer_id": "string", "subject": "string", "body": "string", "case_id": "string (optional)"}
    },
    "send_whatsapp_message": {
        "name": "send_whatsapp_message",
        "description": "Send WhatsApp message to customer phone.",
        "parameters": {"customer_id": "string", "message": "string", "phone": "string (optional)", "case_id": "string (optional)"}
    },
    "update_support_ticket": {
        "name": "update_support_ticket",
        "description": "Update metadata, status, or priority on SupportCase.",
        "parameters": {"case_id": "string", "priority": "string (optional)", "status": "string (optional)", "subject": "string (optional)", "description": "string (optional)"}
    },
    "update_customer_profile": {
        "name": "update_customer_profile",
        "description": "Update customer tier, phone, or status.",
        "parameters": {"customer_id": "string", "tier": "string (optional)", "phone": "string (optional)", "account_status": "string (optional)"}
    }
}

def execute_tool(tool_name: str, params: Dict[str, Any], task_id: str = "general") -> Dict[str, Any]:
    """Execute a registered tool, record execution metrics, and persist tool call log in database.

    Args:
        tool_name: Name of tool to execute
        params: Input parameters dictionary
        task_id: Active task identifier for trace attribution

    Returns:
        Structured result dictionary with latency and execution status.
    """
    start_time = time.time()
    db = SessionLocal()
    status = "success"
    error_msg = None
    result = {}

    try:
        if tool_name == "get_order_status":
            result = get_order_status(order_id=params.get("order_id", ""))
        elif tool_name == "get_customer_info":
            result = get_customer_info(customer_id=params.get("customer_id", ""))
        elif tool_name == "check_refund_eligibility":
            result = check_refund_eligibility(
                order_id=params.get("order_id", ""),
                customer_id=params.get("customer_id")
            )
        elif tool_name == "process_refund":
            result = process_refund(
                order_id=params.get("order_id", ""),
                refund_amount=float(params.get("refund_amount", 0.0)),
                reason=params.get("reason", "Customer request"),
                customer_id=params.get("customer_id")
            )
        elif tool_name == "cancel_order":
            result = cancel_order(
                order_id=params.get("order_id", ""),
                reason=params.get("reason", "Customer request"),
                customer_id=params.get("customer_id")
            )
        elif tool_name == "create_replacement":
            result = create_replacement(
                order_id=params.get("order_id", ""),
                items=params.get("items"),
                reason=params.get("reason", "Defective replacement"),
                customer_id=params.get("customer_id")
            )
        elif tool_name == "reship_order":
            result = reship_order(
                order_id=params.get("order_id", ""),
                carrier=params.get("carrier", "NovaExpress"),
                reason=params.get("reason", "Transit redispatch")
            )
        elif tool_name == "send_customer_email":
            result = send_customer_email(
                customer_id=params.get("customer_id", ""),
                subject=params.get("subject", "NovaCart Support Notification"),
                body=params.get("body", ""),
                case_id=params.get("case_id")
            )
        elif tool_name == "send_whatsapp_message":
            result = send_whatsapp_message(
                customer_id=params.get("customer_id", ""),
                message=params.get("message", ""),
                phone=params.get("phone"),
                case_id=params.get("case_id")
            )
        elif tool_name == "update_support_ticket":
            result = update_support_ticket(
                case_id=params.get("case_id", ""),
                priority=params.get("priority"),
                status=params.get("status"),
                subject=params.get("subject"),
                description=params.get("description")
            )
        elif tool_name == "update_customer_profile":
            result = update_customer_profile(
                customer_id=params.get("customer_id", ""),
                tier=params.get("tier"),
                phone=params.get("phone"),
                account_status=params.get("account_status")
            )
        else:
            status = "failure"
            error_msg = f"Unknown tool '{tool_name}'"
            result = {"success": False, "error": error_msg}

        if not result.get("success", True) and not result.get("eligible", True) and "error" in result:
            status = "failure"
            error_msg = result.get("error")

    except Exception as e:
        status = "failure"
        error_msg = str(e)
        result = {"success": False, "error": error_msg}
    finally:
        duration_ms = int((time.time() - start_time) * 1000)
        try:
            call_log = ToolCall(
                task_id=task_id,
                tool_name=tool_name,
                input_params_json=json.dumps(params),
                output_result_json=json.dumps(result),
                status=status,
                duration_ms=duration_ms,
                error_message=error_msg
            )
            db.add(call_log)
            db.commit()
        except Exception:
            db.rollback()
        finally:
            db.close()

    return {
        "tool_name": tool_name,
        "input": params,
        "result": result,
        "status": status,
        "duration_ms": duration_ms
    }

__all__ = [
    "get_order_status",
    "get_customer_info",
    "check_refund_eligibility",
    "process_refund",
    "cancel_order",
    "create_replacement",
    "reship_order",
    "send_customer_email",
    "send_whatsapp_message",
    "update_support_ticket",
    "update_customer_profile",
    "execute_tool",
    "AVAILABLE_TOOLS"
]
