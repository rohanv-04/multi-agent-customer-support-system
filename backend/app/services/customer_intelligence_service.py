import json
import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import desc

from ..database.models import (
    Customer,
    Order,
    Refund,
    SupportCase,
    EscalationTicket,
    CustomerMemory,
    get_utc_now
)
from ..schemas.customer import (
    CustomerProfileSchema,
    CustomerLoyaltySchema,
    CustomerOrderItemSchema,
    CustomerOrderSummarySchema,
    CustomerPaymentSummarySchema,
    CustomerRefundSummarySchema,
    CustomerCaseSummarySchema,
    CustomerComplaintSummarySchema,
    CustomerResolutionSummarySchema,
    CustomerEscalationSummarySchema,
    CustomerMemoryItemSchema,
    CustomerActivityItemSchema,
    Customer360Response
)


class CustomerIntelligenceService:
    @staticmethod
    def get_tier_perks(tier: str) -> List[str]:
        tier_upper = (tier or "Standard").upper()
        if tier_upper == "PLATINUM":
            return [
                "VIP Concierge Handoff Priority",
                "Instant Refund Authorization (< $500)",
                "Zero-Restocking Fee Guarantee",
                "Dedicated Account Resolution Specialist"
            ]
        elif tier_upper == "GOLD":
            return [
                "Priority Routing in Agent Queue",
                "Extended 30-Day Return Window",
                "Free Express Replacements"
            ]
        elif tier_upper == "SILVER":
            return [
                "Standard Priority Dispatch",
                "14-Day Return Window",
                "Email Notification Receipts"
            ]
        else:
            return [
                "Standard Support Queue",
                "Self-Service Knowledge Base Access"
            ]

    @classmethod
    def get_customer_360(cls, db: Session, customer_id: str) -> Optional[Customer360Response]:
        customer = db.query(Customer).filter(Customer.customer_id == customer_id).first()
        if not customer:
            return None

        now = get_utc_now()

        # 1. Orders & Payments
        raw_orders = db.query(Order).filter(Order.customer_id == customer_id).order_by(desc(Order.order_date)).all()
        orders: List[CustomerOrderSummarySchema] = []
        payments: List[CustomerPaymentSummarySchema] = []
        lifetime_spend = 0.0

        for o in raw_orders:
            items_list = []
            try:
                raw_items = json.loads(o.items_json) if o.items_json else []
                for item in raw_items:
                    items_list.append(CustomerOrderItemSchema(
                        item_id=item.get("item_id", "ITM-UNKNOWN"),
                        name=item.get("name", "Product Item"),
                        qty=int(item.get("qty", 1)),
                        price=float(item.get("price", 0.0))
                    ))
            except Exception:
                items_list = []

            if o.status not in ["Cancelled"]:
                lifetime_spend += float(o.total_amount)

            orders.append(CustomerOrderSummarySchema(
                order_id=o.order_id,
                status=o.status,
                total_amount=o.total_amount,
                currency=o.currency or "USD",
                carrier=o.carrier,
                tracking_number=o.tracking_number,
                order_date=o.order_date,
                expected_delivery=o.expected_delivery,
                actual_delivery=o.actual_delivery,
                delay_reason=o.delay_reason,
                items=items_list
            ))

            payment_status = "refunded" if o.status == "Refunded" else "paid" if o.status != "Cancelled" else "voided"
            payments.append(CustomerPaymentSummarySchema(
                payment_id=f"PAY-{o.order_id}",
                order_id=o.order_id,
                amount=o.total_amount,
                currency=o.currency or "USD",
                status=payment_status,
                payment_method="Primary Card (Ending in 4242)",
                created_at=o.order_date
            ))

        # 2. Refunds
        raw_refunds = db.query(Refund).filter(Refund.customer_id == customer_id).order_by(desc(Refund.processed_at)).all()
        refunds: List[CustomerRefundSummarySchema] = []
        total_refunded = 0.0
        for r in raw_refunds:
            total_refunded += float(r.refund_amount)
            refunds.append(CustomerRefundSummarySchema(
                refund_id=r.refund_id,
                order_id=r.order_id,
                refund_amount=r.refund_amount,
                currency=r.currency or "USD",
                status=r.status,
                reason=r.reason,
                refund_method=r.refund_method,
                processed_at=r.processed_at
            ))

        # 3. Support Cases
        raw_cases = db.query(SupportCase).filter(SupportCase.customer_id == customer_id).order_by(desc(SupportCase.created_at)).all()
        cases: List[CustomerCaseSummarySchema] = []
        open_cases_count = 0
        previous_resolutions: List[CustomerResolutionSummarySchema] = []

        for c in raw_cases:
            if c.status not in ["RESOLVED", "CLOSED"]:
                open_cases_count += 1
            else:
                previous_resolutions.append(CustomerResolutionSummarySchema(
                    resolution_id=f"RES-{c.id}",
                    case_id=c.id,
                    resolution_type="case_resolved",
                    outcome_summary=f"Case resolved with intent {c.intent or 'support'}",
                    resolved_at=c.resolved_at or c.updated_at
                ))

            cases.append(CustomerCaseSummarySchema(
                id=c.id,
                channel=c.channel,
                subject=c.subject,
                priority=c.priority,
                status=c.status,
                intent=c.intent,
                sentiment=c.sentiment,
                created_at=c.created_at,
                resolved_at=c.resolved_at
            ))

        # Add refund resolutions
        for r in refunds:
            previous_resolutions.append(CustomerResolutionSummarySchema(
                resolution_id=f"RES-REF-{r.refund_id}",
                order_id=r.order_id,
                resolution_type="refund_issued",
                outcome_summary=f"Automated refund of ${r.refund_amount:.2f} {r.currency} credited via {r.refund_method}",
                resolved_at=r.processed_at
            ))

        # 4. Escalations & Complaints
        raw_escalations = db.query(EscalationTicket).filter(EscalationTicket.customer_id == customer_id).order_by(desc(EscalationTicket.created_at)).all()
        escalations: List[CustomerEscalationSummarySchema] = []
        previous_complaints: List[CustomerComplaintSummarySchema] = []

        for e in raw_escalations:
            escalations.append(CustomerEscalationSummarySchema(
                ticket_id=e.ticket_id,
                case_id=e.case_id,
                summary=e.summary,
                reason=e.reason,
                status=e.status,
                priority=e.priority,
                assigned_to=e.assigned_to or "Unassigned",
                created_at=e.created_at
            ))
            previous_complaints.append(CustomerComplaintSummarySchema(
                complaint_id=f"CMP-{e.ticket_id}",
                source_type="escalation",
                severity=e.priority,
                issue=e.reason,
                status=e.status,
                created_at=e.created_at
            ))

        for c in cases:
            if c.sentiment in ["negative", "frustrated"] or c.priority in ["high", "urgent"]:
                previous_complaints.append(CustomerComplaintSummarySchema(
                    complaint_id=f"CMP-CASE-{c.id}",
                    source_type="support_case",
                    severity=c.priority,
                    issue=c.subject,
                    status=c.status,
                    created_at=c.created_at
                ))

        # 5. Persistent Memories
        raw_memories = db.query(CustomerMemory).filter(CustomerMemory.customer_id == customer_id).order_by(desc(CustomerMemory.updated_at)).all()
        memories: List[CustomerMemoryItemSchema] = []
        for m in raw_memories:
            memories.append(CustomerMemoryItemSchema(
                id=m.id,
                memory_type=m.memory_type,
                key=m.key,
                value=m.value,
                updated_at=m.updated_at
            ))

        # 6. Loyalty Calculation
        tenure_days = max(1, (now - customer.created_at).days)
        is_vip = customer.tier.upper() in ["PLATINUM", "GOLD"] or lifetime_spend >= 1000.0

        loyalty = CustomerLoyaltySchema(
            tier=customer.tier,
            is_vip=is_vip,
            lifetime_spend=round(lifetime_spend, 2),
            currency="USD",
            order_count=len(orders),
            tenure_days=tenure_days,
            perks=cls.get_tier_perks(customer.tier)
        )

        # 7. Risk Assessment
        churn_signals = []
        delayed_orders = [o for o in orders if o.status == "Delayed"]
        if delayed_orders:
            for d in delayed_orders:
                churn_signals.append(f"Shipment {d.tracking_number or d.order_id} is overdue: {d.delay_reason or 'Delayed in transit'}")

        if escalations:
            open_esc = [e for e in escalations if e.status == "open"]
            if open_esc:
                churn_signals.append(f"{len(open_esc)} open escalation tickets awaiting human action.")

        if total_refunded > 0:
            churn_signals.append(f"Past refunds claimed: ${total_refunded:.2f} USD.")

        if len(delayed_orders) >= 2 or len(escalations) >= 2:
            risk_level = "HIGH"
        elif len(delayed_orders) == 1 or len(escalations) == 1:
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"

        risk_assessment = {
            "risk_level": risk_level,
            "churn_signals": churn_signals,
            "total_refunded_amount": round(total_refunded, 2),
            "loyalty_score": 95 if is_vip else 70,
            "recommended_treatment": "Prioritize autonomous resolution and waive return fees" if is_vip else "Standard SLA procedures"
        }

        profile = CustomerProfileSchema(
            customer_id=customer.customer_id,
            organization_id=customer.organization_id or "ORG-NOVACART",
            name=customer.name,
            email=customer.email,
            phone=customer.phone,
            account_status=customer.account_status,
            created_at=customer.created_at
        )

        return Customer360Response(
            profile=profile,
            account_status=customer.account_status,
            loyalty=loyalty,
            orders=orders,
            payments=payments,
            refunds=refunds,
            previous_cases=cases,
            cases=cases,
            previous_complaints=previous_complaints,
            previous_resolutions=previous_resolutions,
            escalations=escalations,
            memories=memories,
            open_cases_count=open_cases_count,
            risk_assessment=risk_assessment
        )

    @classmethod
    def get_customer_orders(cls, db: Session, customer_id: str) -> List[CustomerOrderSummarySchema]:
        c360 = cls.get_customer_360(db, customer_id)
        return c360.orders if c360 else []

    @classmethod
    def get_customer_cases(cls, db: Session, customer_id: str) -> List[CustomerCaseSummarySchema]:
        c360 = cls.get_customer_360(db, customer_id)
        return c360.cases if c360 else []

    @classmethod
    def get_customer_activity(cls, db: Session, customer_id: str) -> List[CustomerActivityItemSchema]:
        c360 = cls.get_customer_360(db, customer_id)
        if not c360:
            return []

        activities: List[CustomerActivityItemSchema] = []

        # Orders
        for o in c360.orders:
            activities.append(CustomerActivityItemSchema(
                id=f"act-ord-{o.order_id}",
                activity_type="order",
                timestamp=o.order_date,
                title=f"Order Placed: {o.order_id}",
                description=f"Status: {o.status} | Total: ${o.total_amount:.2f} {o.currency} | Carrier: {o.carrier or 'Pending'}",
                badge=o.status,
                status="success" if o.status in ["Delivered", "Shipped"] else "warning" if o.status == "Delayed" else "neutral",
                metadata={"items_count": len(o.items), "tracking": o.tracking_number}
            ))

        # Payments
        for p in c360.payments:
            activities.append(CustomerActivityItemSchema(
                id=f"act-pay-{p.payment_id}",
                activity_type="payment",
                timestamp=p.created_at,
                title=f"Payment Processed: {p.payment_id}",
                description=f"Amount: ${p.amount:.2f} {p.currency} | Status: {p.status.upper()}",
                badge=p.status,
                status="success" if p.status == "paid" else "neutral",
                metadata={"order_id": p.order_id, "method": p.payment_method}
            ))

        # Refunds
        for r in c360.refunds:
            activities.append(CustomerActivityItemSchema(
                id=f"act-ref-{r.refund_id}",
                activity_type="refund",
                timestamp=r.processed_at,
                title=f"Refund Credited: #{r.refund_id}",
                description=f"Amount: ${r.refund_amount:.2f} {r.currency} | Reason: {r.reason}",
                badge="Refund",
                status="success",
                metadata={"order_id": r.order_id, "method": r.refund_method}
            ))

        # Cases
        for c in c360.cases:
            activities.append(CustomerActivityItemSchema(
                id=f"act-case-{c.id}",
                activity_type="case",
                timestamp=c.created_at,
                title=f"Support Case: {c.id}",
                description=c.subject,
                badge=c.status,
                status="info" if c.status not in ["ESCALATED"] else "urgent",
                metadata={"priority": c.priority, "channel": c.channel}
            ))

        # Escalations
        for e in c360.escalations:
            activities.append(CustomerActivityItemSchema(
                id=f"act-esc-{e.ticket_id}",
                activity_type="escalation",
                timestamp=e.created_at,
                title=f"Human Escalation: #{e.ticket_id}",
                description=e.reason,
                badge=e.priority,
                status="urgent",
                metadata={"assigned_to": e.assigned_to}
            ))

        # Memories
        for m in c360.memories:
            activities.append(CustomerActivityItemSchema(
                id=f"act-mem-{m.id}",
                activity_type="memory",
                timestamp=m.updated_at,
                title=f"Customer Preference: {m.key.replace('_', ' ').title()}",
                description=m.value,
                badge=m.memory_type,
                status="neutral"
            ))

        activities.sort(key=lambda x: x.timestamp, reverse=True)
        return activities


customer_intelligence_service = CustomerIntelligenceService()
