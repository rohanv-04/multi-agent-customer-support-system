import uuid
import datetime
from typing import Dict, Any, Optional
from ..database.database import SessionLocal
from ..database.models import Order, get_utc_now


def reship_order(
    order_id: str,
    carrier: str = "NovaExpress",
    reason: str = "Package lost in transit or returned by carrier"
) -> Dict[str, Any]:
    """Execute reshipment dispatch for an existing delayed/lost order."""
    db = SessionLocal()
    try:
        clean_order_id = order_id.strip().upper()
        order = db.query(Order).filter(Order.order_id == clean_order_id).first()

        if not order:
            return {
                "success": False,
                "error": f"Order {clean_order_id} not found.",
                "reshipment_id": None
            }

        reshipment_id = f"RSH-{clean_order_id}-{uuid.uuid4().hex[:6].upper()}"
        new_tracking = f"TRK-RSH-{uuid.uuid4().hex[:8].upper()}"
        now = get_utc_now()

        order.status = "Shipped"
        order.tracking_number = new_tracking
        order.carrier = carrier
        order.expected_delivery = now + datetime.timedelta(days=2)
        order.delay_reason = f"Reshipped: {reason}"
        db.commit()

        return {
            "success": True,
            "reshipment_id": reshipment_id,
            "order_id": order.order_id,
            "new_tracking_number": new_tracking,
            "carrier": carrier,
            "status": "Shipped",
            "reason": reason,
            "timestamp": now.isoformat(),
            "message": f"Successfully re-dispatched order {order.order_id} via {carrier} (Tracking: {new_tracking})."
        }
    except Exception as e:
        db.rollback()
        return {
            "success": False,
            "error": f"Failed to reship order: {str(e)}",
            "reshipment_id": None
        }
    finally:
        db.close()
