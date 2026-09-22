from typing import Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database.database import get_db
from ..schemas.omnichannel import (
    BusinessEventType,
    BusinessEventPayload,
    ProactiveImpactResult
)
from ..services.proactive_support_service import proactive_support_service

router = APIRouter(prefix="/api/proactive", tags=["proactive"])


@router.post("/events", response_model=ProactiveImpactResult)
def ingest_business_event(
    event: BusinessEventPayload,
    db: Session = Depends(get_db)
):
    """
    Ingests an operational business event (shipment delay, payment failure, delivery failure, etc.),
    evaluates impact on the customer, autonomously provisions a SupportCase, and triggers proactive communication.
    """
    try:
        result = proactive_support_service.evaluate_business_event(db, event)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process business event: {str(e)}")


@router.get("/events")
def list_proactive_event_history():
    """Retrieve history of evaluated proactive business events."""
    return {
        "count": len(proactive_support_service.get_event_history()),
        "events": proactive_support_service.get_event_history()
    }
