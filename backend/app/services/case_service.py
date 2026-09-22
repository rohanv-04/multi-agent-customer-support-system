import json
import uuid
import datetime
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import desc, or_

from ..database.models import (
    get_utc_now,
    SupportCase,
    CaseMessage,
    CaseEvent,
    AgentRun,
    AgentAction,
    EscalationTicket,
    AuditLog,
    Customer,
    Organization
)
from ..schemas.case import (
    CaseStatus,
    CasePriority,
    CaseChannel,
    MessageDirection,
    SenderType,
    EventType,
    CaseCreate,
    CaseUpdate,
    CaseMessageCreate,
    TimelineItemResponse
)


ALLOWED_TRANSITIONS: Dict[str, List[str]] = {
    CaseStatus.NEW.value: [
        CaseStatus.TRIAGING.value,
        CaseStatus.INVESTIGATING.value,
        CaseStatus.DECISION_PENDING.value,
        CaseStatus.ACTION_PENDING.value,
        CaseStatus.HUMAN_REVIEW.value,
        CaseStatus.ESCALATED.value,
        CaseStatus.CLOSED.value
    ],
    CaseStatus.TRIAGING.value: [
        CaseStatus.INVESTIGATING.value,
        CaseStatus.ESCALATED.value,
        CaseStatus.CLOSED.value
    ],
    CaseStatus.INVESTIGATING.value: [
        CaseStatus.DECISION_PENDING.value,
        CaseStatus.ACTION_PENDING.value,
        CaseStatus.HUMAN_REVIEW.value,
        CaseStatus.ESCALATED.value,
        CaseStatus.CLOSED.value
    ],
    CaseStatus.DECISION_PENDING.value: [
        CaseStatus.ACTION_PENDING.value,
        CaseStatus.HUMAN_REVIEW.value,
        CaseStatus.VERIFYING.value,
        CaseStatus.RESOLVED.value,
        CaseStatus.ESCALATED.value,
        CaseStatus.CLOSED.value
    ],
    CaseStatus.HUMAN_REVIEW.value: [
        CaseStatus.ACTION_PENDING.value,
        CaseStatus.VERIFYING.value,
        CaseStatus.RESOLVED.value,
        CaseStatus.ESCALATED.value,
        CaseStatus.CLOSED.value
    ],
    CaseStatus.ACTION_PENDING.value: [
        CaseStatus.VERIFYING.value,
        CaseStatus.HUMAN_REVIEW.value,
        CaseStatus.RESOLVED.value,
        CaseStatus.ESCALATED.value,
        CaseStatus.CLOSED.value
    ],
    CaseStatus.VERIFYING.value: [
        CaseStatus.RESOLVED.value,
        CaseStatus.INVESTIGATING.value,
        CaseStatus.HUMAN_REVIEW.value,
        CaseStatus.ESCALATED.value,
        CaseStatus.CLOSED.value
    ],
    CaseStatus.RESOLVED.value: [
        CaseStatus.CLOSED.value,
        CaseStatus.TRIAGING.value  # Re-opened case
    ],
    CaseStatus.ESCALATED.value: [
        CaseStatus.TRIAGING.value,
        CaseStatus.INVESTIGATING.value,
        CaseStatus.HUMAN_REVIEW.value,
        CaseStatus.RESOLVED.value,
        CaseStatus.CLOSED.value
    ],
    CaseStatus.CLOSED.value: [
        CaseStatus.TRIAGING.value  # Re-opened case
    ]
}

SLA_HOURS = {
    CasePriority.URGENT.value: 1,
    CasePriority.HIGH.value: 4,
    CasePriority.MEDIUM.value: 24,
    CasePriority.LOW.value: 48,
}


class InvalidStateTransitionError(ValueError):
    """Raised when an illegal case lifecycle state transition is attempted."""
    pass


