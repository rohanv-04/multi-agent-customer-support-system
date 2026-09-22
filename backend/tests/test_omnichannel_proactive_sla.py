import uuid
import pytest
import datetime
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.database.database import SessionLocal, init_db
from backend.app.database.models import (
    Customer,
    SupportCase,
    CaseMessage,
    CaseEvent,
    EscalationTicket,
    AuditLog,
    get_utc_now
)
from backend.app.schemas.omnichannel import (
    ChannelType,
    SupportRequest,
    BusinessEventType,
    BusinessEventPayload,
    SLABreachStatus
)
from backend.app.schemas.case import CasePriority, CaseStatus
from backend.app.services.omnichannel_service import omnichannel_service, dedup_registry
from backend.app.services.proactive_support_service import proactive_support_service
from backend.app.services.sla_engine import sla_engine
from backend.app.services.case_service import CaseService


@pytest.fixture(autouse=True)
def setup_database_and_cache():
    init_db()
    dedup_registry.clear()
    yield


@pytest.fixture
def client():
    return TestClient(app)


# =========================================================================
# 1. TEST OMNICHANNEL INGESTION ACROSS ALL 5 CHANNELS
# =========================================================================

def test_ingestion_channel_web_chat():
    db = SessionLocal()
    try:
        raw_payload = {
            "message_id": "chat-test-001",
            "customer_id": "CUST1002",
            "message": "Where is my order #ORD-2024-9001?",
            "conversation_id": "conv-webchat-001",
            "ip_address": "192.168.1.50"
        }
        req = omnichannel_service.normalize_inbound("web_chat", raw_payload)
        assert req.channel == ChannelType.WEB_CHAT
        assert req.sender_identifier == "CUST1002"
        assert "ORD-2024-9001" in req.body

        result = omnichannel_service.process_inbound_request(db, req, trigger_workflow=False)
        assert result.is_duplicate is False
        assert result.status == "processed"
        assert result.case_id is not None

        case = db.query(SupportCase).filter(SupportCase.id == result.case_id).first()
        assert case is not None
        assert case.channel == "web_chat"
        assert case.customer_id == "CUST1002"
    finally:
        db.close()


def test_ingestion_channel_email():
    db = SessionLocal()
    try:
        raw_payload = {
            "from": "sarah.connor@cyberdyne.org",
            "from_name": "Sarah Connor",
            "subject": "Damaged Package Delivery",
            "body": "Hello Support, I received my package but the mechanical unit inside is completely shattered.",
            "message_id": "email-msg-5501",
            "attachments": ["photo_evidence.jpg"]
        }
        req = omnichannel_service.normalize_inbound("email", raw_payload)
        assert req.channel == ChannelType.EMAIL
        assert req.sender_identifier == "sarah.connor@cyberdyne.org"
        assert req.subject == "Damaged Package Delivery"

        result = omnichannel_service.process_inbound_request(db, req, trigger_workflow=False)
        assert result.is_duplicate is False
        assert result.case_id is not None

        # Verify auto-created customer and case
        case = db.query(SupportCase).filter(SupportCase.id == result.case_id).first()
        assert case is not None
        assert case.channel == "email"
        
        # Verify message persistence
        msg = db.query(CaseMessage).filter(CaseMessage.case_id == case.id).first()
        assert msg is not None
        assert msg.direction == "inbound"
        assert msg.channel == "email"
        assert "shattered" in msg.body
    finally:
        db.close()


def test_ingestion_channel_whatsapp():
    db = SessionLocal()
    try:
        raw_payload = {
            "wa_id": "+14155552671",
            "profile_name": "John Connor",
            "text": {"body": "Hi, need to change my delivery address to 404 Resistance Way."},
            "message_id": "wamid.HBgLMTQxNTU1NTI2NzEVAgASGB",
            "timestamp": "1726000000"
        }
        req = omnichannel_service.normalize_inbound("whatsapp", raw_payload)
        assert req.channel == ChannelType.WHATSAPP
        assert req.sender_identifier == "+14155552671"
        assert "Resistance Way" in req.body

        result = omnichannel_service.process_inbound_request(db, req, trigger_workflow=False)
        assert result.is_duplicate is False
        assert result.case_id is not None

        case = db.query(SupportCase).filter(SupportCase.id == result.case_id).first()
        assert case.channel == "whatsapp"
    finally:
        db.close()


