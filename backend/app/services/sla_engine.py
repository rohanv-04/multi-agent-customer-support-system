import json
import uuid
import datetime
from typing import Dict, Any, Optional, List, Tuple
from sqlalchemy.orm import Session

from ..database.models import (
    get_utc_now,
    Customer,
    SupportCase,
    CaseEvent,
    EscalationTicket,
    AuditLog
)
from ..schemas.case import (
    CaseStatus,
    CasePriority,
    EventType
)
from ..schemas.omnichannel import (
    SLABreachStatus,
    SLAPolicyConfig,
    SLACheckResult
)
from .case_service import CaseService


DEFAULT_SLA_POLICIES: Dict[str, SLAPolicyConfig] = {
    CasePriority.URGENT.value: SLAPolicyConfig(
        priority=CasePriority.URGENT.value,
        standard_target_hours=1.0,
        vip_target_hours=0.5,
        warning_threshold_ratio=0.20
    ),
    CasePriority.HIGH.value: SLAPolicyConfig(
        priority=CasePriority.HIGH.value,
        standard_target_hours=4.0,
        vip_target_hours=2.0,
        warning_threshold_ratio=0.20
    ),
    CasePriority.MEDIUM.value: SLAPolicyConfig(
        priority=CasePriority.MEDIUM.value,
        standard_target_hours=12.0,
        vip_target_hours=6.0,
        warning_threshold_ratio=0.20
    ),
    CasePriority.LOW.value: SLAPolicyConfig(
        priority=CasePriority.LOW.value,
        standard_target_hours=24.0,
        vip_target_hours=12.0,
        warning_threshold_ratio=0.20
    ),
}


