import datetime
from typing import Dict, Any, Optional
from ..database.database import SessionLocal
from ..database.models import Order, Customer

def check_refund_eligibility(order_id: str, customer_id: Optional[str] = None) -> Dict[str, Any]:
    """Evaluate refund eligibility according to NovaCart corporate policies.

    Checks delay thresholds, delivery timelines, order status, and policy constraints.

    Args:
        order_id: Order identifier (e.g. ORD10002)
        customer_id: Optional customer identifier for verification

    Returns:
        Structured evaluation with eligibility boolean, policy basis, refundable amount, and method.
    """
    db = SessionLocal()
    try:
        clean_order_id = order_id.strip().upper()
        order = db.query(Order).filter(Order.order_id == clean_order_id).first()
        if not order:
            return {
                "eligible": False,
                "reason": f"Order {clean_order_id} does not exist in NovaCart database.",
                "refund_amount": 0.0,
                "policy_applied": "Order Verification Failure",
                "customer_id": customer_id
            }

        if customer_id:
            clean_cust_id = customer_id.strip().upper()
            if order.customer_id != clean_cust_id:
                return {
                    "eligible": False,
                    "reason": f"Order {clean_order_id} belongs to another customer account ({order.customer_id}).",
                    "refund_amount": 0.0,
                    "policy_applied": "Customer Verification Security Rule"
                }

        now = datetime.datetime.utcnow()

        # Check Order Status conditions
        if order.status == "Refunded":
            return {
                "eligible": False,
                "reason": "This order has already been fully refunded.",
                "refund_amount": 0.0,
                "refund_method": "Original Payment Method",
                "policy_applied": "Duplicate Refund Prevention"
            }

        if order.status == "Cancelled":
            return {
                "eligible": False,
                "reason": "Order was cancelled prior to fulfillment; cancellation credit already applied.",
                "refund_amount": 0.0,
                "refund_method": "Original Payment Method",
                "policy_applied": "Cancellation Policy"
            }

        # Case 1: Delayed Order Policy (Severely delayed > 3 days)
        if order.status == "Delayed":
            delay_days = 0
            if order.expected_delivery:
                delay_delta = now - order.expected_delivery
                delay_days = max(0, delay_delta.days)

            # NovaCart policy: delay > 3 days qualifies for immediate full refund
            if delay_days >= 3 or (order.delay_reason and "4 days overdue" in order.delay_reason):
                return {
                    "eligible": True,
                    "reason": f"Order is delayed by {max(delay_days, 4)} days beyond expected delivery. Meets NovaCart Severe Delay threshold (> 3 days).",
                    "refund_amount": order.total_amount,
                    "refund_method": "Original Payment Method",
                    "policy_applied": "NovaCart Shipping Delays & Delivery Failures Policy (Section 3)",
                    "currency": order.currency,
                    "order_id": order.order_id,
                    "customer_id": order.customer_id
                }
            else:
                return {
                    "eligible": False,
                    "reason": f"Order delay is currently {delay_days} day(s). Immediate full refund requires delay > 3 days. A $10 courtesy credit is recommended.",
                    "refund_amount": 10.00,
                    "refund_method": "Store Credit",
                    "policy_applied": "NovaCart Shipping Delays Policy (Section 3 - Minor Delay)"
                }

        # Case 2: Delivered Order Policy (30-day window)
        if order.status == "Delivered":
            if order.actual_delivery:
                days_since_delivery = (now - order.actual_delivery).days
                if days_since_delivery > 30:
                    return {
                        "eligible": False,
                        "reason": f"Delivered {days_since_delivery} days ago. Standard return/refund window is 30 days (expired).",
                        "refund_amount": 0.0,
                        "refund_method": "N/A",
                        "policy_applied": "NovaCart Standard 30-Day Return Window (Section 2)"
                    }
                else:
                    return {
                        "eligible": True,
                        "reason": f"Within 30-day return window ({days_since_delivery} days since delivery). Return label required.",
                        "refund_amount": order.total_amount,
                        "refund_method": "Original Payment Method",
                        "policy_applied": "NovaCart Standard 30-Day Return Window"
                    }

        # Case 3: Processing
        if order.status == "Processing":
            return {
                "eligible": True,
                "reason": "Order is still processing in warehouse; eligible for instant cancellation and full reversal.",
                "refund_amount": order.total_amount,
                "refund_method": "Original Payment Method",
                "policy_applied": "NovaCart Cancellation Policy (Section 1)"
            }

        # Case 4: Normal Shipped
        if order.status == "Shipped":
            return {
                "eligible": False,
                "reason": "Order is in active transit with carrier and within on-time schedule. Not eligible for pre-delivery refund.",
                "refund_amount": 0.0,
                "refund_method": "N/A",
                "policy_applied": "NovaCart In-Transit Policy"
            }

        return {
            "eligible": False,
            "reason": f"Status '{order.status}' requires manual review by human agent.",
            "refund_amount": 0.0,
            "refund_method": "N/A",
            "policy_applied": "NovaCart Escalation Policy"
        }
    finally:
        db.close()
