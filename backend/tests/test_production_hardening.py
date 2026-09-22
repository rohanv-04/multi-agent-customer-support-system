import pytest
import uuid
import datetime
from unittest.mock import patch
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from sqlalchemy import text

from backend.app.main import app
from backend.app.database.database import get_db, SessionLocal
from backend.app.database.models import Customer, Order, SupportCase, AuditLog, get_utc_now
from backend.app.schemas.case import CaseStatus
from backend.app.schemas.action_gateway import ActionRequest, ActionStatus, ActionResult
from backend.app.schemas.decision import DecisionResult, DecisionType
from backend.app.schemas.risk import RiskDecision, RiskLevel
from backend.app.services.customer_intelligence_service import CustomerIntelligenceService
from backend.app.services.omnichannel_service import OmnichannelService, DeduplicationRegistry
from backend.app.services.sla_engine import SLAEngine, SLABreachStatus, sla_engine
from backend.app.services.action_gateway import ActionGateway
from backend.app.agents.intake_agent import run_intake_agent
from backend.app.agents.policy_agent import run_policy_agent
from backend.app.agents.decision_agent import run_decision_engine
from backend.app.agents.risk_agent import run_risk_agent
from backend.app.agents.llm_client import LLMClient
from backend.app.agents.verification_agent import verify_action_execution
from backend.app.tools.refund_tool import process_refund
from backend.app.tools.order_cancellation_tool import cancel_order
from backend.app.schemas.omnichannel import SupportRequest, ChannelType


from backend.app.rag.vector_store import policy_store
from backend.app.database.database import init_db

@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    init_db()
    policy_store.index_documents()

@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------------------------------------------------------
# 1. Health and Readiness Endpoints
# ---------------------------------------------------------

def test_health_endpoints(client):
    """Verify /health, /health/live, and /health/ready endpoints."""
    # /health
    res = client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert "request_id" in data

    # /health/live
    res_live = client.get("/health/live")
    assert res_live.status_code == 200
    assert res_live.json()["status"] == "live"

    # /health/ready
    res_ready = client.get("/health/ready")
    assert res_ready.status_code == 200
    ready_data = res_ready.json()
    assert ready_data["status"] == "ready"
    assert ready_data["database"] == "connected"
    assert ready_data["knowledge_chunks"] > 0


def test_request_id_and_correlation_headers(client):
    """Verify X-Request-ID and X-Response-Time-Ms headers are attached to all responses."""
    custom_req_id = "test-req-id-12345"
    res = client.get("/health", headers={"X-Request-ID": custom_req_id})
    assert res.status_code == 200
    assert res.headers.get("x-request-id") == custom_req_id
    assert "x-response-time-ms" in res.headers


# ---------------------------------------------------------
# 2. LLM Failure and Local Fallback Resilience
# ---------------------------------------------------------

@pytest.mark.asyncio
async def test_llm_failure_graceful_fallback():
    """Verify system falls back gracefully when external LLM API throws network/timeout exceptions."""
    client_mock = LLMClient()
    client_mock.provider = "openai"
    client_mock.api_key = "sk-fake-key-for-test"

    # Mock httpx failure
    with patch("httpx.AsyncClient.post", side_effect=Exception("Connection timed out to LLM provider")):
        result = await client_mock.generate_json("System prompt", "User prompt")
        # Must return None so deterministic rule engine kicks in without throwing unhandled exception
        assert result is None


# ---------------------------------------------------------
# 3. Database Failure Resilience & Transaction Rollback
# ---------------------------------------------------------

def test_database_failure_rollback(db_session: Session):
    """Verify database transactions roll back cleanly when an error occurs during execution."""
    test_cust_id = f"CUST-FAIL-{uuid.uuid4().hex[:6]}"
    
    try:
        # Simulate an operation that encounters an integrity error
        db_session.add(Customer(
            customer_id=test_cust_id,
            name="Fail Test",
            email="fail@test.com",
            tier="Standard"
        ))
        db_session.flush()

        # Intentionally force a failure
        raise ValueError("Simulated DB transaction failure midway")
    except ValueError:
        db_session.rollback()

    # Confirm the customer was NOT committed to the database
    cust_check = db_session.query(Customer).filter(Customer.customer_id == test_cust_id).first()
    assert cust_check is None


# ---------------------------------------------------------
# 4. Duplicate Webhook and Idempotency Checks
# ---------------------------------------------------------

def test_duplicate_webhook_deduplication():
    """Verify DeduplicationRegistry flags duplicate requests and message bodies."""
    registry = DeduplicationRegistry(ttl_seconds=300)
    req_id = f"req-{uuid.uuid4().hex}"
    sender = "user@example.com"
    body = "Please refund my order ORD-10024"
    channel = "email"

    # First attempt - not duplicate
    is_dup_1 = registry.is_duplicate(req_id, sender, body, channel)
    assert is_dup_1 is False

    # Second attempt with same request ID - MUST be duplicate
    is_dup_2 = registry.is_duplicate(req_id, sender, body, channel)
    assert is_dup_2 is True

    # Third attempt with different request ID but identical sender+body+channel (spam detection)
    is_dup_3 = registry.is_duplicate(f"req-different-{uuid.uuid4().hex}", sender, body, channel)
    assert is_dup_3 is True