def test_ingestion_channel_api():
    db = SessionLocal()
    try:
        raw_payload = {
            "request_id": "b2b-api-req-8899",
            "client_id": "PARTNER-SHOP",
            "customer_id": "CUST1003",
            "subject": "B2B Bulk Inventory Inquiry",
            "query": "Status inquiry for wholesale batch PO-9921",
            "priority": "high"
        }
        req = omnichannel_service.normalize_inbound("api", raw_payload)
        assert req.channel == ChannelType.API
        assert req.customer_id == "CUST1003"

        result = omnichannel_service.process_inbound_request(db, req, trigger_workflow=False)
        assert result.is_duplicate is False
        assert result.case_id is not None

        case = db.query(SupportCase).filter(SupportCase.id == result.case_id).first()
        assert case.channel == "api"
    finally:
        db.close()


def test_ingestion_channel_support_form():
    db = SessionLocal()
    try:
        raw_payload = {
            "form_submission_id": "form-sub-1004",
            "name": "Alex Mercer",
            "email": "alex.mercer@gentek.com",
            "order_number": "ORD-2024-8844",
            "category": "Billing & Refund",
            "description": "I was double-charged on my credit card statement for Order ORD-2024-8844.",
            "urgency": "urgent"
        }
        req = omnichannel_service.normalize_inbound("support_form", raw_payload)
        assert req.channel == ChannelType.SUPPORT_FORM
        assert "ORD-2024-8844" in req.body
        assert req.metadata.get("category") == "Billing & Refund"

        result = omnichannel_service.process_inbound_request(db, req, trigger_workflow=False)
        assert result.is_duplicate is False
        assert result.case_id is not None

        case = db.query(SupportCase).filter(SupportCase.id == result.case_id).first()
        assert case.channel == "support_form"
    finally:
        db.close()


# =========================================================================
# 2. TEST DUPLICATE MESSAGE PREVENTION / DEDUPLICATION
# =========================================================================

def test_duplicate_message_prevention():
    db = SessionLocal()
    try:
        raw_payload = {
            "message_id": "dedup-test-unique-id-999",
            "customer_id": "CUST1002",
            "message": "Duplicate check test inquiry message."
        }
        req1 = omnichannel_service.normalize_inbound("web_chat", raw_payload)
        res1 = omnichannel_service.process_inbound_request(db, req1, trigger_workflow=False)
        assert res1.is_duplicate is False
        assert res1.case_id is not None

        # Repeat identical message ID
        req2 = omnichannel_service.normalize_inbound("web_chat", raw_payload)
        res2 = omnichannel_service.process_inbound_request(db, req2, trigger_workflow=False)
        assert res2.is_duplicate is True
        assert res2.status == "deduplicated"
        assert res2.case_id is None
        assert "ignored" in res2.message.lower()

        # Repeat same sender + content spam with different request_id
        spam_payload = {
            "message_id": "dedup-test-different-id-888",
            "customer_id": "CUST1002",
            "message": "Duplicate check test inquiry message."
        }
        req3 = omnichannel_service.normalize_inbound("web_chat", spam_payload)
        res3 = omnichannel_service.process_inbound_request(db, req3, trigger_workflow=False)
        assert res3.is_duplicate is True
    finally:
        db.close()


# =========================================================================
# 3. TEST PROACTIVE SUPPORT ENGINE (BUSINESS EVENTS & OUTREACH)
# =========================================================================

def test_proactive_event_shipment_delay():
    db = SessionLocal()
    try:
        event = BusinessEventPayload(
            event_id="evt-delay-101",
            event_type=BusinessEventType.SHIPMENT_DELAY,
            customer_id="CUST1002",
            order_id="ORD-2024-9001",
            severity="high",
            details={"order_id": "ORD-2024-9001", "carrier": "FedEx", "delay_days": 3},
            source_system="CarrierWebhookService"
        )
        impact = proactive_support_service.evaluate_business_event(db, event)
        assert impact.case_created is True
        assert impact.case_id is not None
        assert impact.impact_level == "high"
        assert impact.compensation_granted is not None
        assert "NovaCredit" in impact.compensation_granted

        # Verify case in DB
        case = db.query(SupportCase).filter(SupportCase.id == impact.case_id).first()
        assert case is not None
        assert "ORD-2024-9001" in case.subject
        assert case.priority == "high"

        # Verify proactive outbound message recorded
        msg = db.query(CaseMessage).filter(CaseMessage.case_id == case.id, CaseMessage.direction == "outbound").first()
        assert msg is not None
        assert "transit delay" in msg.body
    finally:
        db.close()