class CaseService:
    @staticmethod
    def generate_case_id(db: Session) -> str:
        """Generate human-readable sequential case identifier like CASE-10001."""
        count = db.query(SupportCase).count() + 1
        return f"CASE-{10000 + count}"

    @staticmethod
    def calculate_sla_deadline(priority: str, start_time: Optional[datetime.datetime] = None) -> datetime.datetime:
        now = start_time or get_utc_now()
        hours = SLA_HOURS.get(priority.lower(), 24)
        return now + datetime.timedelta(hours=hours)

    @classmethod
    def create_case(cls, db: Session, data: CaseCreate) -> SupportCase:
        now = get_utc_now()
        case_id = cls.generate_case_id(db)

        # Validate customer
        customer = db.query(Customer).filter(Customer.customer_id == data.customer_id).first()
        if not customer:
            # Fallback customer creation if needed for seamless testing/channel ingestion
            customer = Customer(
                customer_id=data.customer_id,
                organization_id=data.organization_id or "ORG-NOVACART",
                name=f"Customer {data.customer_id}",
                email=f"{data.customer_id.lower()}@customer.novacart.com",
                tier="Standard",
                account_status="Active",
                created_at=now
            )
            db.add(customer)
            db.commit()

        sla_deadline = cls.calculate_sla_deadline(data.priority or "medium", now)

        case = SupportCase(
            id=case_id,
            organization_id=data.organization_id or "ORG-NOVACART",
            customer_id=data.customer_id,
            conversation_id=data.conversation_id,
            channel=data.channel or CaseChannel.WEB_CHAT.value,
            subject=data.subject,
            description=data.description or data.subject,
            intent=data.intent,
            priority=(data.priority or CasePriority.MEDIUM.value).lower(),
            status=CaseStatus.NEW.value,
            sla_deadline=sla_deadline,
            created_at=now,
            updated_at=now
        )
        db.add(case)
        db.commit()
        db.refresh(case)

        # Record CASE_CREATED event
        cls.record_case_event(
            db=db,
            case_id=case.id,
            event_type=EventType.CASE_CREATED.value,
            actor="System",
            summary=f"Support case '{case.subject}' registered via {case.channel}.",
            details={"priority": case.priority, "customer_id": case.customer_id}
        )

        # Record AuditLog
        cls.record_audit_log(
            db=db,
            entity_type="SupportCase",
            entity_id=case.id,
            action="CASE_CREATED",
            actor_type="system",
            actor_id="CaseEngine",
            case_id=case.id,
            details={"priority": case.priority, "channel": case.channel}
        )

        # Store initial message if provided
        if data.initial_message:
            cls.add_case_message(
                db=db,
                case_id=case.id,
                msg_data=CaseMessageCreate(
                    body=data.initial_message,
                    direction=MessageDirection.INBOUND.value,
                    channel=case.channel,
                    sender_type=SenderType.CUSTOMER.value,
                    sender_id=case.customer_id
                )
            )

        return case

    @classmethod
    def get_case(cls, db: Session, case_id: str) -> Optional[SupportCase]:
        return db.query(SupportCase).filter(SupportCase.id == case_id).first()

    @classmethod
    def list_cases(
        cls,
        db: Session,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        customer_id: Optional[str] = None,
        channel: Optional[str] = None,
        search: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[SupportCase]:
        query = db.query(SupportCase)
        if status:
            query = query.filter(SupportCase.status == status.upper())
        if priority:
            query = query.filter(SupportCase.priority == priority.lower())
        if customer_id:
            query = query.filter(SupportCase.customer_id == customer_id)
        if channel:
            query = query.filter(SupportCase.channel == channel)
        if search:
            search_pattern = f"%{search}%"
            query = query.filter(
                or_(
                    SupportCase.id.ilike(search_pattern),
                    SupportCase.subject.ilike(search_pattern),
                    SupportCase.description.ilike(search_pattern),
                    SupportCase.intent.ilike(search_pattern)
                )
            )
        return query.order_by(desc(SupportCase.created_at)).offset(offset).limit(limit).all()

    @classmethod
    def transition_status(
        cls,
        db: Session,
        case: SupportCase,
        new_status: str,
        actor: str = "System",
        reason: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> SupportCase:
        new_status_upper = new_status.upper()
        current_status = case.status

        if current_status == new_status_upper:
            return case

        allowed = ALLOWED_TRANSITIONS.get(current_status, [])
        if new_status_upper not in allowed:
            raise InvalidStateTransitionError(
                f"Illegal lifecycle transition from '{current_status}' to '{new_status_upper}'. "
                f"Allowed target states: {allowed}"
            )

        now = get_utc_now()
        case.status = new_status_upper
        case.updated_at = now

        if new_status_upper == CaseStatus.RESOLVED.value and not case.resolved_at:
            case.resolved_at = now

        db.commit()
        db.refresh(case)

        # Record STATUS_CHANGED event
        summary = f"Case moved from {current_status} to {new_status_upper}."
        if reason:
            summary += f" Reason: {reason}"

        cls.record_case_event(
            db=db,
            case_id=case.id,
            event_type=EventType.STATUS_CHANGED.value,
            actor=actor,
            summary=summary,
            from_status=current_status,
            to_status=new_status_upper,
            details=details or {"reason": reason}
        )

        # Record AuditLog
        cls.record_audit_log(
            db=db,
            entity_type="SupportCase",
            entity_id=case.id,
            action="STATUS_CHANGED",
            actor_type="system" if actor == "System" else "agent",
            actor_id=actor,
            case_id=case.id,
            details={"from_status": current_status, "to_status": new_status_upper, "reason": reason}
        )

        return case

    @classmethod
    def update_case(cls, db: Session, case_id: str, data: CaseUpdate) -> SupportCase:
        case = cls.get_case(db, case_id)
        if not case:
            raise ValueError(f"Support case '{case_id}' not found.")

        # Status transition
        if data.status:
            cls.transition_status(
                db=db,
                case=case,
                new_status=data.status,
                actor=data.actor or "system",
                reason=data.reason
            )

        # Attribute updates
        if data.priority and data.priority.lower() != case.priority:
            case.priority = data.priority.lower()
            case.sla_deadline = cls.calculate_sla_deadline(case.priority, case.created_at)

        if data.subject:
            case.subject = data.subject
        if data.description:
            case.description = data.description
        if data.intent:
            case.intent = data.intent
        if data.sentiment:
            case.sentiment = data.sentiment

        case.updated_at = get_utc_now()
        db.commit()
        db.refresh(case)
        return case

    @classmethod
    def add_case_message(cls, db: Session, case_id: str, msg_data: CaseMessageCreate) -> CaseMessage:
        case = cls.get_case(db, case_id)
        if not case:
            raise ValueError(f"Support case '{case_id}' not found.")

        now = get_utc_now()
        msg = CaseMessage(
            case_id=case_id,
            direction=msg_data.direction or MessageDirection.OUTBOUND.value,
            channel=msg_data.channel or case.channel,
            sender_type=msg_data.sender_type or SenderType.AGENT.value,
            sender_id=msg_data.sender_id,
            body=msg_data.body,
            metadata_json=msg_data.metadata_json,
            created_at=now
        )
        case.updated_at = now
        db.add(msg)
        db.commit()
        db.refresh(msg)
        return msg

    @classmethod
    def record_case_event(
        cls,
        db: Session,
        case_id: str,
        event_type: str,
        actor: str,
        summary: str,
        from_status: Optional[str] = None,
        to_status: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> CaseEvent:
        event = CaseEvent(
            case_id=case_id,
            event_type=event_type,
            from_status=from_status,
            to_status=to_status,
            actor=actor,
            summary=summary,
            details_json=json.dumps(details) if details else None,
            created_at=get_utc_now()
        )
        db.add(event)
        db.commit()
        db.refresh(event)
        return event

    @classmethod
    def start_agent_run(
        cls,
        db: Session,
        case_id: str,
        agent_name: str,
        task_id: Optional[str] = None
    ) -> AgentRun:
        run = AgentRun(
            case_id=case_id,
            task_id=task_id,
            agent_name=agent_name,
            started_at=get_utc_now(),
            status="running"
        )
        db.add(run)
        db.commit()
        db.refresh(run)

        # Log event
        cls.record_case_event(
            db=db,
            case_id=case_id,
            event_type=EventType.AGENT_STARTED.value,
            actor=agent_name,
            summary=f"Specialist agent '{agent_name}' initiated cognitive step."
        )
        return run

    @classmethod
    def complete_agent_run(
        cls,
        db: Session,
        run_id: int,
        status: str = "completed",
        output_summary: Optional[str] = None,
        confidence: Optional[float] = None,
        error_info: Optional[str] = None
    ) -> Optional[AgentRun]:
        run = db.query(AgentRun).filter(AgentRun.id == run_id).first()
        if not run:
            return None

        run.ended_at = get_utc_now()
        run.status = status
        run.output_summary = output_summary
        run.confidence = confidence
        run.error_info = error_info
        db.commit()
        db.refresh(run)

        # Log completion event
        cls.record_case_event(
            db=db,
            case_id=run.case_id,
            event_type=EventType.AGENT_COMPLETED.value if status == "completed" else EventType.FAILURE.value,
            actor=run.agent_name,
            summary=f"Agent '{run.agent_name}' {status}: {output_summary or 'Step finished.'}",
            details={"confidence": confidence, "status": status}
        )
        return run

    @classmethod
    def record_agent_action(
        cls,
        db: Session,
        case_id: str,
        agent_name: str,
        action_type: str,
        task_id: Optional[str] = None,
        requested_by: Optional[str] = None,
        status: str = "completed",
        input_summary: Optional[str] = None,
        output_summary: Optional[str] = None,
        input_metadata: Optional[Dict[str, Any]] = None,
        result_metadata: Optional[Dict[str, Any]] = None,
        confidence: float = 1.0,
        duration_ms: int = 0
    ) -> AgentAction:
        effective_task_id = task_id or case_id or f"task-{uuid.uuid4().hex[:8]}"
        action = AgentAction(
            case_id=case_id,
            task_id=effective_task_id,
            agent_name=agent_name,
            action_type=action_type,
            requested_by=requested_by or agent_name,
            status=status,
            input_summary=input_summary,
            output_summary=output_summary,
            input_metadata=json.dumps(input_metadata) if input_metadata else None,
            result_metadata=json.dumps(result_metadata) if result_metadata else None,
            confidence=confidence,
            duration_ms=duration_ms,
            created_at=get_utc_now()
        )
        db.add(action)
        db.commit()
        db.refresh(action)

        cls.record_case_event(
            db=db,
            case_id=case_id,
            event_type=EventType.TOOL_EXECUTED.value,
            actor=agent_name,
            summary=f"Action '{action_type}' executed ({status}). {output_summary or ''}",
            details={"input": input_summary, "duration_ms": duration_ms}
        )
        return action

    @classmethod
    def record_audit_log(
        cls,
        db: Session,
        entity_type: str,
        entity_id: str,
        action: str,
        actor_type: str = "system",
        actor_id: str = "system",
        case_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> AuditLog:
        audit = AuditLog(
            case_id=case_id,
            entity_type=entity_type,
            entity_id=str(entity_id),
            action=action,
            actor_type=actor_type,
            actor_id=actor_id,
            details_json=json.dumps(details) if details else None,
            created_at=get_utc_now()
        )
        db.add(audit)
        db.commit()
        db.refresh(audit)
        return audit

    @classmethod
    def get_case_timeline(cls, db: Session, case_id: str) -> List[TimelineItemResponse]:
        """Aggregate all case interactions, state shifts, agent runs, actions, and escalations into a unified chronological stream."""
        items: List[TimelineItemResponse] = []

        # 1. Case Messages
        messages = db.query(CaseMessage).filter(CaseMessage.case_id == case_id).all()
        for m in messages:
            items.append(
                TimelineItemResponse(
                    id=f"msg-{m.id}",
                    item_type="message",
                    timestamp=m.created_at,
                    title=f"{m.sender_type.capitalize()} Message ({m.direction})",
                    description=m.body,
                    actor=m.sender_id or m.sender_type,
                    badge=m.channel,
                    status=m.direction,
                    metadata={"metadata_json": m.metadata_json}
                )
            )

        # 2. Case Events
        events = db.query(CaseEvent).filter(CaseEvent.case_id == case_id).all()
        for e in events:
            items.append(
                TimelineItemResponse(
                    id=f"evt-{e.id}",
                    item_type="event",
                    timestamp=e.created_at,
                    title=e.event_type.replace("_", " ").title(),
                    description=e.summary,
                    actor=e.actor,
                    badge=e.to_status or e.event_type,
                    status="info",
                    metadata=json.loads(e.details_json) if e.details_json else None
                )
            )

        # 3. Agent Runs
        runs = db.query(AgentRun).filter(AgentRun.case_id == case_id).all()
        for r in runs:
            items.append(
                TimelineItemResponse(
                    id=f"run-{r.id}",
                    item_type="agent_run",
                    timestamp=r.started_at,
                    title=f"Agent Run: {r.agent_name}",
                    description=r.output_summary or f"Agent status: {r.status}",
                    actor=r.agent_name,
                    badge=r.status,
                    status="success" if r.status == "completed" else "warning",
                    metadata={"confidence": r.confidence, "error": r.error_info}
                )
            )

        # 4. Agent Actions
        actions = db.query(AgentAction).filter(AgentAction.case_id == case_id).all()
        for a in actions:
            items.append(
                TimelineItemResponse(
                    id=f"act-{a.id}",
                    item_type="action",
                    timestamp=a.created_at,
                    title=f"Action: {a.action_type}",
                    description=a.output_summary or a.input_summary or "Action executed",
                    actor=a.agent_name,
                    badge=a.status,
                    status="success" if a.status == "completed" else "warning",
                    metadata={"duration_ms": a.duration_ms}
                )
            )

        # 5. Escalations
        escalations = db.query(EscalationTicket).filter(EscalationTicket.case_id == case_id).all()
        for esc in escalations:
            items.append(
                TimelineItemResponse(
                    id=f"esc-{esc.ticket_id}",
                    item_type="escalation",
                    timestamp=esc.created_at,
                    title=f"Human Escalation: #{esc.ticket_id}",
                    description=esc.reason,
                    actor="Escalation Agent",
                    badge=esc.priority,
                    status="urgent",
                    metadata={"summary": esc.summary, "assigned_to": esc.assigned_to}
                )
            )

        # Sort chronologically
        items.sort(key=lambda x: x.timestamp)
        return items
