import json
from typing import Dict, Any
from ..database.database import SessionLocal
from ..database.models import Order

def get_order_status(order_id: str) -> Dict[str, Any]:
    """Retrieve detailed order status, carrier info, tracking, and delay diagnostics.

    Args:
        order_id: The unique identifier of the order (e.g. ORD10002)

    Returns:
        Structured dictionary containing order details and current shipment state.
    """
    db = SessionLocal()
    try:
        clean_order_id = order_id.strip().upper()
        order = db.query(Order).filter(Order.order_id == clean_order_id).first()
        if not order:
            return {
                "success": False,
                "error": f"Order {clean_order_id} not found in NovaCart systems.",
                "order_id": clean_order_id
            }

        items = []
        try:
            items = json.loads(order.items_json)
        except Exception:
            items = [{"raw": order.items_json}]

        return {
            "success": True,
            "order_id": order.order_id,
            "customer_id": order.customer_id,
            "status": order.status,
            "items": items,
            "total_amount": order.total_amount,
            "currency": order.currency,
            "tracking_number": order.tracking_number,
            "carrier": order.carrier,
            "order_date": order.order_date.isoformat() if order.order_date else None,
            "expected_delivery": order.expected_delivery.isoformat() if order.expected_delivery else None,
            "actual_delivery": order.actual_delivery.isoformat() if order.actual_delivery else None,
            "delay_reason": order.delay_reason
        }
    finally:
        db.close()
