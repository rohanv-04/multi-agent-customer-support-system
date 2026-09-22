import json
from fastapi import APIRouter
from ..database.database import SessionLocal
from ..database.models import Customer, Order

router = APIRouter(prefix="/api/customers", tags=["customers"])

@router.get("")
def list_customers():
    db = SessionLocal()
    try:
        customers = db.query(Customer).all()
        results = []
        for c in customers:
            orders = db.query(Order).filter(Order.customer_id == c.customer_id).all()
            order_list = []
            for o in orders:
                try:
                    items = json.loads(o.items_json)
                except Exception:
                    items = []
                order_list.append({
                    "order_id": o.order_id,
                    "status": o.status,
                    "total_amount": o.total_amount,
                    "items": items,
                    "carrier": o.carrier,
                    "tracking_number": o.tracking_number,
                    "delay_reason": o.delay_reason
                })

            results.append({
                "customer_id": c.customer_id,
                "name": c.name,
                "email": c.email,
                "tier": c.tier,
                "account_status": c.account_status,
                "orders": order_list
            })
        return {"customers": results}
    finally:
        db.close()
