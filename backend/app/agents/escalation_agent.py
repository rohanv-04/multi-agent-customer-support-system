import uuid
import json
import datetime
from typing import Dict, Any, List
from ..database.database import SessionLocal
from ..database.models import EscalationTicket

def run_escalation_agent(
    task_id: str,
    customer_id: str,
    user_goal: str,
    intent_data: Dict[str, Any],
    plan: List[str],
    completed_steps: List[str],
    tool_calls: List[Dict[str, Any]],
    observations: List[Dict[str, Any]],
    reason: str = "Automated resolution criteria not met or customer requested human agent."
) -> Dict[str, Any]:
    """Agent 6 — Escalation Agent.

    Compiles an audit-grade Human Support Handoff Dossier and generates a priority ticket in SQLite.
    """
    ticket_suffix = str(uuid.uuid4())[:6].upper()
    ticket_id = f"TICK-{ticket_suffix}"

    tools_used = [tc.get("tool_name") for tc in tool_calls if tc.get("tool_name")]
    results = [obs.get("observation") for obs in observations if obs.get("observation")]

    recommended_next_action = "Review customer request, verify order telemetry, and assist manually."
    if intent_data.get("intent") == "human_escalation":
        recommended_next_action = "Initiate live customer chat; acknowledge request immediately."
    elif any("failed" in r.lower() for r in results):
        recommended_next_action = "Investigate system/carrier API exception and manually override refund if eligible."

    dossier = {
        "ticket_id": ticket_id,
        "customer_id": customer_id,
        "task_id": task_id,
        "summary": f"Human assistance requested for: '{user_goal}'",
        "intent": intent_data.get("intent", "general_inquiry"),
        "actions_attempted": completed_steps,
        "tools_used": tools_used,
        "results": results,
        "reason": reason,
        "recommended_next_action": recommended_next_action,
        "created_at": datetime.datetime.utcnow().isoformat()
    }

    # Save to database
    db = SessionLocal()
    try:
        ticket = EscalationTicket(
            ticket_id=ticket_id,
            customer_id=customer_id,
            task_id=task_id,
            summary=dossier["summary"],
            intent=dossier["intent"],
            reason=reason,
            actions_attempted_json=json.dumps(completed_steps),
            tools_used_json=json.dumps(tools_used),
            results_json=json.dumps(results),
            status="open",
            priority="high",
            recommended_action=recommended_next_action,
            created_at=datetime.datetime.utcnow()
        )
        db.add(ticket)
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"[Escalation Agent DB Error]: {e}")
    finally:
        db.close()

    return dossier
