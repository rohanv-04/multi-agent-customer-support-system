from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from ..database.database import get_db
from ..database.models import SupportCase, Customer, get_utc_now
from ..schemas.case import (
    CaseCreate,
    CaseUpdate,
    CaseResponse,
    CaseDetailResponse,
    CaseMessageCreate,
    CaseMessageResponse,
    CaseEventResponse,
    TimelineItemResponse
)
from ..services.case_service import CaseService, InvalidStateTransitionError

from ..core.security import get_current_user, require_permission
from ..database.models import User
from ..schemas.auth import Permission, UserRole

router = APIRouter(prefix="/api/cases", tags=["cases"])


@router.post("", response_model=CaseResponse, status_code=201)
def create_case(
    req: CaseCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new Support Case within tenant boundary."""
    try:
        # Assign tenant boundary from authenticated context
        if not req.organization_id or current_user.role != UserRole.ADMIN.value:
            req.organization_id = current_user.organization_id

        case = CaseService.create_case(db, req)
        return case
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("", response_model=List[CaseResponse])
def list_cases(
    status: Optional[str] = Query(None, description="Filter by status (NEW, TRIAGING, INVESTIGATING, etc.)"),
    priority: Optional[str] = Query(None, description="Filter by priority (low, medium, high, urgent)"),
    customer_id: Optional[str] = Query(None, description="Filter by customer ID"),
    channel: Optional[str] = Query(None, description="Filter by channel (web_chat, email, api, portal)"),
    search: Optional[str] = Query(None, description="Keyword search in subject, description, or intent"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(require_permission(Permission.VIEW_CASES.value)),
    db: Session = Depends(get_db)
):
    """List support cases strictly scoped to authenticated user's organization."""
    # If customer role, only return cases associated with their customer profile
    effective_cust_id = customer_id
    if current_user.role == UserRole.CUSTOMER.value:
        # Find customer profile matching email
        cust = db.query(Customer).filter(Customer.email == current_user.email, Customer.organization_id == current_user.organization_id).first()
        if cust:
            effective_cust_id = cust.customer_id

    return CaseService.list_cases(
        db=db,
        status=status,
        priority=priority,
        customer_id=effective_cust_id,
        channel=channel,
        search=search,
        organization_id=current_user.organization_id,
        limit=limit,
        offset=offset
    )


@router.get("/{case_id}", response_model=CaseDetailResponse)
def get_case(
    case_id: str,
    current_user: User = Depends(require_permission(Permission.VIEW_CASES.value)),
    db: Session = Depends(get_db)
):
    """Retrieve detailed support case profile with tenant isolation enforcement."""
    case = CaseService.get_case(db, case_id)
    if not case:
        raise HTTPException(status_code=404, detail=f"Support case '{case_id}' not found.")

    # Enforce multi-tenant boundary
    if case.organization_id != current_user.organization_id and current_user.role != UserRole.ADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Forbidden: Access to case '{case_id}' is restricted to organization '{case.organization_id}'."
        )

    customer = db.query(Customer).filter(Customer.customer_id == case.customer_id).first()
    now = get_utc_now()

    is_breached = False
    minutes_remaining = None
    if case.sla_deadline:
        diff = (case.sla_deadline - now).total_seconds() / 60.0
        minutes_remaining = round(diff, 1)
        if diff < 0 and case.status not in ["RESOLVED", "CLOSED"]:
            is_breached = True

    return CaseDetailResponse(
        id=case.id,
        organization_id=case.organization_id,
        customer_id=case.customer_id,
        conversation_id=case.conversation_id,
        channel=case.channel,
        subject=case.subject,
        description=case.description,
        intent=case.intent,
        sentiment=case.sentiment,
        priority=case.priority,
        status=case.status,
        sla_deadline=case.sla_deadline,
        created_at=case.created_at,
        updated_at=case.updated_at,
        resolved_at=case.resolved_at,
        customer_name=customer.name if customer else None,
        customer_email=customer.email if customer else None,
        customer_tier=customer.tier if customer else "Standard",
        message_count=len(case.messages),
        event_count=len(case.events),
        agent_run_count=len(case.agent_runs),
        action_count=len(case.actions),
        is_sla_breached=is_breached,
        sla_minutes_remaining=minutes_remaining
    )


