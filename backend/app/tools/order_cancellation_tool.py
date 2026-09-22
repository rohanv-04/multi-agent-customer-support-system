import uuid
import datetime
from typing import Dict, Any, Optional
from ..database.database import SessionLocal
from ..database.models import Order, Customer, get_utc_now


def cancel_order(order_id: str, reason: str = "Customer requested cancellation", customer_id: Optional[str] = None) -> Dict[str, Any]:
    """Execute order cancellation in NovaCart database.
    
    Validates that the order exists, is in a cancellable state (Processing),
    and updates status to Cancelled.
    """
    db = SessionLocal()
    try:
        clean_order_id = order_id.strip().upper()
        order = db.query(Order).filter(Order.order_id == clean_order_id).first()

        if not order:
            return {
                "success": False,
                "error": f"Order {clean_order_id} not found in records.",
                "cancellation_id": None
            }

        if order.status in ["Cancelled", "Refunded"]:
            return {
                "success": False,
                "error": f"Order {clean_order_id} has already been {order.status.lower()}.",
                "cancellation_id": None
            }

        if order.status in ["Shipped", "Delivered"]:
            return {
                "success": False,
                "error": f"Order {clean_order_id} is already in status '{order.status}'. Cannot cancel post-dispatch.",
                "cancellation_id": None
            }

        target_customer_id = customer_id or order.customer_id
        if customer_id and customer_id.strip().upper() != order.customer_id:
            return {
                "success": False,
                "error": f"Customer ID mismatch: Order {clean_order_id} does not belong to {customer_id}.",
                "cancellation_id": None
            }

        cancellation_id = f"CAN-{clean_order_id}-{uuid.uuid4().hex[:6].upper()}"
        now = get_utc_now()
        order.status = "Cancelled"
        order.delay_reason = f"Cancelled: {reason}"
        db.commit()

        return {
            "success": True,
            "cancellation_id": cancellation_id,
            "order_id": order.order_id,
            "customer_id": target_customer_id,
            "previous_status": "Processing",
            "new_status": "Cancelled",
            "reason": reason,
            "timestamp": now.isoformat(),
            "message": f"Successfully cancelled order {order.order_id} prior to dispatch."
        }
    except Exception as e:
        db.rollback()
        return {
            "success": False,
            "error": f"Failed to cancel order: {str(e)}",
            "cancellation_id": None
        }
    finally:
        db.close()
