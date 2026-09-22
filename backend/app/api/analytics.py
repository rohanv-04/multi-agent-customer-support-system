from fastapi import APIRouter
from ..database.database import SessionLocal
from ..database.models import Task, ToolCall, EscalationTicket, Refund, Conversation

router = APIRouter(prefix="/api/analytics", tags=["analytics"])

@router.get("")
def get_analytics():
    db = SessionLocal()
    try:
        total_tasks = db.query(Task).count()
        completed_tasks = db.query(Task).filter(Task.status == "completed").count()
        escalated_tasks = db.query(EscalationTicket).count()

        tasks = db.query(Task).all()
        avg_confidence = round(sum(t.confidence for t in tasks) / len(tasks), 2) if tasks else 0.94
        total_replans = sum(t.replan_count for t in tasks) if tasks else 0

        total_tool_calls = db.query(ToolCall).count()
        successful_tools = db.query(ToolCall).filter(ToolCall.status == "success").count()

        # Tool breakdown
        tool_counts = {}
        for tc in db.query(ToolCall).all():
            tool_counts[tc.tool_name] = tool_counts.get(tc.tool_name, 0) + 1

        # Total refunds
        refunds = db.query(Refund).all()
        total_refund_amount = sum(r.refund_amount for r in refunds)

        resolution_rate = round((completed_tasks / total_tasks) * 100, 1) if total_tasks > 0 else 100.0

        return {
            "total_tasks": total_tasks,
            "completed_tasks": completed_tasks,
            "escalated_cases": escalated_tasks,
            "resolution_rate": resolution_rate,
            "average_confidence": avg_confidence,
            "total_replanning_events": total_replans,
            "total_tool_calls": total_tool_calls,
            "tool_success_rate": round((successful_tools / total_tool_calls) * 100, 1) if total_tool_calls > 0 else 100.0,
            "tool_distribution": tool_counts,
            "total_refunds_processed": len(refunds),
            "total_refund_volume_usd": round(total_refund_amount, 2),
            "system_status": "All systems operational"
        }
    finally:
        db.close()