@router.patch("/{case_id}", response_model=CaseResponse)
def update_case(
    case_id: str,
    req: CaseUpdate,
    current_user: User = Depends(require_permission(Permission.MODIFY_CASES.value)),
    db: Session = Depends(get_db)
):
    """Update case attributes or trigger lifecycle transitions."""
    case = CaseService.get_case(db, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    if case.organization_id != current_user.organization_id and current_user.role != UserRole.ADMIN.value:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot modify case from another organization")

    try:
        updated_case = CaseService.update_case(db, case_id, req)
        return updated_case
    except InvalidStateTransitionError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{case_id}/messages", response_model=List[CaseMessageResponse])
def get_case_messages(
    case_id: str,
    current_user: User = Depends(require_permission(Permission.VIEW_CASES.value)),
    db: Session = Depends(get_db)
):
    """Retrieve all inbound and outbound messages associated with the case."""
    case = CaseService.get_case(db, case_id)
    if not case:
        raise HTTPException(status_code=404, detail=f"Support case '{case_id}' not found.")
    if case.organization_id != current_user.organization_id and current_user.role != UserRole.ADMIN.value:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cross-tenant access prohibited.")
    return case.messages


@router.post("/{case_id}/messages", response_model=CaseMessageResponse, status_code=201)
def add_case_message(
    case_id: str,
    req: CaseMessageCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Add a new inbound or outbound message to a support case."""
    case = CaseService.get_case(db, case_id)
    if not case:
        raise HTTPException(status_code=404, detail=f"Support case '{case_id}' not found.")
    if case.organization_id != current_user.organization_id and current_user.role != UserRole.ADMIN.value:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cross-tenant access prohibited.")
    try:
        msg = CaseService.add_case_message(db, case_id, req)
        return msg
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{case_id}/events", response_model=List[CaseEventResponse])
def get_case_events(
    case_id: str,
    current_user: User = Depends(require_permission(Permission.VIEW_CASES.value)),
    db: Session = Depends(get_db)
):
    """Retrieve the operational and state transition event stream for a case."""
    case = CaseService.get_case(db, case_id)
    if not case:
        raise HTTPException(status_code=404, detail=f"Support case '{case_id}' not found.")
    if case.organization_id != current_user.organization_id and current_user.role != UserRole.ADMIN.value:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cross-tenant access prohibited.")
    return case.events


@router.get("/{case_id}/timeline", response_model=List[TimelineItemResponse])
def get_case_timeline(
    case_id: str,
    current_user: User = Depends(require_permission(Permission.VIEW_CASES.value)),
    db: Session = Depends(get_db)
):
    """Retrieve a unified chronological timeline (messages, events, agent runs, actions, escalations)."""
    case = CaseService.get_case(db, case_id)
    if not case:
        raise HTTPException(status_code=404, detail=f"Support case '{case_id}' not found.")
    if case.organization_id != current_user.organization_id and current_user.role != UserRole.ADMIN.value:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cross-tenant access prohibited.")
    return CaseService.get_case_timeline(db, case_id)


@router.post("/{case_id}/actions/{action_id}/review")
def review_case_action(
    case_id: str,
    action_id: str,
    status_choice: str = Query(..., description="approved or rejected"),
    reason: Optional[str] = Query(None, description="Review justification"),
    current_user: User = Depends(require_permission(Permission.APPROVE_ACTIONS.value)),
    db: Session = Depends(get_db)
):
    """Supervisor / Admin review and execution of pending business actions."""
    import json
    import uuid
    from ..database.models import AgentAction
    from ..services.action_gateway import ActionGateway
    from ..schemas.action_gateway import ActionRequest

    case = CaseService.get_case(db, case_id)
    if not case:
        raise HTTPException(status_code=404, detail=f"Case {case_id} not found")
    if case.organization_id != current_user.organization_id and current_user.role != UserRole.ADMIN.value:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cross-tenant access prohibited")

    action = db.query(AgentAction).filter(AgentAction.case_id == case_id, AgentAction.id == action_id).first()
    if not action:
        action = db.query(AgentAction).filter(AgentAction.case_id == case_id).first()

    if not action:
        raise HTTPException(status_code=404, detail="Action not found on case")

    if status_choice.lower() == "approved":
        params = {}
        try:
            if action.input_summary:
                params = json.loads(action.input_summary) if isinstance(action.input_summary, str) else action.input_summary
        except Exception:
            params = {}

        req = ActionRequest(
            case_id=case_id,
            action_type=action.action_type or "refund",
            actor=current_user.name,
            actor_role="supervisor",
            parameters=params,
            justification=reason or f"Approved by {current_user.name} ({current_user.role})",
            idempotency_key=f"APP-{action_id}-{uuid.uuid4().hex[:6]}"
        )
        res = ActionGateway.approve_action(db=db, request=req, approved_by=f"{current_user.name} ({current_user.role})")
        action.status = "approved"
        db.commit()
        return {"success": True, "action_id": action_id, "status": "approved", "result": res.model_dump()}
    else:
        action.status = "rejected"
        db.commit()
        return {"success": True, "action_id": action_id, "status": "rejected", "reason": reason}
