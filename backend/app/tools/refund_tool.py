import uuid
import datetime
from typing import Dict, Any
from ..database.database import SessionLocal
from ..database.models import Order, Refund, Customer

def process_refund(order_id: str, refund_amount: float, reason: str, customer_id: str = None) -> Dict[str, Any]:
    """Execute a real, safe financial refund transaction for an eligible NovaCart order.

    Performs database transaction:
    - Verifies order and customer
    - Creates persistent Refund record
    - Updates Order status to 'Refunded'
    - Generates traceable transaction receipt

    Args:
        order_id: Order identifier (e.g. ORD10002)
        refund_amount: Monetary amount to credit back
        reason: Justification (e.g. "Severe shipping delay > 3 business days")
        customer_id: Customer ID for audit logging

    Returns:
        Structured receipt with refund_id, status, timestamp, and updated order details.
    """
    db = SessionLocal()
    try:
        clean_order_id = order_id.strip().upper()
        order = db.query(Order).filter(Order.order_id == clean_order_id).first()

        if not order:
            return {
                "success": False,
                "error": f"Order {clean_order_id} not found in database.",
                "refund_id": None
            }

        if order.status == "Refunded":
            return {
                "success": False,
                "error": f"Order {clean_order_id} is already refunded.",
                "refund_id": None
            }

        # Safety: check customer ID if provided
        target_customer_id = customer_id or order.customer_id
        if customer_id and customer_id.strip().upper() != order.customer_id:
            return {
                "success": False,
                "error": f"Customer ID mismatch: Order {clean_order_id} does not belong to {customer_id}.",
                "refund_id": None
            }

        # Generate unique transaction receipt ID
        receipt_suffix = str(uuid.uuid4())[:8].upper()
        refund_id = f"REF-{clean_order_id}-{receipt_suffix}"
        now = datetime.datetime.utcnow()

        # Database write: create Refund record
        refund_record = Refund(
            refund_id=refund_id,
            order_id=order.order_id,
            customer_id=target_customer_id,
            refund_amount=float(refund_amount),
            currency=order.currency,
            status="processed",
            reason=reason,
            refund_method="Original Payment Method",
            processed_at=now
        )
        db.add(refund_record)

        # Update order status
        order.status = "Refunded"
        db.commit()

        return {
            "success": True,
            "refund_id": refund_id,
            "order_id": order.order_id,
            "customer_id": target_customer_id,
            "refund_amount": float(refund_amount),
            "currency": order.currency,
            "status": "processed",
            "reason": reason,
            "timestamp": now.isoformat(),
            "message": f"Successfully processed full refund of ${refund_amount:.2f} {order.currency} for order {order.order_id} to original payment method."
        }
    except Exception as e:
        db.rollback()
        return {
            "success": False,
            "error": f"Failed to execute refund transaction: {str(e)}",
            "refund_id": None
        }
    finally:
        db.close()
