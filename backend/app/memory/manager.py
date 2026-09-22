import json
import datetime
from typing import Dict, Any, List, Optional
from ..database.database import SessionLocal
from ..database.models import Customer, CustomerMemory, Conversation, Message, Task, Order

class MemoryManager:
    """Persistent customer and task memory manager backed by SQLite."""

    @staticmethod
    def get_customer_context(customer_id: str) -> Dict[str, Any]:
        """Compile a rich customer context profile including memories, orders, and recent tasks."""
        db = SessionLocal()
        try:
            clean_id = customer_id.strip().upper()
            customer = db.query(Customer).filter(Customer.customer_id == clean_id).first()
            if not customer:
                return {"customer_id": clean_id, "found": False}

            # Fetch customer memories
            mem_records = db.query(CustomerMemory).filter(CustomerMemory.customer_id == clean_id).all()
            memories = [
                {"type": m.memory_type, "key": m.key, "value": m.value, "updated_at": m.updated_at.isoformat()}
                for m in mem_records
            ]

            # Fetch orders
            orders = db.query(Order).filter(Order.customer_id == clean_id).all()
            order_list = [
                {
                    "order_id": o.order_id,
                    "status": o.status,
                    "total_amount": o.total_amount,
                    "carrier": o.carrier,
                    "tracking_number": o.tracking_number,
                    "delay_reason": o.delay_reason
                }
                for o in orders
            ]

            # Fetch recent tasks
            recent_tasks = db.query(Task).filter(Task.customer_id == clean_id).order_by(Task.created_at.desc()).limit(5).all()
            task_list = [
                {
                    "task_id": t.task_id,
                    "user_goal": t.user_goal,
                    "intent": t.intent,
                    "status": t.status,
                    "confidence": t.confidence,
                    "created_at": t.created_at.isoformat()
                }
                for t in recent_tasks
            ]

            return {
                "found": True,
                "customer_id": customer.customer_id,
                "name": customer.name,
                "email": customer.email,
                "tier": customer.tier,
                "account_status": customer.account_status,
                "memories": memories,
                "orders": order_list,
                "recent_tasks": task_list
            }
        finally:
            db.close()

    @staticmethod
    def save_memory(customer_id: str, key: str, value: str, memory_type: str = "preference"):
        db = SessionLocal()
        try:
            clean_id = customer_id.strip().upper()
            mem = CustomerMemory(
                customer_id=clean_id,
                memory_type=memory_type,
                key=key,
                value=value,
                created_at=datetime.datetime.utcnow(),
                updated_at=datetime.datetime.utcnow()
            )
            db.add(mem)
            db.commit()
        except Exception as e:
            db.rollback()
            print(f"[Memory Save Error]: {e}")
        finally:
            db.close()

memory_manager = MemoryManager()
