import json
import uuid
import datetime
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session

from ..database.models import (
    get_utc_now,
    Customer,
    Order,
    SupportCase,
    CaseEvent,
    AuditLog
)
from ..schemas.case import (
    CaseStatus,
    CasePriority,
    CaseCreate,
    CaseUpdate,
    CaseMessageCreate,
    MessageDirection,
    SenderType,
    EventType
)
from ..schemas.omnichannel import (
    BusinessEventType,
    BusinessEventPayload,
    ProactiveImpactResult,
    ChannelType
)
from .case_service import CaseService
from .customer_intelligence_service import customer_intelligence_service
from .omnichannel_service import omnichannel_service


class ProactiveSupportService:
    """
    Proactive Support Engine.
    Detects customer-impacting operational events, evaluates impact via Customer 360,
    autonomously provisions SupportCases, initiates policy checks, and delivers proactive outreach.
    """

    def __init__(self):
        self._event_history: List[Dict[str, Any]] = []

    def evaluate_business_event(
        self,
        db: Session,
        event: BusinessEventPayload
    ) -> ProactiveImpactResult:
        """
        Full proactive loop:
        Business Event -> Event Monitor -> Impact Detection -> Case Creation -> Investigation -> Decision -> Proactive Communication
        """
        now = get_utc_now()
        customer = db.query(Customer).filter(Customer.customer_id == event.customer_id).first()
        if not customer:
            # Fallback customer creation if needed
            customer = Customer(
                customer_id=event.customer_id,
                organization_id="ORG-NOVACART",
                name=f"Customer {event.customer_id}",
                email=f"{event.customer_id.lower()}@customer.novacart.com",
                tier="Standard",
                account_status="Active",
                created_at=now
            )
            db.add(customer)
            db.commit()

        # Customer 360 lookup for tier, lifetime value, and sentiment
        c360 = customer_intelligence_service.get_customer_360(db, customer.customer_id)
        is_vip = (customer.tier or "").lower() in ["gold", "platinum", "vip"]
        
        # 1. Impact Detection & Decision Logic by Event Type
        impact_level = "medium"
        action_taken = "proactive_outreach"
        compensation_granted = None
        outreach_message = ""
        subject = f"[Proactive Notice] Event: {event.event_type.value.replace('_', ' ').title()}"
        priority = CasePriority.MEDIUM.value

        if event.event_type == BusinessEventType.SHIPMENT_DELAY:
            order_id = event.order_id or event.details.get("order_id", "ORD-UNKNOWN")
            carrier = event.details.get("carrier", "Carrier")
            delay_days = event.details.get("delay_days", 2)
            impact_level = "high" if (delay_days >= 3 or is_vip) else "medium"
            priority = CasePriority.HIGH.value if impact_level == "high" else CasePriority.MEDIUM.value

            compensation_val = "$15 NovaCredit" if is_vip else "$10 NovaCredit"
            compensation_granted = f"{compensation_val} applied for shipping delay"
            subject = f"[Proactive Update] Delivery Delay Notice for Order #{order_id}"
            outreach_message = (
                f"Hello {customer.name},\n\nWe noticed that your package for Order #{order_id} has experienced a brief transit delay "
                f"with {carrier} ({delay_days} days). We apologize for the inconvenience. As a courtesy, we have automatically applied "
                f"{compensation_val} to your NovaCart account. We are monitoring your delivery closely."
            )

        elif event.event_type == BusinessEventType.PAYMENT_FAILURE:
            amount = event.details.get("amount", 0.0)
            reason = event.details.get("decline_reason", "Card expired or insufficient funds")
            impact_level = "high"
            priority = CasePriority.HIGH.value
            subject = "[Action Required] Notice Regarding Your Recent Payment"
            outreach_message = (
                f"Hello {customer.name},\n\nWe attempted to process your payment of ${amount:.2f}, but the transaction could not be completed "
                f"({reason}). To prevent any disruption to your order or service, please update your billing details in your NovaCart account."
            )

        elif event.event_type == BusinessEventType.REPEATED_FAILED_DELIVERY:
            attempts = event.details.get("attempts", 2)
            order_id = event.order_id or "ORD-UNKNOWN"
            impact_level = "high"
            priority = CasePriority.URGENT.value if is_vip else CasePriority.HIGH.value
            subject = f"[Delivery Assistance] Carrier unable to reach your address for Order #{order_id}"
            outreach_message = (
                f"Hello {customer.name},\n\nOur carrier reported {attempts} unsuccessful delivery attempts for Order #{order_id}. "
                f"Please reply with any special gate codes or delivery instructions, or choose a nearby pickup locker to receive your package."
            )

        elif event.event_type == BusinessEventType.PRODUCT_ISSUE:
            product_name = event.details.get("product_name", "Item")
            issue_desc = event.details.get("issue_description", "Manufacturer quality advisory")
            impact_level = "severe" if event.severity in ["high", "critical"] else "high"
            priority = CasePriority.URGENT.value
            subject = f"[Important Advisory] Quality Notice Regarding {product_name}"
            outreach_message = (
                f"Hello {customer.name},\n\nNovaCart Quality Assurance has issued an advisory for {product_name} ({issue_desc}). "
                f"We are offering an immediate complimentary replacement or a full refund to your original payment method."
            )

        elif event.event_type == BusinessEventType.ABNORMAL_SUPPORT_ACTIVITY:
            recent_count = event.details.get("case_count", 3)
            impact_level = "high"
            priority = CasePriority.HIGH.value
            subject = f"[Customer Care] Escalated Support Review for {customer.name}"
            outreach_message = (
                f"Hello {customer.name},\n\nOur Senior Care Team noticed you've had {recent_count} recent inquiries with us. "
                f"A dedicated senior specialist has been assigned to ensure all your issues are resolved swiftly."
            )

        elif event.event_type == BusinessEventType.SLA_RISK:
            target_case_id = event.details.get("case_id", "CASE-UNKNOWN")
            impact_level = "high"
            priority = CasePriority.URGENT.value
            subject = f"[SLA Warning] Priority Attention for Case {target_case_id}"
            outreach_message = (
                f"Notice: Case {target_case_id} has entered elevated priority monitoring to ensure swift resolution within our SLA commitment."
            )

        # 2. Autonomous Case Provisioning
        case_create = CaseCreate(
            customer_id=customer.customer_id,
            subject=subject,
            description=f"Proactive event {event.event_type.value} detected by {event.source_system}. Details: {json.dumps(event.details)}",
            channel=ChannelType.API.value,
            priority=priority,
            intent=f"proactive_{event.event_type.value}",
            conversation_id=f"proactive-{event.event_id}"
        )
        proactive_case = CaseService.create_case(db, case_create)

        # 3. Record Telemetry Event & Audit Log
        CaseService.record_case_event(
            db=db,
            case_id=proactive_case.id,
            event_type=EventType.CASE_CREATED.value,
            actor="ProactiveSupportEngine",
            summary=f"Autonomous proactive case opened for {event.event_type.value}",
            details={"event_id": event.event_id, "severity": event.severity, "impact": impact_level}
        )

        # 4. Proactive Customer Communication via Preferred Channel (Email or WhatsApp or WebChat)
        preferred_channel = ChannelType.EMAIL.value
        recipient = customer.email
        if customer.phone and ("whatsapp" in (customer.tier or "").lower() or event.event_type == BusinessEventType.REPEATED_FAILED_DELIVERY):
            preferred_channel = ChannelType.WHATSAPP.value
            recipient = customer.phone

        omnichannel_service.dispatch_outbound(
            db=db,
            case_id=proactive_case.id,
            channel=preferred_channel,
            recipient=recipient,
            body=outreach_message,
            metadata={"proactive_event_id": event.event_id, "subject": subject}
        )

        result = ProactiveImpactResult(
            event_id=event.event_id,
            event_type=event.event_type.value,
            customer_id=customer.customer_id,
            impact_level=impact_level,
            case_created=True,
            case_id=proactive_case.id,
            action_taken=action_taken,
            outreach_channel=preferred_channel,
            outreach_message=outreach_message,
            compensation_granted=compensation_granted,
            reasoning=f"Proactive monitoring evaluated {event.event_type.value} as {impact_level} impact. Case {proactive_case.id} created and outreach sent via {preferred_channel}."
        )

        self._event_history.append(result.model_dump())
        return result

    def get_event_history(self) -> List[Dict[str, Any]]:
        return list(self._event_history)


proactive_support_service = ProactiveSupportService()
