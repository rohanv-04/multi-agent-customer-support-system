import uuid
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.database.database import init_db, SessionLocal
from backend.app.database.models import (
    SupportCase,
    CaseMessage,
    CaseEvent,
    AgentRun,
    AgentAction,
    AuditLog,
    Customer,
    Order
)
from backend.app.schemas.case import (
    CaseStatus,
    CasePriority,
    CaseCreate,
    CaseUpdate,
    CaseMessageCreate
)
from backend.app.services.case_service import (
    CaseService,
    InvalidStateTransitionError
)
from backend.app.api.chat import ChatRequest, chat_endpoint

client = TestClient(app)

@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    init_db()

@pytest.fixture
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def test_case_creation_and_audit(db_session):
    """Test 1: SupportCase creation, default SLA calculation, and event/audit logging."""
    req = CaseCreate(
        customer_id="CUST1002",
        subject="Delay inquiry for package",
        description="Customer states shipment NV-992014 has not arrived.",
        channel="web_chat",
        priority="high",
        initial_message="Where is my order ORD10002?"
    )
    case = CaseService.create_case(db_session, req)

    assert case.id.startswith("CASE-")
    assert case.status == CaseStatus.NEW.value
    assert case.priority == "high"
    assert case.customer_id == "CUST1002"
    assert case.organization_id == "ORG-NOVACART"
    assert case.sla_deadline is not None
    # High priority SLA is 4 hours from creation
    diff_hours = (case.sla_deadline - case.created_at).total_seconds() / 3600.0
    assert 3.9 <= diff_hours <= 4.1

    # Verify initial inbound message was saved
    assert len(case.messages) == 1
    assert case.messages[0].body == "Where is my order ORD10002?"
    assert case.messages[0].direction == "inbound"

    # Verify CASE_CREATED event was recorded
    created_events = [e for e in case.events if e.event_type == "case_created"]
    assert len(created_events) == 1
    assert "Delay inquiry for package" in created_events[0].summary

    # Verify AuditLog
    audits = db_session.query(AuditLog).filter(AuditLog.case_id == case.id).all()
    assert len(audits) >= 1
    assert audits[0].action == "CASE_CREATED"


def test_case_lifecycle_state_machine(db_session):
    """Test 2: Full valid lifecycle progression and illegal transition validation."""
    req = CaseCreate(
        customer_id="CUST1001",
        subject="Return item request",
        priority="medium"
    )
    case = CaseService.create_case(db_session, req)
    assert case.status == "NEW"

    # Step 1: NEW -> TRIAGING
    CaseService.transition_status(db_session, case, CaseStatus.TRIAGING.value, actor="Supervisor Agent")
    assert case.status == "TRIAGING"

    # Step 2: TRIAGING -> INVESTIGATING
    CaseService.transition_status(db_session, case, CaseStatus.INVESTIGATING.value, actor="Intent Agent")
    assert case.status == "INVESTIGATING"

    # Step 3: INVESTIGATING -> ACTION_PENDING
    CaseService.transition_status(db_session, case, CaseStatus.ACTION_PENDING.value, actor="Resolution Agent")
    assert case.status == "ACTION_PENDING"

    # Step 4: ACTION_PENDING -> VERIFYING
    CaseService.transition_status(db_session, case, CaseStatus.VERIFYING.value, actor="Critic Agent")
    assert case.status == "VERIFYING"

    # Step 5: VERIFYING -> RESOLVED
    CaseService.transition_status(db_session, case, CaseStatus.RESOLVED.value, actor="Supervisor Agent")
    assert case.status == "RESOLVED"
    assert case.resolved_at is not None

    # Step 6: RESOLVED -> CLOSED
    CaseService.transition_status(db_session, case, CaseStatus.CLOSED.value, actor="System")
    assert case.status == "CLOSED"

    # Step 7: Re-open CLOSED -> TRIAGING
    CaseService.transition_status(db_session, case, CaseStatus.TRIAGING.value, actor="Customer", reason="Customer reopened issue")
    assert case.status == "TRIAGING"

    # Step 8: Illegal transition test: TRIAGING directly to VERIFYING should raise InvalidStateTransitionError
    with pytest.raises(InvalidStateTransitionError):
        CaseService.transition_status(db_session, case, CaseStatus.VERIFYING.value)


def test_agent_runs_and_actions(db_session):
    """Test 3: Telemetry for AgentRuns and AgentActions within a Case."""
    req = CaseCreate(
        customer_id="CUST1003",
        subject="Warranty check",
        priority="low"
    )
    case = CaseService.create_case(db_session, req)

    # Start and complete an AgentRun
    run = CaseService.start_agent_run(db_session, case.id, "Retrieval Agent")
    assert run.status == "running"
    assert run.started_at is not None

    completed_run = CaseService.complete_agent_run(
        db_session,
        run.id,
        status="completed",
        output_summary="Retrieved 2 warranty policy sections",
        confidence=0.94
    )
    assert completed_run.status == "completed"
    assert completed_run.confidence == 0.94
    assert completed_run.ended_at is not None

    # Record an AgentAction
    action = CaseService.record_agent_action(
        db=db_session,
        case_id=case.id,
        agent_name="Resolution Agent",
        action_type="check_warranty_eligibility",
        status="completed",
        input_summary="Order ORD10003",
        output_summary="Item under 1-year hardware warranty",
        confidence=0.98,
        duration_ms=85
    )
    assert action.id is not None
    assert action.case_id == case.id
    assert action.action_type == "check_warranty_eligibility"


