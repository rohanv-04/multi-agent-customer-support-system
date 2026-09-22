import time
import json
from typing import Dict, Any
from .order_tool import get_order_status
from .customer_tool import get_customer_info
from .eligibility_tool import check_refund_eligibility
from .refund_tool import process_refund
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
    "execute_tool",
    "AVAILABLE_TOOLS"
]