def test_proactive_event_payment_failure():
    db = SessionLocal()
    try:
        event = BusinessEventPayload(
            event_id="evt-pay-202",
            event_type=BusinessEventType.PAYMENT_FAILURE,
            customer_id="CUST1001",
            severity="high",
            details={"amount": 149.99, "decline_reason": "Card expired"},
            source_system="StripeBillingWebhook"
        )
        impact = proactive_support_service.evaluate_business_event(db, event)
        assert impact.case_created is True
        assert impact.impact_level == "high"
        assert "billing details" in impact.outreach_message.lower()
    finally:
        db.close()


def test_proactive_event_repeated_failed_delivery():
    db = SessionLocal()
    try:
        event = BusinessEventPayload(
            event_id="evt-delivery-303",
            event_type=BusinessEventType.REPEATED_FAILED_DELIVERY,
            customer_id="CUST1002",
            order_id="ORD-2024-9001",
            severity="high",
            details={"attempts": 2, "carrier_note": "Gate code required"},
            source_system="NovaExpressDriverApp"
        )
        impact = proactive_support_service.evaluate_business_event(db, event)
        assert impact.case_created is True
        assert "gate code" in impact.outreach_message.lower()
    finally:
        db.close()


# =========================================================================
# 4. TEST SLA CALCULATION & POLICIES
# =========================================================================

def test_sla_calculation_standard_and_vip():
    now = get_utc_now()
    
    # Standard Customer SLA
    urgent_std = sla_engine.calculate_deadline(CasePriority.URGENT.value, "Standard", now)
    assert (urgent_std - now).total_seconds() == 3600.0  # 1 hour

    high_std = sla_engine.calculate_deadline(CasePriority.HIGH.value, "Standard", now)
    assert (high_std - now).total_seconds() == 4 * 3600.0  # 4 hours

    # VIP Customer Accelerated SLA
    urgent_vip = sla_engine.calculate_deadline(CasePriority.URGENT.value, "Platinum", now)
    assert (urgent_vip - now).total_seconds() == 1800.0  # 0.5 hour (30 min)

    high_vip = sla_engine.calculate_deadline(CasePriority.HIGH.value, "VIP", now)
    assert (high_vip - now).total_seconds() == 2 * 3600.0  # 2 hours


# =========================================================================
# 5. TEST SLA BREACH & APPROACHING BREACH DETECTION
# =========================================================================

def test_sla_status_ok_and_approaching_breach():
    db = SessionLocal()
    try:
        now = get_utc_now()
        
        # 1. OK case (deadline far in future)
        case_ok = SupportCase(
            id=f"CASE-SLA-OK-{uuid.uuid4().hex[:6]}",
            customer_id="CUST1001",
            channel="web_chat",
            subject="Standard In-Window Case",
            priority="medium",
            status=CaseStatus.INVESTIGATING.value,
            sla_deadline=now + datetime.timedelta(hours=10),
            created_at=now
        )
        db.add(case_ok)
        db.commit()

        res_ok = sla_engine.evaluate_case_sla(db, case_ok, auto_escalate=False)
        assert res_ok.breach_status == SLABreachStatus.OK
        assert res_ok.is_breached is False
        assert res_ok.is_approaching_breach is False

        # 2. Approaching breach case (e.g. only 10 minutes remaining on a 4-hour window)
        case_warn = SupportCase(
            id=f"CASE-SLA-WARN-{uuid.uuid4().hex[:6]}",
            customer_id="CUST1001",
            channel="web_chat",
            subject="Approaching Deadline Case",
            priority="high",
            status=CaseStatus.INVESTIGATING.value,
            sla_deadline=now + datetime.timedelta(minutes=10),
            created_at=now - datetime.timedelta(hours=3, minutes=50)
        )
        db.add(case_warn)
        db.commit()

        res_warn = sla_engine.evaluate_case_sla(db, case_warn, auto_escalate=False)
        assert res_warn.breach_status == SLABreachStatus.APPROACHING_BREACH
        assert res_warn.is_approaching_breach is True
        assert res_warn.is_breached is False

        # Verify supervisor alert event was recorded
        evt = db.query(CaseEvent).filter(
            CaseEvent.case_id == case_warn.id,
            CaseEvent.actor == "SLAEngine"
        ).first()
        assert evt is not None
        assert "approaching deadline" in evt.summary.lower()
    finally:
        db.close()


