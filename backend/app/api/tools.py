import json
from fastapi import APIRouter
from ..tools import AVAILABLE_TOOLS
from ..database.database import SessionLocal
from ..database.models import ToolCall

router = APIRouter(prefix="/api/tools", tags=["tools"])

@router.get("")
def get_tools_info(limit: int = 30):
    db = SessionLocal()
    try:
        calls = db.query(ToolCall).order_by(ToolCall.created_at.desc()).limit(limit).all()

        call_logs = []
        for c in calls:
            try:
                inp = json.loads(c.input_params_json)
            except Exception:
                inp = c.input_params_json
            try:
                out = json.loads(c.output_result_json)
            except Exception:
                out = c.output_result_json

            call_logs.append({
                "id": c.id,
                "task_id": c.task_id,
                "tool_name": c.tool_name,
                "input": inp,
                "output": out,
                "status": c.status,
                "duration_ms": c.duration_ms,
                "error_message": c.error_message,
                "created_at": c.created_at.isoformat() if c.created_at else None
            })

        return {
            "tools": list(AVAILABLE_TOOLS.values()),
            "recent_executions": call_logs
        }
    finally:
        db.close()
