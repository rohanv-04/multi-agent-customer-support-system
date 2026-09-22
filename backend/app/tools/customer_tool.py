from typing import Dict, Any
from ..database.database import SessionLocal
from ..database.models import Customer, Order

def get_customer_info(customer_id: str) -> Dict[str, Any]:
    """Fetch customer profile, loyalty tier, account status, and order history.

    Args:
        customer_id: Customer ID (e.g. CUST1002)

    Returns:
        Structured dictionary of customer profile and order summaries.
    """
    db = SessionLocal()
    try:
        clean_cust_id = customer_id.strip().upper()
        customer = db.query(Customer).filter(Customer.customer_id == clean_cust_id).first()
        if not customer:
            return {
                "success": False,
                "error": f"Customer {clean_cust_id} not found.",
                "customer_id": clean_cust_id
            }

        orders = db.query(Order).filter(Order.customer_id == clean_cust_id).all()
        order_summaries = [
            {
                "order_id": o.order_id,
                "status": o.status,
                "total_amount": o.total_amount,
                "currency": o.currency,
                "carrier": o.carrier,
                "tracking_number": o.tracking_number,
                "delay_reason": o.delay_reason
            }
            for o in orders
        ]

        return {
            "success": True,
            "customer_id": customer.customer_id,
            "name": customer.name,
            "email": customer.email,
            "phone": customer.phone,
            "tier": customer.tier,
            "account_status": customer.account_status,
            "orders": order_summaries,
            "order_count": len(order_summaries)
        }
    finally:
        db.close()
