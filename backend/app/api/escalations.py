import json
import datetime
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from ..database.database import SessionLocal
from ..database.models import EscalationTicket, Customer

router = APIRouter(prefix="/api/escalations", tags=["escalations"])

class StatusUpdateRequest(BaseModel):
    status: str  # open, in_progress, resolved
    assigned_to: Optional[str] = None

@router.get("")
def list_escalations(status: Optional[str] = None):
    db = SessionLocal()
    try:
        query = db.query(EscalationTicket)
        if status:
            query = query.filter(EscalationTicket.status == status.lower())
        tickets = query.order_by(EscalationTicket.created_at.desc()).all()

        results = []
        for t in tickets:
            try:
                actions = json.loads(t.actions_attempted_json or "[]")
            except Exception:
                actions = []
            try:
                tools = json.loads(t.tools_used_json or "[]")
            except Exception:
                tools = []
            try:
                results_list = json.loads(t.results_json or "[]")
            except Exception:
                results_list = []

            results.append({
                "ticket_id": t.ticket_id,
                "customer_id": t.customer_id,
                "task_id": t.task_id,
                "summary": t.summary,
                "intent": t.intent,
                "reason": t.reason,
                "actions_attempted": actions,
                "tools_used": tools,
                "results": results_list,
                "status": t.status,
                "priority": t.priority,
                "recommended_action": t.recommended_action,
                "assigned_to": t.assigned_to,
                "created_at": t.created_at.isoformat() if t.created_at else None,
                "resolved_at": t.resolved_at.isoformat() if t.resolved_at else None
            })

        return {"tickets": results, "total": len(results)}
    finally:
        db.close()

@router.post("/{ticket_id}/status")
def update_escalation_status(ticket_id: str, req: StatusUpdateRequest):
    db = SessionLocal()
    try:
        ticket = db.query(EscalationTicket).filter(EscalationTicket.ticket_id == ticket_id).first()
        if not ticket:
            raise HTTPException(status_code=404, detail="Ticket not found")

        ticket.status = req.status.lower()
        if req.assigned_to:
            ticket.assigned_to = req.assigned_to
        if req.status.lower() == "resolved":
            ticket.resolved_at = datetime.datetime.utcnow()

        db.commit()
        return {"success": True, "ticket_id": ticket_id, "new_status": ticket.status}
    finally:
        db.close()