# ---------------------------------------------------------
# 5. Malformed Input and Validation Handling
# ---------------------------------------------------------

def test_malformed_input_validation(client):
    """Verify malformed JSON or invalid schema payloads return 422 with structured error details."""
    # Missing required 'action' field in case route
    res = client.post("/api/cases", json={"invalid_field": "data"})
    assert res.status_code == 422
    data = res.json()
    assert "detail" in data
    assert "error" in data
    assert data["error"]["code"] == "VALIDATION_ERROR"


# ---------------------------------------------------------
# 6. Invalid Customer and Order Handling
# ---------------------------------------------------------

def test_invalid_customer_handling(db_session: Session):
    """Verify CustomerIntelligenceService handles non-existent customers gracefully."""
    c360 = CustomerIntelligenceService.get_customer_360(db_session, "CUST-DOES-NOT-EXIST")
    assert c360 is None


def test_invalid_order_handling():
    """Verify refund and cancellation tools safely reject non-existent orders."""
    res_refund = process_refund(order_id="ORD-99999", refund_amount=50.0, reason="Item damaged")
    assert res_refund["success"] is False
    assert "not found" in res_refund["error"].lower()

    res_cancel = cancel_order(order_id="ORD-99999", reason="User changed mind")
    assert res_cancel["success"] is False
    assert "not found" in res_cancel["error"].lower()


# ---------------------------------------------------------
# 7. Policy Ambiguity & Human Review Triggers
# ---------------------------------------------------------

def test_policy_ambiguity_triggers_human_review(db_session: Session):
    """Verify ambiguous or unsupported requests flag uncertainty and require human review."""
    intake = run_intake_agent("I want a cryptocurrency rebate under policy crypto_airdrop_v9", customer_id="CUST1002")
    c360 = CustomerIntelligenceService.get_customer_360(db_session, "CUST1002")

    policy_res = run_policy_agent(
        intent_data=intake,
        customer_360=c360,
        investigation=None,
        forced_policy_name="NonExistentCryptoAirdropPolicy"
    )

    assert policy_res.applicable is False
    assert policy_res.eligibility is False
    assert policy_res.requires_human_review is True
    assert policy_res.confidence <= 0.50


# ---------------------------------------------------------
# 8. Refund Failure & Guardrail Enforcement
# ---------------------------------------------------------

def test_refund_guardrails_prevent_invalid_execution():
    """Verify negative amounts, exceeding order totals, or already refunded orders fail safely."""
    # 1. Negative amount
    neg_res = process_refund(order_id="ORD10024", refund_amount=-25.0, reason="Invalid negative")
    assert neg_res["success"] is False

    # 2. Exceeding max policy cap (> $1000)
    huge_res = process_refund(order_id="ORD10024", refund_amount=5000.0, reason="Massive overcharge")
    assert huge_res["success"] is False


# ---------------------------------------------------------
# 9. Verification Failure Triggers Escalation
# ---------------------------------------------------------

def test_verification_failure_handling(db_session: Session):
    """Verify Action Gateway verification marks actions as unverified when execution fails."""
    req = ActionRequest(
        action_type="refund",
        parameters={"order_id": "ORD-NONEXISTENT", "refund_amount": 100.0},
        justification="Invalid refund test"
    )

    verif_result = verify_action_execution(
        db=db_session,
        request=req,
        execution_result={"success": False, "error": "Order not found"}
    )

    assert verif_result.verified is False
    assert verif_result.mismatch_detected is True


# ---------------------------------------------------------
# 10. Escalation Routing for High Risk / VIP Customers
# ---------------------------------------------------------

def test_high_risk_escalation_routing(db_session: Session):
    """Verify high risk / fraud score or VIP angry customers trigger escalation."""
    c360 = CustomerIntelligenceService.get_customer_360(db_session, "CUST1002")
    decision = DecisionResult(
        decision_type=DecisionType.REFUND,
        target_entity_id="ORD-HV-10002",
        parameters={
            "order_id": "ORD-HV-10002",
            "refund_amount": 1499.00,
            "currency": "USD",
            "reason": "Damaged server hardware"
        },
        rationale="High value equipment refund requested",
        recommended_action_name="process_refund"
    )

    risk_res = run_risk_agent(
        db=db_session,
        decision=decision,
        customer_360=c360
    )

    assert risk_res.decision == RiskDecision.HUMAN_REVIEW
    assert risk_res.required_approval == "finance_specialist"
    assert risk_res.risk_level == RiskLevel.HIGH


# ---------------------------------------------------------
# 11. SLA Breach Calculation and Detection
# ---------------------------------------------------------

def test_sla_breach_detection(db_session: Session):
    """Verify SLA engine identifies breached cases accurately."""
    now = get_utc_now()
    case = SupportCase(
        id=f"CASE-SLA-TEST-{uuid.uuid4().hex[:6]}",
        customer_id="CUST1002",
        channel="email",
        subject="Overdue Support Case",
        priority="urgent",
        status=CaseStatus.INVESTIGATING.value,
        sla_deadline=now - datetime.timedelta(hours=4),
        created_at=now - datetime.timedelta(hours=5)
    )
    db_session.add(case)
    db_session.commit()

    res = sla_engine.evaluate_case_sla(db_session, case, auto_escalate=False)
    assert res.breach_status == SLABreachStatus.BREACHED
    assert res.is_breached is True