def test_case_timeline_aggregation(db_session):
    """Test 4: Unified chronological timeline compilation."""
    req = CaseCreate(
        customer_id="CUST1004",
        subject="Shipping address update",
        priority="medium",
        initial_message="I moved and need to update delivery address."
    )
    case = CaseService.create_case(db_session, req)

    CaseService.transition_status(db_session, case, CaseStatus.TRIAGING.value, actor="Supervisor Agent")
    CaseService.add_case_message(
        db_session,
        case.id,
        CaseMessageCreate(
            body="Address update verified and applied to Order ORD10004.",
            direction="outbound",
            sender_type="agent",
            sender_id="SupportOS AI"
        )
    )

    timeline = CaseService.get_case_timeline(db_session, case.id)
    assert len(timeline) >= 3  # message + case_created event + status_changed event + outbound message

    item_types = [item.item_type for item in timeline]
    assert "message" in item_types
    assert "event" in item_types


def test_cases_rest_api_endpoints():
    """Test 5: REST API endpoints for /api/cases."""
    # 1. POST /api/cases
    create_payload = {
        "customer_id": "CUST1002",
        "subject": "REST API Test Case",
        "description": "Testing FastAPI case endpoints",
        "channel": "api",
        "priority": "urgent",
        "initial_message": "Need urgent assistance with delayed order."
    }
    res = client.post("/api/cases", json=create_payload)
    assert res.status_code == 201
    case_data = res.json()
    case_id = case_data["id"]
    assert case_data["status"] == "NEW"
    assert case_data["priority"] == "urgent"

    # 2. GET /api/cases
    res = client.get("/api/cases?priority=urgent")
    assert res.status_code == 200
    cases_list = res.json()
    assert any(c["id"] == case_id for c in cases_list)

    # 3. GET /api/cases/{case_id}
    res = client.get(f"/api/cases/{case_id}")
    assert res.status_code == 200
    detail = res.json()
    assert detail["id"] == case_id
    assert detail["customer_name"] == "Elena Rostova"
    assert detail["message_count"] >= 1
    assert detail["sla_minutes_remaining"] is not None

    # 4. PATCH /api/cases/{case_id}
    patch_payload = {
        "status": "TRIAGING",
        "priority": "high",
        "reason": "Agent picked up case for investigation"
    }
    res = client.patch(f"/api/cases/{case_id}", json=patch_payload)
    assert res.status_code == 200
    updated = res.json()
    assert updated["status"] == "TRIAGING"
    assert updated["priority"] == "high"

    # 5. POST & GET /api/cases/{case_id}/messages
    msg_payload = {
        "body": "We are currently investigating your order with the carrier.",
        "direction": "outbound",
        "sender_type": "agent",
        "sender_id": "SupportOS AI"
    }
    res = client.post(f"/api/cases/{case_id}/messages", json=msg_payload)
    assert res.status_code == 201

    res = client.get(f"/api/cases/{case_id}/messages")
    assert res.status_code == 200
    messages = res.json()
    assert len(messages) == 2

    # 6. GET /api/cases/{case_id}/events
    res = client.get(f"/api/cases/{case_id}/events")
    assert res.status_code == 200
    events = res.json()
    assert len(events) >= 2  # created + status changed

    # 7. GET /api/cases/{case_id}/timeline
    res = client.get(f"/api/cases/{case_id}/timeline")
    assert res.status_code == 200
    timeline = res.json()
    assert len(timeline) >= 4


@pytest.mark.asyncio
async def test_chat_integration_with_case_engine():
    """Test 6: Integration of /api/chat with auto-provisioned SupportCase."""
    # Ensure test order ORD10002 is in Delayed status and clean
    db = SessionLocal()
    order = db.query(Order).filter(Order.order_id == "ORD10002").first()
    if order:
        order.status = "Delayed"
    db.commit()
    db.close()

    req = ChatRequest(
        message="What is the refund policy for delayed orders?",
        customer_id="CUST1002"
    )
    res = await chat_endpoint(req)

    # Verify chat returns case_id
    assert res.case_id is not None
    assert res.case_id.startswith("CASE-")
    assert res.confidence >= 0.75

    # Verify that the case in DB progressed to RESOLVED
    db = SessionLocal()
    case = db.query(SupportCase).filter(SupportCase.id == res.case_id).first()
    assert case is not None
    assert case.status in ["RESOLVED", "INVESTIGATING", "TRIAGING"]
    assert len(case.messages) >= 2  # user message + assistant response
    assert len(case.agent_runs) >= 1
    db.close()
