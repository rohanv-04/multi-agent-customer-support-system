from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import Optional

from ..database.database import get_db
from ..services.human_support_service import human_support_service
from ..schemas.human_support import (
    HumanSupportAssignmentRequest,
    HumanSupportAssignmentResponse,
    CallInitiatedResponse
)

router = APIRouter(prefix="/api/cases", tags=["Human Support"])


@router.post("/{case_id}/human-support", response_model=HumanSupportAssignmentResponse)
def request_human_support(
    case_id: str,
    payload: Optional[HumanSupportAssignmentRequest] = None,
    customer_id: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """Assign a dedicated human support representative randomly to a case and log escalation timeline events."""
    effective_customer_id = (payload and payload.customer_id) or customer_id or "CUST1002"
    notes = payload.notes if payload else None

    try:
        assignment = human_support_service.assign_human_support(
            db=db,
            case_id=case_id,
            customer_id=effective_customer_id,
            notes=notes
        )
        return assignment
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to assign human support: {str(e)}"
        )


@router.post("/{case_id}/human-support/{assignment_id}/call", response_model=CallInitiatedResponse)
def record_call_initiated(
    case_id: str,
    assignment_id: str,
    db: Session = Depends(get_db)
):
    """Record that the customer initiated a call via the tel: link.

    Note: Does NOT mark call as COMPLETED as telephony connection is not verified.
    """
    try:
        result = human_support_service.record_call_initiated(
            db=db,
            case_id=case_id,
            assignment_id=assignment_id
        )
        return result
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ve))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to record call initiation: {str(e)}"
        )


@router.get("/{case_id}/human-support", response_model=Optional[HumanSupportAssignmentResponse])
def get_case_human_support(
    case_id: str,
    db: Session = Depends(get_db)
):
    """Get active human support assignment for a case if one exists."""
    assignment = human_support_service.get_assignment_for_case(db=db, case_id=case_id)
    if not assignment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No human support assignment found for this case")
    return assignment


# Standalone telephony endpoint for Section 25
telephony_router = APIRouter(prefix="/api/human-support", tags=["Telephony Provider"])


@telephony_router.post("/call")
def dispatch_human_support_call(
    payload: dict,
    db: Session = Depends(get_db)
):
    """Dispatches an outbound phone call via configured TelephonyProvider (Twilio or Mock).
    Request: {"case_id": "...", "agent_id": "kavin" | "rohan" | "narahari"}
    """
    case_id = payload.get("case_id")
    agent_id = (payload.get("agent_id") or payload.get("representative_id") or "kavin").lower()

    # Find contact
    contacts = human_support_service.get_configured_contacts()
    target_contact = next((c for c in contacts if c["id"].lower() == agent_id), contacts[0])
    to_phone = target_contact["phone"]

    # Dispatch via TelephonyProvider
    call_record = human_support_service.telephony_provider.initiate_outbound_call(
        to_phone=to_phone,
        from_phone="+18005550199",
        metadata={"case_id": case_id, "representative": target_contact["name"]}
    )

    return {
        "success": True,
        "case_id": case_id,
        "representative": target_contact["name"],
        "call_sid": call_record.get("call_sid"),
        "status": call_record.get("status"),
        "provider": call_record.get("provider"),
        "message": f"Connecting support call with representative {target_contact['name']} ({to_phone})."
    }
