import uuid
import datetime
from typing import Dict, Any, Optional, List
from ..database.database import SessionLocal
from ..database.models import Order, Customer, get_utc_now


def create_replacement(
    order_id: str,
    items: Optional[List[str]] = None,
    reason: str = "Damaged or defective item replacement",
    customer_id: Optional[str] = None
) -> Dict[str, Any]:
    """Execute creation of a replacement order in NovaCart database."""
    db = SessionLocal()
    try:
        clean_order_id = order_id.strip().upper()
        orig_order = db.query(Order).filter(Order.order_id == clean_order_id).first()

        if not orig_order:
            return {
                "success": False,
                "error": f"Original order {clean_order_id} not found.",
                "replacement_id": None
            }

        target_customer_id = customer_id or orig_order.customer_id
        replacement_id = f"RPL-{clean_order_id}-{uuid.uuid4().hex[:6].upper()}"
        new_order_id = f"ORD-{uuid.uuid4().hex[:5].upper()}"
        now = get_utc_now()

        # Create replacement order entry
        replacement_order = Order(
            order_id=new_order_id,
            customer_id=target_customer_id,
            status="Processing",
            items_json=orig_order.items_json,
            total_amount=0.00,  # Complimentary replacement
            currency=orig_order.currency,
            tracking_number=f"TRK-RPL-{uuid.uuid4().hex[:8].upper()}",
            carrier=orig_order.carrier or "NovaExpress",
            order_date=now,
            expected_delivery=now + datetime.timedelta(days=2),
            delay_reason=f"Replacement for {orig_order.order_id}: {reason}",
            created_at=now
        )
        db.add(replacement_order)
        db.commit()

        return {
            "success": True,
            "replacement_id": replacement_id,
            "original_order_id": orig_order.order_id,
            "replacement_order_id": new_order_id,
            "customer_id": target_customer_id,
            "tracking_number": replacement_order.tracking_number,
            "carrier": replacement_order.carrier,
            "status": "Processing",
            "reason": reason,
            "timestamp": now.isoformat(),
            "message": f"Successfully authorized and generated replacement order {new_order_id} for order {orig_order.order_id}."
        }
    except Exception as e:
        db.rollback()
        return {
            "success": False,
            "error": f"Failed to create replacement: {str(e)}",
            "replacement_id": None
        }
    finally:
        db.close()
