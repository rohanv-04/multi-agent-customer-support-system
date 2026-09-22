from typing import List, Optional
from fastapi import APIRouter, HTTPException
from ..database.database import SessionLocal
from ..database.models import Task, TaskStep, ToolCall, AgentAction

router = APIRouter(prefix="/api/tasks", tags=["tasks"])

@router.get("")
def list_tasks(limit: int = 20, customer_id: Optional[str] = None):
    db = SessionLocal()
    try:
        query = db.query(Task)
        if customer_id:
            query = query.filter(Task.customer_id == customer_id.strip().upper())
        tasks = query.order_by(Task.created_at.desc()).limit(limit).all()

        return [
            {
                "task_id": t.task_id,
                "conversation_id": t.conversation_id,
                "customer_id": t.customer_id,
                "user_goal": t.user_goal,
                "intent": t.intent,
                "confidence": t.confidence,
                "status": t.status,
                "replan_count": t.replan_count,
                "created_at": t.created_at.isoformat() if t.created_at else None,
                "completed_at": t.completed_at.isoformat() if t.completed_at else None,
            }
            for t in tasks
        ]
    finally:
        db.close()

@router.get("/{task_id}")
def get_task_detail(task_id: str):
    db = SessionLocal()
    try:
        task = db.query(Task).filter(Task.task_id == task_id).first()
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")

        steps = db.query(TaskStep).filter(TaskStep.task_id == task_id).order_by(TaskStep.step_number.asc()).all()
        tool_calls = db.query(ToolCall).filter(ToolCall.task_id == task_id).order_by(ToolCall.created_at.asc()).all()

        return {
            "task_id": task.task_id,
            "conversation_id": task.conversation_id,
            "customer_id": task.customer_id,
            "user_goal": task.user_goal,
            "intent": task.intent,
            "confidence": task.confidence,
            "status": task.status,
            "replan_count": task.replan_count,
            "created_at": task.created_at.isoformat() if task.created_at else None,
            "completed_at": task.completed_at.isoformat() if task.completed_at else None,
            "steps": [
                {
                    "step_number": s.step_number,
                    "description": s.description,
                    "status": s.status,
                    "result_summary": s.result_summary
                }
                for s in steps
            ],
            "tool_calls": [
                {
                    "tool_name": tc.tool_name,
                    "status": tc.status,
                    "duration_ms": tc.duration_ms,
                    "error_message": tc.error_message,
                    "created_at": tc.created_at.isoformat() if tc.created_at else None
                }
                for tc in tool_calls
            ]
        }
    finally:
        db.close()
