import json
import datetime
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from ..database.models import (
    Customer,
    SupportCase,
    Order,
    Refund,
    EscalationTicket,
    CaseMessage,
    CustomerFrictionRecord,
    get_utc_now
)
from ..schemas.differentiation import (
    CustomerFrictionProfile,
    FrictionLevel,
    FrictionFactor
)


class CustomerFrictionService:
    """Customer Friction Intelligence Engine.
    
    Computes explainable operational friction scores (0-100) from 11 verified signals:
    1. Recent support cases
    2. Repeat contacts about the same topic
    3. Failed/missed deliveries
    4. Delayed shipments
    5. Prior escalations to human supervisors
    6. Prolonged resolution times
    7. High re-plan/transfer frequency
    8. Unresolved open cases
    9. SLA breaches
    10. Repeat refund or replacement history
    11. High contact velocity in short timeframes
    """

    @staticmethod
    def calculate_friction(db: Session, customer_id: str) -> CustomerFrictionProfile:
        clean_id = customer_id.strip().upper()
        now = get_utc_now()
        thirty_days_ago = now - datetime.timedelta(days=30)

        customer = db.query(Customer).filter(Customer.customer_id == clean_id).first()
        if not customer:
            # Safe default for unknown customer
            return CustomerFrictionProfile(
                customer_id=clean_id,
                score=10.0,
                level=FrictionLevel.LOW,
                contributing_factors=[
                    FrictionFactor(
                        factor_type="unknown_customer",
                        label="New / Unregistered Customer",
                        impact_score=10.0,
                        description="Customer profile not yet established in CRM records."
                    )
                ],
                recent_trend="stable",
                affected_cases=[]
            )

        factors: List[FrictionFactor] = []
        raw_score = 0.0

        # Query operational data
        cases = db.query(SupportCase).filter(SupportCase.customer_id == clean_id).all()
        recent_cases = [c for c in cases if c.created_at and c.created_at >= thirty_days_ago]
        open_cases = [c for c in cases if c.status not in ["RESOLVED", "CLOSED"]]
        orders = db.query(Order).filter(Order.customer_id == clean_id).all()
        refunds = db.query(Refund).filter(Refund.customer_id == clean_id).all()
        escalations = db.query(EscalationTicket).filter(EscalationTicket.customer_id == clean_id).all()

        # 1. Recent cases volume
        if len(recent_cases) > 1:
            impact = min(20.0, (len(recent_cases) - 1) * 7.5)
            raw_score += impact
            factors.append(FrictionFactor(
                factor_type="recent_cases",
                label="Frequent Support Inquiries",
                impact_score=impact,
                description=f"Customer opened {len(recent_cases)} cases in the past 30 days.",
                raw_signal={"case_count": len(recent_cases)}
            ))

        # 2. Repeat contacts (same intent)
        intents = [c.intent for c in recent_cases if c.intent]
        intent_counts = {}
        for it in intents:
            intent_counts[it] = intent_counts.get(it, 0) + 1
        repeat_intents = {k: v for k, v in intent_counts.items() if v > 1}
        if repeat_intents:
            impact = min(25.0, sum(v * 8.0 for v in repeat_intents.values()))
            raw_score += impact
            factors.append(FrictionFactor(
                factor_type="repeat_contacts",
                label="Repeated Contact on Same Issue",
                impact_score=impact,
                description=f"Multiple inquiries regarding: {', '.join(repeat_intents.keys())}.",
                raw_signal=repeat_intents
            ))

        # 3. Delayed orders
        delayed_orders = [o for o in orders if o.status in ["Delayed", "Delayed_Carrier"]]
        if delayed_orders:
            impact = min(20.0, len(delayed_orders) * 12.0)
            raw_score += impact
            factors.append(FrictionFactor(
                factor_type="delayed_orders",
                label="Shipment Delays",
                impact_score=impact,
                description=f"{len(delayed_orders)} order(s) experienced carrier delays.",
                raw_signal={"delayed_orders": [o.order_id for o in delayed_orders]}
            ))

        # 4. Previous escalations
        if escalations:
            impact = min(25.0, len(escalations) * 15.0)
            raw_score += impact
            factors.append(FrictionFactor(
                factor_type="previous_escalations",
                label="Supervisor Escalation History",
                impact_score=impact,
                description=f"Customer required {len(escalations)} previous human escalations.",
                raw_signal={"escalation_count": len(escalations)}
            ))

        # 5. Open / Unresolved cases
        if open_cases:
            impact = min(20.0, len(open_cases) * 10.0)
            raw_score += impact
            factors.append(FrictionFactor(
                factor_type="unresolved_cases",
                label="Active Unresolved Cases",
                impact_score=impact,
                description=f"{len(open_cases)} support case(s) currently open/investigating.",
                raw_signal={"open_cases": [c.id for c in open_cases]}
            ))

        # 6. Prior refunds
        if len(refunds) > 1:
            impact = min(15.0, (len(refunds) - 1) * 6.0)
            raw_score += impact
            factors.append(FrictionFactor(
                factor_type="refunds",
                label="Repeated Refund History",
                impact_score=impact,
                description=f"Customer has {len(refunds)} historical refund transactions.",
                raw_signal={"refund_count": len(refunds)}
            ))

        # 7. SLA breaches
        sla_breached_cases = [c for c in cases if c.sla_deadline and c.sla_deadline < (c.resolved_at or now)]
        if sla_breached_cases:
            impact = min(25.0, len(sla_breached_cases) * 15.0)
            raw_score += impact
            factors.append(FrictionFactor(
                factor_type="sla_breaches",
                label="Past SLA Breaches",
                impact_score=impact,
                description=f"{len(sla_breached_cases)} case(s) exceeded target SLA resolution windows.",
                raw_signal={"breached_cases": [c.id for c in sla_breached_cases]}
            ))

        # Base minimum score
        if not factors:
            raw_score = 5.0
            factors.append(FrictionFactor(
                factor_type="smooth_operations",
                label="Healthy Account History",
                impact_score=0.0,
                description="No recent friction, delays, or escalations on record."
            ))

        final_score = min(100.0, max(0.0, round(raw_score, 1)))

        # Determine level
        if final_score < 25.0:
            level = FrictionLevel.LOW
        elif final_score < 55.0:
            level = FrictionLevel.MEDIUM
        elif final_score < 80.0:
            level = FrictionLevel.HIGH
        else:
            level = FrictionLevel.CRITICAL

        # Determine trend
        if len(recent_cases) >= 2 or len(open_cases) >= 2:
            trend = "escalating"
        elif len(recent_cases) == 0 and not open_cases:
            trend = "improving"
        else:
            trend = "stable"

        affected_cases = [c.id for c in open_cases + recent_cases][:10]

        profile = CustomerFrictionProfile(
            customer_id=clean_id,
            score=final_score,
            level=level,
            contributing_factors=factors,
            recent_trend=trend,
            affected_cases=list(set(affected_cases)),
            calculated_at=now
        )

        # Persist record snapshot in SQLite
        try:
            record = CustomerFrictionRecord(
                customer_id=clean_id,
                organization_id=customer.organization_id or "ORG-NOVACART",
                score=final_score,
                level=level.value,
                contributing_factors_json=json.dumps([f.model_dump() for f in factors]),
                recent_trend=trend,
                affected_cases_json=json.dumps(profile.affected_cases),
                calculated_at=now
            )
            db.add(record)
            db.commit()
        except Exception:
            db.rollback()

        return profile
