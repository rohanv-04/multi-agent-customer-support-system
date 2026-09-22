import datetime
from typing import Dict, Any, Optional
from ..database.database import SessionLocal
from ..database.models import SupportCase, Customer, get_utc_now


def update_support_ticket(
    case_id: str,
    priority: Optional[str] = None,
    status: Optional[str] = None,
    subject: Optional[str] = None,
    description: Optional[str] = None
) -> Dict[str, Any]:
    """Execute update on SupportCase record."""
    db = SessionLocal()
    try:
        case = db.query(SupportCase).filter(SupportCase.id == case_id).first()
        if not case:
            return {
                "success": False,
                "error": f"Support case {case_id} not found.",
                "case_id": case_id
            }

        if priority:
            case.priority = priority
        if status:
            case.status = status
        if subject:
            case.subject = subject
        if description:
            case.description = description

        case.updated_at = get_utc_now()
        db.commit()

        return {
            "success": True,
            "case_id": case.id,
            "priority": case.priority,
            "status": case.status,
            "subject": case.subject,
            "timestamp": case.updated_at.isoformat(),
            "message": f"Successfully updated support case {case.id}."
        }
    except Exception as e:
        db.rollback()
        return {
            "success": False,
            "error": f"Failed to update support case: {str(e)}",
            "case_id": case_id
        }
    finally:
        db.close()


def update_customer_profile(
    customer_id: str,
    tier: Optional[str] = None,
    phone: Optional[str] = None,
    account_status: Optional[str] = None
) -> Dict[str, Any]:
    """Execute update on Customer profile."""
    db = SessionLocal()
    try:
        cust = db.query(Customer).filter(Customer.customer_id == customer_id).first()
        if not cust:
            return {
                "success": False,
                "error": f"Customer {customer_id} not found.",
                "customer_id": customer_id
            }

        if tier:
            cust.tier = tier
        if phone:
            cust.phone = phone
        if account_status:
            cust.account_status = account_status

        db.commit()

        return {
            "success": True,
            "customer_id": cust.customer_id,
            "tier": cust.tier,
            "phone": cust.phone,
            "account_status": cust.account_status,
            "message": f"Successfully updated profile for customer {cust.customer_id}."
        }
    except Exception as e:
        db.rollback()
        return {
            "success": False,
            "error": f"Failed to update customer: {str(e)}",
            "customer_id": customer_id
        }
    finally:
        db.close()
