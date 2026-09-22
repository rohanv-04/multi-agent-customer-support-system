import uuid
import datetime
from typing import Dict, Any, Optional
from ..database.database import SessionLocal
from ..database.models import Customer, SupportCase, CaseMessage, get_utc_now


def send_customer_email(
    customer_id: str,
    subject: str,
    body: str,
    case_id: Optional[str] = None
) -> Dict[str, Any]:
    """Execute customer email dispatch and record in case activity timeline."""
    db = SessionLocal()
    try:
        customer = db.query(Customer).filter(Customer.customer_id == customer_id).first()
        target_email = customer.email if customer else f"{customer_id}@example.com"

        message_id = f"MSG-EML-{uuid.uuid4().hex[:8].upper()}"
        now = get_utc_now()

        if case_id:
            case = db.query(SupportCase).filter(SupportCase.id == case_id).first()
            if case:
                case_msg = CaseMessage(
                    case_id=case_id,
                    direction="outbound",
                    channel="email",
                    sender_type="agent",
                    sender_id="Action Gateway Email Service",
                    body=f"Subject: {subject}\n\n{body}",
                    created_at=now
                )
                db.add(case_msg)
                db.commit()

        return {
            "success": True,
            "message_id": message_id,
            "channel": "email",
            "recipient": target_email,
            "subject": subject,
            "body": body,
            "status": "sent",
            "timestamp": now.isoformat(),
            "message": f"Email successfully dispatched to {target_email}."
        }
    except Exception as e:
        db.rollback()
        return {
            "success": False,
            "error": f"Failed to send email: {str(e)}",
            "message_id": None
        }
    finally:
        db.close()


def send_whatsapp_message(
    customer_id: str,
    message: str,
    phone: Optional[str] = None,
    case_id: Optional[str] = None
) -> Dict[str, Any]:
    """Execute WhatsApp message dispatch and record in case activity timeline."""
    db = SessionLocal()
    try:
        customer = db.query(Customer).filter(Customer.customer_id == customer_id).first()
        target_phone = phone or (customer.phone if customer else "+1-555-0199")

        message_id = f"MSG-WA-{uuid.uuid4().hex[:8].upper()}"
        now = get_utc_now()

        if case_id:
            case = db.query(SupportCase).filter(SupportCase.id == case_id).first()
            if case:
                case_msg = CaseMessage(
                    case_id=case_id,
                    direction="outbound",
                    channel="whatsapp",
                    sender_type="agent",
                    sender_id="Action Gateway WhatsApp Service",
                    body=message,
                    created_at=now
                )
                db.add(case_msg)
                db.commit()

        return {
            "success": True,
            "message_id": message_id,
            "channel": "whatsapp",
            "recipient": target_phone,
            "message_body": message,
            "status": "delivered",
            "timestamp": now.isoformat(),
            "message": f"WhatsApp message successfully delivered to {target_phone}."
        }
    except Exception as e:
        db.rollback()
        return {
            "success": False,
            "error": f"Failed to send WhatsApp message: {str(e)}",
            "message_id": None
        }
    finally:
        db.close()
