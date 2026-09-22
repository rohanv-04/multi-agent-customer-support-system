import uuid
import json
import hashlib
import datetime
from typing import Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import or_

from ..database.models import (
    get_utc_now,
    Customer,
    SupportCase,
    CaseMessage,
    CaseEvent,
    AuditLog
)
from ..schemas.case import (
    CaseStatus,
    CasePriority,
    CaseCreate,
    CaseMessageCreate,
    MessageDirection,
    SenderType,
    EventType
)
from ..schemas.omnichannel import (
    ChannelType,
    SupportRequest,
    InboundProcessingResult,
    ProviderMessageResponse
)
from ..providers.base import BaseChannelProvider
from ..providers.channel_providers import (
    WebChatProvider,
    EmailProvider,
    WhatsAppProvider,
    APIProvider,
    SupportFormProvider
)
from .case_service import CaseService


class DeduplicationRegistry:
    """Thread-safe in-memory cache for fast deduplication checking."""
    def __init__(self, ttl_seconds: int = 3600):
        self._processed_ids: Dict[str, datetime.datetime] = {}
        self._content_hashes: Dict[str, datetime.datetime] = {}
        self._ttl = datetime.timedelta(seconds=ttl_seconds)

    def _cleanup(self, now: datetime.datetime):
        expired_ids = [k for k, v in self._processed_ids.items() if now - v > self._ttl]
        for k in expired_ids:
            del self._processed_ids[k]
        expired_hashes = [k for k, v in self._content_hashes.items() if now - v > self._ttl]
        for k in expired_hashes:
            del self._content_hashes[k]

    def is_duplicate(self, request_id: str, sender: str, body: str, channel: str) -> bool:
        now = get_utc_now()
        self._cleanup(now)

        # Check explicit request ID
        if request_id in self._processed_ids:
            return True

        # Check content hash for fast repeat spam
        content_key = f"{channel}:{sender.lower()}:{body.strip()}"
        content_hash = hashlib.sha256(content_key.encode("utf-8")).hexdigest()
        if content_hash in self._content_hashes:
            return True

        # Register
        self._processed_ids[request_id] = now
        self._content_hashes[content_hash] = now
        return False

    def clear(self):
        """Used in test fixtures for clean slate testing."""
        self._processed_ids.clear()
        self._content_hashes.clear()


dedup_registry = DeduplicationRegistry()