# =========================================================================
# 6. TEST SLA BREACH & AUTO-ESCALATION
# =========================================================================

def test_sla_breach_and_auto_escalation():
    db = SessionLocal()
    try:
        now = get_utc_now()
        
        # Case created 5 hours ago with 1 hour deadline -> definitely breached
        case_breached = SupportCase(
            id=f"CASE-SLA-BREACHED-{uuid.uuid4().hex[:6]}",
            customer_id="CUST1002",
            channel="email",
            subject="Overdue Case Requiring Escalation",
            priority="urgent",
            status=CaseStatus.INVESTIGATING.value,
            sla_deadline=now - datetime.timedelta(hours=4),
            created_at=now - datetime.timedelta(hours=5)
        )
        db.add(case_breached)
        db.commit()

        res = sla_engine.evaluate_case_sla(db, case_breached, auto_escalate=True)
        assert res.breach_status == SLABreachStatus.BREACHED
        assert res.is_breached is True
        assert res.auto_escalated is True

        # Verify case status updated to ESCALATED
        db.refresh(case_breached)
        assert case_breached.status == CaseStatus.ESCALATED.value

        # Verify EscalationTicket created
        esc = db.query(EscalationTicket).filter(EscalationTicket.case_id == case_breached.id).first()
        assert esc is not None
        assert esc.priority == "urgent"
        assert "SLA Breach" in esc.summary

        # Verify AuditLog created
        audit = db.query(AuditLog).filter(
            AuditLog.case_id == case_breached.id,
            AuditLog.action == "SLA_BREACH_AUTO_ESCALATED"
        ).first()
        assert audit is not None
    finally:
        db.close()


# =========================================================================
# 7. TEST FASTAPI API ENDPOINTS (OMNICHANNEL, PROACTIVE, SLA)
# =========================================================================

def test_api_omnichannel_channels(client):
    res = client.get("/api/omnichannel/channels")
    assert res.status_code == 200
    data = res.json()
    assert "channels" in data
    assert "email" in data["channels"]
    assert "whatsapp" in data["channels"]
    assert "web_chat" in data["channels"]
    assert "api" in data["channels"]
    assert "support_form" in data["channels"]


def test_api_omnichannel_inbound_webhook(client):
    payload = {
        "from": "webhook-tester@example.com",
        "subject": "Webhook Integration Test",
        "body": "Testing omnichannel HTTP webhook endpoint.",
        "message_id": "api-hook-msg-01"
    }
    res = client.post("/api/omnichannel/inbound/email", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["channel"] == "email"
    assert data["is_duplicate"] is False
    assert data["case_id"] is not None


def test_api_proactive_events_and_history(client):
    event_payload = {
        "event_id": "api-evt-001",
        "event_type": "product_issue",
        "customer_id": "CUST1001",
        "severity": "critical",
        "details": {"product_name": "NovaSound Pro", "issue_description": "Firmware audio distortion"},
        "source_system": "QAEWS"
    }
    res = client.post("/api/proactive/events", json=event_payload)
    assert res.status_code == 200
    data = res.json()
    assert data["event_type"] == "product_issue"
    assert data["case_created"] is True

    # Check history
    hist = client.get("/api/proactive/events")
    assert hist.status_code == 200
    assert hist.json()["count"] >= 1


def test_api_sla_policies_and_status(client):
    policies = client.get("/api/sla/policies")
    assert policies.status_code == 200
    assert "urgent" in policies.json()["policies"]

    status = client.get("/api/sla/status")
    assert status.status_code == 200
    data = status.json()
    assert "total_active_cases" in data
    assert "ok_count" in data
