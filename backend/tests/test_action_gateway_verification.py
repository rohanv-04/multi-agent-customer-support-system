import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.app.main import app
from backend.app.database.database import init_db, SessionLocal
from backend.app.database.models import Order, Refund, Customer, SupportCase, AuditLog, CaseMessage, get_utc_now
from backend.app.schemas.case import CaseCreate, CaseStatus
from backend.app.schemas.action_gateway import ActionRequest, ActionResult, ActionStatus
from backend.app.services.case_service import CaseService
from backend.app.services.action_gateway import ActionGateway
from backend.app.agents.verification_agent import verify_action_execution


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    init_db()
    db = SessionLocal()
    db.query(Refund).delete()
    db.commit()
    db.close()


@pytest.fixture
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def test_action_gateway_auto_approve_execution_and_verification(db_session: Session):
    """Test 1: Low-risk action is auto-approved, executed, and independently verified against DB."""
    test_order_id = f"ORD-GW-{uuid.uuid4().hex[:6].upper()}"
    now = get_utc_now()

    # Seed test order in Processing state
    order = Order(
        order_id=test_order_id,
        customer_id="CUST1002",
        status="Delayed",
        items_json='[{"name": "Nova Pro Earbuds", "price": 149.00}]',
        total_amount=149.00,
        currency="USD",
        order_date=now,
        expected_delivery=now
    )
    db_session.add(order)
    db_session.commit()

    case = CaseService.create_case(
        db_session,
        CaseCreate(
            customer_id="CUST1002",
            subject=f"Refund request for {test_order_id}",
            priority="medium",
            channel="web_chat"
        )
    )

    request = ActionRequest(
        case_id=case.id,
        action_type="refund",
        requested_by="Resolution Agent",
        parameters={
            "order_id": test_order_id,
            "refund_amount": 149.00,
            "reason": "Shipment delayed beyond SLA buffer",
            "customer_id": "CUST1002"
        },
        justification="Verified SLA breach for active VIP customer",
        task_id=f"task-{uuid.uuid4().hex[:6]}",
        actor_role="agent"
    )

    result = ActionGateway.execute_action(db=db_session, request=request)

    assert result.status == ActionStatus.VERIFIED.value
    assert result.external_reference is not None
    assert result.verification is not None
    assert result.verification.verified is True
    assert result.verification.mismatch_detected is False

    # Verify actual DB state
    db_order = db_session.query(Order).filter(Order.order_id == test_order_id).first()
    assert db_order.status == "Refunded"

    db_refund = db_session.query(Refund).filter(Refund.order_id == test_order_id).first()
    assert db_refund is not None
    assert db_refund.refund_amount == 149.00

    # Verify audit log exists
    audit = db_session.query(AuditLog).filter(
        AuditLog.case_id == case.id,
        AuditLog.action == "REFUND_VERIFIED"
    ).first()
    assert audit is not None


def test_action_gateway_human_approval_required(db_session: Session):
    """Test 2: High-value refund (> $500 limit) halts execution and requires human review."""
    test_order_id = f"ORD-HV-{uuid.uuid4().hex[:6].upper()}"
    now = get_utc_now()

    order = Order(
        order_id=test_order_id,
        customer_id="CUST1002",
        status="Delayed",
        items_json='[{"name": "Ultra Workstation Server", "price": 1899.00}]',
        total_amount=1899.00,
        currency="USD",
        carrier="NovaExpress",
        order_date=now,
        expected_delivery=now
    )
    db_session.add(order)
    db_session.commit()

    case = CaseService.create_case(
        db_session,
        CaseCreate(
            customer_id="CUST1002",
            subject=f"High value claim for {test_order_id}",
            priority="high",
            channel="web_chat"
        )
    )

    request = ActionRequest(
        case_id=case.id,
        action_type="refund",
        requested_by="Resolution Agent",
        parameters={
            "order_id": test_order_id,
            "refund_amount": 1899.00,
            "reason": "Hardware defect",
            "customer_id": "CUST1002"
        },
        justification="High value claim requiring Finance sign-off",
        task_id=f"task-{uuid.uuid4().hex[:6]}",
        actor_role="agent"
    )

    result = ActionGateway.execute_action(db=db_session, request=request)

    assert result.status == ActionStatus.APPROVAL_PENDING.value
    assert result.result.get("approval_pending") is True
    assert "finance_specialist" in result.result.get("required_approval")

    # Ensure tool was NOT executed and order remains NOT refunded
    db_order = db_session.query(Order).filter(Order.order_id == test_order_id).first()
    assert db_order.status != "Refunded"

    # Ensure case transitioned to HUMAN_REVIEW
    db_case = CaseService.get_case(db_session, case.id)
    assert db_case.status == CaseStatus.HUMAN_REVIEW.value