class OmnichannelService:
    """
    Omnichannel Ingestion & Dispatch Engine.
    Normalizes requests from all 5 channels, handles deduplication, resolves customer identities,
    links/creates SupportCases, and coordinates AI workflow execution.
    """

    def __init__(self):
        self._providers: Dict[str, BaseChannelProvider] = {
            ChannelType.WEB_CHAT.value: WebChatProvider(),
            ChannelType.EMAIL.value: EmailProvider(),
            ChannelType.WHATSAPP.value: WhatsAppProvider(),
            ChannelType.API.value: APIProvider(),
            ChannelType.SUPPORT_FORM.value: SupportFormProvider()
        }

    def register_provider(self, provider: BaseChannelProvider):
        """Allows plugging in external custom or production providers."""
        self._providers[provider.channel_type.value] = provider

    def get_provider(self, channel: str) -> BaseChannelProvider:
        provider = self._providers.get(channel.lower())
        if not provider:
            raise ValueError(f"No registered channel provider for '{channel}'")
        return provider

    def normalize_inbound(
        self,
        channel: str,
        payload: Dict[str, Any],
        headers: Optional[Dict[str, str]] = None
    ) -> SupportRequest:
        """Parses raw payload using the corresponding channel provider."""
        provider = self.get_provider(channel)
        return provider.normalize_inbound(payload, headers)

    def resolve_customer(self, db: Session, req: SupportRequest) -> Customer:
        """
        Resolves customer identity using customer_id, email, phone, or creates a new customer.
        """
        now = get_utc_now()

        # 1. Direct ID lookup
        if req.customer_id:
            cust = db.query(Customer).filter(Customer.customer_id == req.customer_id).first()
            if cust:
                return cust

        # 2. Lookup by email / phone / identifier
        identifier = req.sender_identifier.strip().lower()
        cust = db.query(Customer).filter(
            or_(
                Customer.email.ilike(identifier),
                Customer.phone == req.sender_identifier
            )
        ).first()
        if cust:
            return cust

        # 3. Auto-provision Customer record if unknown
        generated_id = f"CUST-AUTO-{hashlib.md5(identifier.encode()).hexdigest()[:6].upper()}"
        email = identifier if "@" in identifier else f"{identifier.replace('+', '')}@mobile.novacart.com"
        phone = req.sender_identifier if "@" not in identifier else None
        name = req.sender_name or f"Omnichannel Customer ({req.channel.value})"

        new_cust = Customer(
            customer_id=generated_id,
            organization_id="ORG-NOVACART",
            name=name,
            email=email,
            phone=phone,
            tier="Standard",
            account_status="Active",
            created_at=now
        )
        db.add(new_cust)
        db.commit()
        db.refresh(new_cust)
        return new_cust

    def process_inbound_request(
        self,
        db: Session,
        req: SupportRequest,
        trigger_workflow: bool = True
    ) -> InboundProcessingResult:
        """
        End-to-end ingestion pipeline:
        SupportRequest -> Deduplication -> Customer Lookup -> SupportCase -> AI Workflow -> Outbound Delivery
        """
        # 1. Deduplication check
        if dedup_registry.is_duplicate(req.request_id, req.sender_identifier, req.body, req.channel.value):
            return InboundProcessingResult(
                request_id=req.request_id,
                channel=req.channel.value,
                is_duplicate=True,
                customer_id=req.customer_id or "UNKNOWN",
                case_id=None,
                status="deduplicated",
                message="Duplicate message ignored to prevent reprocessing loop."
            )

        # 2. Resolve or create customer
        customer = self.resolve_customer(db, req)

        # 3. Find active existing case or create new SupportCase
        active_case = None
        if req.conversation_id:
            active_case = db.query(SupportCase).filter(
                SupportCase.conversation_id == req.conversation_id,
                SupportCase.status.notin_([CaseStatus.RESOLVED.value, CaseStatus.CLOSED.value])
            ).first()

        if not active_case:
            # Check most recent open case for this customer in the past 24 hours
            recent_threshold = get_utc_now() - datetime.timedelta(hours=24)
            active_case = db.query(SupportCase).filter(
                SupportCase.customer_id == customer.customer_id,
                SupportCase.channel == req.channel.value,
                SupportCase.created_at >= recent_threshold,
                SupportCase.status.notin_([CaseStatus.RESOLVED.value, CaseStatus.CLOSED.value])
            ).order_by(SupportCase.created_at.desc()).first()

        if not active_case:
            # Create new SupportCase
            case_create = CaseCreate(
                customer_id=customer.customer_id,
                subject=req.subject or f"Inquiry via {req.channel.value}",
                description=req.body,
                channel=req.channel.value,
                priority=req.metadata.get("urgency", "medium").lower() if req.metadata else "medium",
                conversation_id=req.conversation_id or f"conv-{req.request_id}",
                initial_message=req.body
            )
            active_case = CaseService.create_case(db, case_create)
        else:
            # Append inbound message to existing case
            CaseService.add_case_message(
                db=db,
                case_id=active_case.id,
                msg_data=CaseMessageCreate(
                    body=req.body,
                    direction=MessageDirection.INBOUND.value,
                    channel=req.channel.value,
                    sender_type=SenderType.CUSTOMER.value,
                    sender_id=customer.customer_id,
                    metadata_json=json.dumps(req.metadata) if req.metadata else None
                )
            )

        # 4. Optional AI Workflow execution
        ai_response_text = None
        if trigger_workflow:
            try:
                from ..graph.workflow import support_graph
                from ..graph.state import AgenticSupportState
                
                initial_state: AgenticSupportState = {
                    "task_id": f"task-{uuid.uuid4().hex[:8]}",
                    "customer_id": customer.customer_id,
                    "conversation_id": active_case.conversation_id,
                    "case_id": active_case.id,
                    "user_goal": req.body,
                    "messages": [{"role": "user", "content": req.body}],
                    "customer_360": None,
                    "intent": {},
                    "investigation_result": None,
                    "policy_evaluation": None,
                    "decision_result": None,
                    "risk_evaluation": None,
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
                final_state = support_graph.invoke(initial_state)
                ai_response_text = final_state.get("final_response") or "Thank you for contacting NovaCart Support. We have logged your request."
                
                # Send outbound reply through the appropriate channel provider
                provider = self.get_provider(req.channel.value)
                provider.send_outbound(
                    recipient=req.sender_identifier,
                    body=ai_response_text,
                    metadata={"case_id": active_case.id, "subject": f"Re: {active_case.subject}"}
                )

                # Record outbound CaseMessage in DB
                CaseService.add_case_message(
                    db=db,
                    case_id=active_case.id,
                    msg_data=CaseMessageCreate(
                        body=ai_response_text,
                        direction=MessageDirection.OUTBOUND.value,
                        channel=req.channel.value,
                        sender_type=SenderType.AGENT.value,
                        sender_id="SupportOS-AI",
                        metadata_json=json.dumps({"workflow_task_id": final_state.get("task_id")})
                    )
                )
            except Exception as e:
                ai_response_text = f"Your request has been logged under case {active_case.id}."
                CaseService.record_case_event(
                    db=db,
                    case_id=active_case.id,
                    event_type=EventType.FAILURE.value,
                    actor="OmnichannelService",
                    summary=f"Automated workflow dispatch exception: {str(e)}"
                )

        return InboundProcessingResult(
            request_id=req.request_id,
            channel=req.channel.value,
            is_duplicate=False,
            customer_id=customer.customer_id,
            case_id=active_case.id,
            status="processed",
            message=f"Support request successfully processed under case {active_case.id}",
            ai_response=ai_response_text
        )

    def dispatch_outbound(
        self,
        db: Session,
        case_id: str,
        channel: str,
        recipient: str,
        body: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ProviderMessageResponse:
        """Sends an outbound communication over the designated channel provider and records in database."""
        provider = self.get_provider(channel)
        result = provider.send_outbound(recipient=recipient, body=body, metadata=metadata)

        # Record outbound message in case
        CaseService.add_case_message(
            db=db,
            case_id=case_id,
            msg_data=CaseMessageCreate(
                body=body,
                direction=MessageDirection.OUTBOUND.value,
                channel=channel,
                sender_type=SenderType.AGENT.value,
                sender_id="Agent",
                metadata_json=json.dumps({
                    "provider_name": result.provider_name,
                    "message_id": result.message_id,
                    "status": result.status
                })
            )
        )

        return result


omnichannel_service = OmnichannelService()
