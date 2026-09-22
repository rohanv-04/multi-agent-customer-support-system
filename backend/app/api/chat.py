import uuid
import json
import asyncio
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from ..graph.workflow import support_graph
from ..graph.state import AgenticSupportState
from ..database.database import SessionLocal
from ..database.models import Conversation, Message

router = APIRouter(prefix="/api/chat", tags=["chat"])

class ChatRequest(BaseModel):
    message: str
    customer_id: Optional[str] = "CUST1002"
    conversation_id: Optional[str] = None
    stream: Optional[bool] = False

class ChatResponse(BaseModel):
    task_id: str
    conversation_id: str
    customer_id: str
    response: str
    intent: Dict[str, Any]
    plan: list
    completed_steps: list
    confidence: float
    status: str
    requires_escalation: bool
    replan_count: int
    tool_calls: list
    execution_trace: list
    escalation_dossier: Optional[Dict[str, Any]] = None

@router.post("", response_model=ChatResponse)
async def chat_endpoint(req: ChatRequest):
    conv_id = req.conversation_id or f"conv-{uuid.uuid4().hex[:8]}"
    task_id = f"task-{uuid.uuid4().hex[:8]}"

    # Save user message to database
    db = SessionLocal()
    try:
        conv = db.query(Conversation).filter(Conversation.conversation_id == conv_id).first()
        if not conv:
            conv = Conversation(
                conversation_id=conv_id,
                customer_id=req.customer_id or "CUST1002",
                title=req.message[:50]
            )
            db.add(conv)
            db.commit()

        user_msg = Message(
            conversation_id=conv_id,
            role="user",
            content=req.message
        )
        db.add(user_msg)
        db.commit()
    finally:
        db.close()

    initial_state: AgenticSupportState = {
        "task_id": task_id,
        "customer_id": req.customer_id or "CUST1002",
        "conversation_id": conv_id,
        "user_goal": req.message,
        "messages": [{"role": "user", "content": req.message}],
        "intent": {},
        "plan": [],
        "completed_steps": [],
        "pending_steps": [],
        "agent_outputs": [],
        "tool_calls": [],
        "observations": [],
        "retrieved_docs": [],
        "confidence": 0.0,
        "status": "in_progress",
        "requires_escalation": False,
        "replan_count": 0,
        "iteration_count": 0,
        "critic_result": {},
        "escalation_dossier": None,
        "final_response": "",
        "execution_trace": []
    }

    # Execute LangGraph
    final_state = support_graph.invoke(initial_state)

    # Save assistant message to database
    db = SessionLocal()
    try:
        assistant_msg = Message(
            conversation_id=conv_id,
            role="assistant",
            content=final_state["final_response"],
            metadata_json=json.dumps({
                "task_id": task_id,
                "confidence": final_state["confidence"],
                "status": final_state["status"]
            })
        )
        db.add(assistant_msg)
        db.commit()
    finally:
        db.close()

    return ChatResponse(
        task_id=final_state["task_id"],
        conversation_id=conv_id,
        customer_id=final_state["customer_id"],
        response=final_state["final_response"],
        intent=final_state.get("intent", {}),
        plan=final_state.get("plan", []),
        completed_steps=final_state.get("completed_steps", []),
        confidence=final_state.get("confidence", 0.95),
        status=final_state.get("status", "completed"),
        requires_escalation=final_state.get("requires_escalation", False),
        replan_count=final_state.get("replan_count", 0),
        tool_calls=final_state.get("tool_calls", []),
        execution_trace=final_state.get("execution_trace", []),
        escalation_dossier=final_state.get("escalation_dossier")
    )

@router.post("/stream")
async def chat_stream_endpoint(req: ChatRequest):
    """Server-Sent Events (SSE) streaming endpoint emitting real-time agent execution events."""
    async def event_generator():
        conv_id = req.conversation_id or f"conv-{uuid.uuid4().hex[:8]}"
        task_id = f"task-{uuid.uuid4().hex[:8]}"

        initial_state: AgenticSupportState = {
            "task_id": task_id,
            "customer_id": req.customer_id or "CUST1002",
            "conversation_id": conv_id,
            "user_goal": req.message,
            "messages": [{"role": "user", "content": req.message}],
            "intent": {},
            "plan": [],
            "completed_steps": [],
            "pending_steps": [],
            "agent_outputs": [],
            "tool_calls": [],
            "observations": [],
            "retrieved_docs": [],
            "confidence": 0.0,
            "status": "in_progress",
            "requires_escalation": False,
            "replan_count": 0,
            "iteration_count": 0,
            "critic_result": {},
            "escalation_dossier": None,
            "final_response": "",
            "execution_trace": []
        }

        # Run graph
        final_state = support_graph.invoke(initial_state)

        # Stream execution trace events chronologically
        for trace in final_state["execution_trace"]:
            yield f"data: {json.dumps({'type': 'trace_event', 'trace': trace})}\n\n"
            await asyncio.sleep(0.08)  # Realistic smooth spatial visual pacing

        # Emit completion payload
        completion_data = {
            "type": "task_completed",
            "task_id": final_state["task_id"],
            "conversation_id": conv_id,
            "response": final_state["final_response"],
            "confidence": final_state["confidence"],
            "status": final_state["status"],
            "plan": final_state["plan"],
            "completed_steps": final_state["completed_steps"],
            "requires_escalation": final_state["requires_escalation"],
            "escalation_dossier": final_state.get("escalation_dossier")
        }
        yield f"data: {json.dumps(completion_data)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