def test_action_gateway_human_approval_resumption(db_session: Session):
    """Test 3: Action held in APPROVAL_PENDING executes successfully once approved by human supervisor."""
    test_order_id = f"ORD-APPR-{uuid.uuid4().hex[:6].upper()}"
    now = get_utc_now()

    order = Order(
        order_id=test_order_id,
        customer_id="CUST1002",
        status="Delayed",
        items_json='[{"name": "Premium Camera Kit", "price": 850.00}]',
        total_amount=850.00,
        currency="USD",
        carrier="NovaExpress",
        order_date=now,
        expected_delivery=now
    )
    db_session.add(order)
    db_session.commit()

    case = CaseService.create_case(
        db_session,
        CaseCreate(
            customer_id="CUST1002",
            subject=f"Supervisor approval test {test_order_id}",
            priority="high",
            channel="web_chat"
        )
    )

    request = ActionRequest(
        case_id=case.id,
        action_type="refund",
        requested_by="Finance Lead Alex",
        parameters={
            "order_id": test_order_id,
            "refund_amount": 850.00,
            "reason": "Approved by Finance Director under special exception",
            "customer_id": "CUST1002"
        },
        justification="Director authorized override",
        task_id=f"task-{uuid.uuid4().hex[:6]}",
        approval_required=False,
        actor_role="supervisor"
    )

    # Approve and execute
    result = ActionGateway.approve_action(db=db_session, request=request, approved_by="Supervisor Alex")

    assert result.status == ActionStatus.VERIFIED.value
    assert result.verification.verified is True

    db_order = db_session.query(Order).filter(Order.order_id == test_order_id).first()
    assert db_order.status == "Refunded"


def test_action_gateway_blocked_action(db_session: Session):
    """Test 4: Duplicate refund on an already refunded order is blocked."""
    test_order_id = f"ORD-BLOCKED-{uuid.uuid4().hex[:6].upper()}"
    now = get_utc_now()

    order = Order(
        order_id=test_order_id,
        customer_id="CUST1002",
        status="Refunded",
        items_json='[{"name": "Nova Phone", "price": 499.00}]',
        total_amount=499.00,
        currency="USD",
        carrier="NovaExpress",
        order_date=now,
        expected_delivery=now
    )
    db_session.add(order)

    # Add prior processed refund
    prior_ref = Refund(
        refund_id=f"REF-PRIOR-{uuid.uuid4().hex[:6].upper()}",
        order_id=test_order_id,
        customer_id="CUST1002",
        refund_amount=499.00,
        currency="USD",
        status="processed",
        reason="Prior refund",
        processed_at=now
    )
    db_session.add(prior_ref)
    db_session.commit()

    request = ActionRequest(
        case_id="CASE-BLOCKED-01",
        action_type="refund",
        requested_by="Resolution Agent",
        parameters={
            "order_id": test_order_id,
            "refund_amount": 499.00,
            "reason": "Second refund attempt",
            "customer_id": "CUST1002"
        },
        justification="Customer asked again",
        task_id=f"task-{uuid.uuid4().hex[:6]}",
        actor_role="agent"
    )

    result = ActionGateway.execute_action(db=db_session, request=request)

    assert result.status == ActionStatus.BLOCKED.value
    assert "duplicate" in result.error.lower() or "blocked" in result.error.lower()


