import json
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database.database import get_db, SessionLocal
from ..database.models import Customer, Order
from ..services.customer_intelligence_service import CustomerIntelligenceService
from ..schemas.customer import (
    Customer360Response,
    CustomerOrderSummarySchema,
    CustomerCaseSummarySchema,
    CustomerActivityItemSchema
)

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
                    items = json.loads(o.items_json) if o.items_json else []
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


@router.get("/{customer_id}/360", response_model=Customer360Response)
def get_customer_360(customer_id: str, db: Session = Depends(get_db)):
    """Retrieve structured Customer 360 intelligence dossier aggregating all 11 customer dimensions."""
    c360 = CustomerIntelligenceService.get_customer_360(db, customer_id)
    if not c360:
        raise HTTPException(status_code=404, detail=f"Customer '{customer_id}' not found.")
    return c360


@router.get("/{customer_id}/cases", response_model=List[CustomerCaseSummarySchema])
def get_customer_cases(customer_id: str, db: Session = Depends(get_db)):
    """Retrieve all support cases and tickets for a customer."""
    customer = db.query(Customer).filter(Customer.customer_id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail=f"Customer '{customer_id}' not found.")
    return CustomerIntelligenceService.get_customer_cases(db, customer_id)


@router.get("/{customer_id}/orders", response_model=List[CustomerOrderSummarySchema])
def get_customer_orders(customer_id: str, db: Session = Depends(get_db)):
    """Retrieve full order portfolio for a customer."""
    customer = db.query(Customer).filter(Customer.customer_id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail=f"Customer '{customer_id}' not found.")
    return CustomerIntelligenceService.get_customer_orders(db, customer_id)


@router.get("/{customer_id}/activity", response_model=List[CustomerActivityItemSchema])
def get_customer_activity(customer_id: str, db: Session = Depends(get_db)):
    """Retrieve chronological unified activity stream for a customer."""
    customer = db.query(Customer).filter(Customer.customer_id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail=f"Customer '{customer_id}' not found.")
    return CustomerIntelligenceService.get_customer_activity(db, customer_id)
