from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from ..memory.manager import memory_manager

router = APIRouter(prefix="/api/memory", tags=["memory"])

class MemoryCreateRequest(BaseModel):
    key: str
    value: str
    memory_type: str = "preference"

@router.get("/{customer_id}")
def get_customer_memory(customer_id: str):
    ctx = memory_manager.get_customer_context(customer_id)
    if not ctx.get("found"):
        raise HTTPException(status_code=404, detail="Customer not found")
    return ctx

@router.post("/{customer_id}")
def save_memory_note(customer_id: str, req: MemoryCreateRequest):
    memory_manager.save_memory(
        customer_id=customer_id,
        key=req.key,
        value=req.value,
        memory_type=req.memory_type
    )
    return {"success": True, "message": f"Memory '{req.key}' persisted for {customer_id}"}