class SLAEngine:
    """
    SLA Calculation, Monitoring, Breach Detection, and Escalation Engine.
    """

    def __init__(self, policies: Optional[Dict[str, SLAPolicyConfig]] = None):
        self.policies = policies or DEFAULT_SLA_POLICIES
        self._approaching_warnings_sent: set = set()

    def calculate_deadline(
        self,
        priority: str,
        customer_tier: Optional[str] = "Standard",
        start_time: Optional[datetime.datetime] = None
    ) -> datetime.datetime:
        """Calculates exact SLA resolution deadline based on priority and customer tier."""
        now = start_time or get_utc_now()
        pri_key = (priority or "medium").lower()
        policy = self.policies.get(pri_key, self.policies[CasePriority.MEDIUM.value])

        tier = (customer_tier or "").lower()
        is_vip = tier in ["gold", "platinum", "vip"]
        hours = policy.vip_target_hours if is_vip else policy.standard_target_hours

        return now + datetime.timedelta(hours=hours)

    def evaluate_case_sla(
        self,
        db: Session,
        case: SupportCase,
        auto_escalate: bool = True
    ) -> SLACheckResult:
        """
        Evaluates remaining time, breach status, and triggers escalation / supervisor alerts when necessary.
        """
        now = get_utc_now()
        pri_key = (case.priority or "medium").lower()
        policy = self.policies.get(pri_key, self.policies[CasePriority.MEDIUM.value])
        
        customer = db.query(Customer).filter(Customer.customer_id == case.customer_id).first()
        customer_tier = customer.tier if customer else "Standard"

        # Calculate deadline if missing
        if not case.sla_deadline:
            case.sla_deadline = self.calculate_deadline(case.priority, customer_tier, case.created_at)
            db.commit()

        # If already resolved or closed, evaluate at resolution timestamp
        eval_time = case.resolved_at if (case.resolved_at and case.status in [CaseStatus.RESOLVED.value, CaseStatus.CLOSED.value]) else now
        remaining_seconds = (case.sla_deadline - eval_time).total_seconds()
        remaining_minutes = remaining_seconds / 60.0

        # Total window in seconds
        tier_lower = (customer_tier or "").lower()
        is_vip = tier_lower in ["gold", "platinum", "vip"]
        total_hours = policy.vip_target_hours if is_vip else policy.standard_target_hours
        total_window_seconds = total_hours * 3600.0
        warning_threshold_seconds = max(total_window_seconds * policy.warning_threshold_ratio, 900.0)  # at least 15 min

        # Status determination
        is_breached = remaining_seconds <= 0
        is_approaching = (not is_breached) and (remaining_seconds <= warning_threshold_seconds)

        if is_breached:
            breach_status = SLABreachStatus.BREACHED
        elif is_approaching:
            breach_status = SLABreachStatus.APPROACHING_BREACH
        else:
            breach_status = SLABreachStatus.OK

        auto_escalated = False
        escalation_reason = None

        # Process Approaching Breach Alert
        if is_approaching and case.id not in self._approaching_warnings_sent:
            self._approaching_warnings_sent.add(case.id)
            CaseService.record_case_event(
                db=db,
                case_id=case.id,
                event_type=EventType.STATUS_CHANGED.value,
                actor="SLAEngine",
                summary=f"SLA Warning: Case is approaching deadline. Remaining time: {remaining_minutes:.1f} minutes",
                details={
                    "remaining_minutes": remaining_minutes,
                    "deadline": case.sla_deadline.isoformat(),
                    "supervisor_alert": "HIGH_PRIORITY_BREACH_RISK"
                }
            )

        # Process Breach & Auto-Escalation
        if is_breached and case.status not in [CaseStatus.RESOLVED.value, CaseStatus.CLOSED.value, CaseStatus.ESCALATED.value]:
            if auto_escalate:
                auto_escalated = True
                escalation_reason = f"Automated SLA Escalation: Case {case.id} breached its SLA deadline ({case.sla_deadline.isoformat()})."
                self._execute_auto_escalation(db, case, escalation_reason)

        return SLACheckResult(
            case_id=case.id,
            priority=case.priority,
            customer_tier=customer_tier,
            sla_deadline=case.sla_deadline,
            remaining_minutes=remaining_minutes,
            breach_status=breach_status,
            is_breached=is_breached,
            is_approaching_breach=is_approaching,
            auto_escalated=auto_escalated,
            escalation_reason=escalation_reason
        )

    def _execute_auto_escalation(self, db: Session, case: SupportCase, reason: str):
        """Creates an EscalationTicket and updates case state to ESCALATED with audit records."""
        now = get_utc_now()
        ticket_id = f"ESC-{uuid.uuid4().hex[:8].upper()}"

        # 1. Create Escalation Ticket
        escalation = EscalationTicket(
            ticket_id=ticket_id,
            case_id=case.id,
            customer_id=case.customer_id,
            task_id=None,
            summary=f"SLA Breach Escalation for Case {case.id}",
            intent=case.intent or "sla_breach_recovery",
            reason=reason,
            status="open",
            priority=CasePriority.URGENT.value,
            recommended_action="Expedite immediate human supervisor review and customer outreach",
            assigned_to="Supervisor Queue",
            created_at=now
        )
        db.add(escalation)

        # 2. Update Case Status
        case.status = CaseStatus.ESCALATED.value
        case.updated_at = now

        # 3. Telemetry Event & Audit Log
        CaseService.record_case_event(
            db=db,
            case_id=case.id,
            event_type=EventType.ESCALATION.value,
            actor="SLAEngine",
            summary=f"Case auto-escalated due to SLA breach. Escalation Ticket #{ticket_id}",
            details={"escalation_ticket_id": ticket_id, "reason": reason}
        )

        audit = AuditLog(
            case_id=case.id,
            entity_type="SupportCase",
            entity_id=case.id,
            action="SLA_BREACH_AUTO_ESCALATED",
            actor_type="system",
            actor_id="SLAEngine",
            details_json=json.dumps({"escalation_ticket_id": ticket_id, "reason": reason}),
            created_at=now
        )
        db.add(audit)
        db.commit()

    def evaluate_all_active_cases(self, db: Session) -> Dict[str, Any]:
        """Evaluates all non-resolved, non-closed cases in the system."""
        active_cases = db.query(SupportCase).filter(
            SupportCase.status.notin_([CaseStatus.RESOLVED.value, CaseStatus.CLOSED.value])
        ).all()

        results = []
        ok_count = 0
        approaching_count = 0
        breached_count = 0
        escalated_count = 0

        for c in active_cases:
            res = self.evaluate_case_sla(db, c, auto_escalate=True)
            results.append(res.model_dump())
            if res.breach_status == SLABreachStatus.BREACHED:
                breached_count += 1
            elif res.breach_status == SLABreachStatus.APPROACHING_BREACH:
                approaching_count += 1
            else:
                ok_count += 1

            if res.auto_escalated:
                escalated_count += 1

        return {
            "total_active_cases": len(active_cases),
            "ok_count": ok_count,
            "approaching_breach_count": approaching_count,
            "breached_count": breached_count,
            "auto_escalated_count": escalated_count,
            "timestamp": get_utc_now().isoformat(),
            "evaluations": results
        }


sla_engine = SLAEngine()