def test_action_gateway_unauthorized_permission_blocked(db_session: Session):
    """Test 5: Unauthorized role attempting sensitive business mutation is blocked."""
    request = ActionRequest(
        case_id="CASE-UNAUTH-01",
        action_type="refund",
        requested_by="External Customer API",
        parameters={"order_id": "ORD10001", "refund_amount": 100.00},
        justification="Customer self-service direct trigger",
        actor_role="customer"  # Customers cannot execute financial refunds directly
    )

    result = ActionGateway.execute_action(db=db_session, request=request)

    assert result.status == ActionStatus.BLOCKED.value
    assert "Permission Denied" in result.error


def test_action_gateway_cancellation_and_verification(db_session: Session):
    """Test 6: Order cancellation passes gateway and is verified in database."""
    test_order_id = f"ORD-CAN-{uuid.uuid4().hex[:6].upper()}"
    now = get_utc_now()

    order = Order(
        order_id=test_order_id,
        customer_id="CUST1001",
        status="Processing",
        items_json='[{"name": "Wireless Mouse", "price": 29.99}]',
        total_amount=29.99,
        currency="USD",
        order_date=now,
        expected_delivery=now
    )
    db_session.add(order)
    db_session.commit()

    request = ActionRequest(
        case_id="CASE-CAN-01",
        action_type="cancellation",
        requested_by="Resolution Agent",
        parameters={"order_id": test_order_id, "reason": "Pre-dispatch customer cancellation"},
        actor_role="agent"
    )

    result = ActionGateway.execute_action(db=db_session, request=request)

    assert result.status == ActionStatus.VERIFIED.value
    assert result.verification.verified is True

    db_order = db_session.query(Order).filter(Order.order_id == test_order_id).first()
    assert db_order.status == "Cancelled"


def test_action_gateway_tool_failure_and_safe_retry_escalation(db_session: Session):
    """Test 7: Tool execution failure is caught by Verification Agent, retried, and escalates after max retries."""
    test_order_id = f"ORD-FAIL-{uuid.uuid4().hex[:6].upper()}"

    case = CaseService.create_case(
        db_session,
        CaseCreate(
            customer_id="CUST1001",
            subject=f"Failure recovery test {test_order_id}",
            priority="high",
            channel="web_chat"
        )
    )

    request = ActionRequest(
        case_id=case.id,
        action_type="refund",
        requested_by="Resolution Agent",
        parameters={"order_id": test_order_id, "refund_amount": 50.00, "reason": "Failure test"},
        actor_role="agent"
    )

    # Trigger with simulated tool failure
    result = ActionGateway.execute_action(
        db=db_session,
        request=request,
        simulate_tool_failure=True,
        max_retries=2
    )

    assert result.status == ActionStatus.FAILED.value
    assert result.verification.verified is False
    assert result.verification.should_escalate is True
    assert result.verification.retry_count >= 2

    # Verify case transitioned to ESCALATED
    db_case = CaseService.get_case(db_session, case.id)
    assert db_case.status == CaseStatus.ESCALATED.value


def test_action_gateway_state_mismatch_detection(db_session: Session):
    """Test 8: Verification detects state mismatch when tool returns success but DB state was not mutated."""
    test_order_id = f"ORD-MISMATCH-{uuid.uuid4().hex[:6].upper()}"
    now = get_utc_now()

    # Order stays in Processing
    order = Order(
        order_id=test_order_id,
        customer_id="CUST1001",
        status="Processing",
        items_json='[{"name": "Keyboard", "price": 49.99}]',
        total_amount=49.99,
        currency="USD",
        order_date=now,
        expected_delivery=now
    )
    db_session.add(order)
    db_session.commit()

    request = ActionRequest(
        case_id="CASE-MISMATCH-01",
        action_type="cancellation",
        requested_by="Resolution Agent",
        parameters={"order_id": test_order_id, "reason": "Cancellation test"},
        actor_role="agent"
    )

    # Simulate state mismatch where tool claims success but DB state wasn't updated
    result = ActionGateway.execute_action(
        db=db_session,
        request=request,
        simulate_state_mismatch=True
    )

    assert result.status == ActionStatus.FAILED.value
    assert result.verification.verified is False
    assert result.verification.mismatch_detected is True
    assert "State mismatch" in result.verification.mismatch_details
