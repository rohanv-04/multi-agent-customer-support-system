import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.database.database import init_db, SessionLocal
from backend.app.database.models import SupportCase, Refund, Customer, Order
from backend.app.schemas.case import CaseCreate, CaseStatus
from backend.app.services.case_service import CaseService
from backend.app.services.customer_intelligence_service import CustomerIntelligenceService
from backend.app.agents.intake_agent import run_intake_agent
from backend.app.agents.investigation_agent import run_investigation_agent
from backend.app.agents.policy_agent import run_policy_agent
from backend.app.agents.decision_agent import run_decision_engine
from backend.app.agents.risk_agent import run_risk_agent
from backend.app.schemas.decision import DecisionType
from backend.app.schemas.risk import RiskDecision, RiskLevel
from backend.app.graph.workflow import support_graph
from backend.app.graph.state import AgenticSupportState

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


def test_valid_policy_evaluation(db_session):
    """Test 1: Valid policy evaluation with verified conditions and evidence."""
    intake = run_intake_agent("My order ORD10002 is severely delayed by 4 days, refund me", customer_id="CUST1002")
    c360 = CustomerIntelligenceService.get_customer_360(db_session, "CUST1002")
    case = CaseService.create_case(
        db_session,
        CaseCreate(
            customer_id="CUST1002",
            subject="Delayed order ORD10002",
            priority="high",
            channel="web_chat"
        )
    )
    inv = run_investigation_agent(db_session, case, c360, intake)

    policy_res = run_policy_agent(
        intent_data=intake,
        customer_360=c360,
        investigation=inv
    )

    assert policy_res.applicable is True
    assert policy_res.eligibility is True
    assert policy_res.requires_human_review is False
    assert policy_res.confidence >= 0.90
    assert len(policy_res.conditions) >= 1
    assert len(policy_res.evidence) >= 1
    condition_names = [c.name for c in policy_res.conditions]
    assert "severe_delay_threshold" in condition_names


def test_conflicting_policy_detection(db_session):
    """Test 2: Conflicting policy clauses flag uncertainty and mandate human review."""
    intake = run_intake_agent("I dispute and have a conflict with your standard warranty policy on order ORD10002", customer_id="CUST1002")
    c360 = CustomerIntelligenceService.get_customer_360(db_session, "CUST1002")

    policy_res = run_policy_agent(
        intent_data=intake,
        customer_360=c360,
        investigation=None
    )

    assert policy_res.requires_human_review is True
    assert len(policy_res.unresolved_conflicts) >= 1
    assert policy_res.confidence < 0.90


def test_missing_policy_handling(db_session):
    """Test 3: Missing/unverifiable policy domain triggers uncertainty and human review."""
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
    assert len(policy_res.unresolved_conflicts) >= 1
    assert policy_res.confidence <= 0.50


def test_high_value_refund_risk_evaluation(db_session):
    """Test 4: High-value refund (> $500 limit) requires Finance Specialist and HUMAN_REVIEW."""
    intake = run_intake_agent("Refund my luxury server order ORD-HV-10002", customer_id="CUST1002")
    c360 = CustomerIntelligenceService.get_customer_360(db_session, "CUST1002")

    # Construct high value decision ($1,499.00 USD)
    from backend.app.schemas.decision import DecisionResult, DecisionType
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
    assert any("exceeds" in r.lower() for r in risk_res.reasons)


def test_duplicate_refund_prevention(db_session):
    """Test 5: Duplicate refund attempt on an already-refunded order is BLOCKED with critical risk."""
    import uuid
    test_order_id = f"ORD-DUP-{uuid.uuid4().hex[:6]}"
    ref = Refund(
        refund_id=f"REF-DUP-{uuid.uuid4().hex[:6]}",
        order_id=test_order_id,
        customer_id="CUST1002",
        refund_amount=499.00,
        currency="USD",
        status="processed",
        reason="Prior delay refund",
        refund_method="Original Payment Method"
    )
    db_session.add(ref)
    db_session.commit()

    from backend.app.schemas.decision import DecisionResult, DecisionType
    decision = DecisionResult(
        decision_type=DecisionType.REFUND,
        target_entity_id=test_order_id,
        parameters={
            "order_id": test_order_id,
            "refund_amount": 499.00,
            "currency": "USD",
            "reason": "Second refund request"
        },
        rationale="Customer requesting another refund on duplicate order",
        recommended_action_name="process_refund"
    )

    c360 = CustomerIntelligenceService.get_customer_360(db_session, "CUST1002")

    risk_res = run_risk_agent(
        db=db_session,
        decision=decision,
        customer_360=c360
    )

    assert risk_res.decision == RiskDecision.BLOCK
    assert risk_res.risk_level == RiskLevel.CRITICAL
    assert any("duplicate" in r.lower() for r in risk_res.reasons)
    factor_names = [f.factor_name for f in risk_res.factors]
    assert "duplicate_transaction_prevention" in factor_names


def test_suspicious_account_risk(db_session):
    """Test 6: Suspicious or Suspended account is BLOCKED for automated actions."""
    from backend.app.schemas.decision import DecisionResult, DecisionType
    decision = DecisionResult(
        decision_type=DecisionType.REFUND,
        target_entity_id="ORD10001",
        parameters={"order_id": "ORD10001", "refund_amount": 100.00},
        rationale="Standard refund request",
        recommended_action_name="process_refund"
    )

    risk_res = run_risk_agent(
        db=db_session,
        decision=decision,
        customer_360=None,
        suspicious_override=True
    )

    assert risk_res.decision == RiskDecision.BLOCK
    assert risk_res.risk_level == RiskLevel.CRITICAL
    assert risk_res.required_approval == "fraud_operations"


def test_case_state_transitions_for_human_review(db_session):
    """Test 7: SupportCase transitions to HUMAN_REVIEW and DECISION_PENDING."""
    case = CaseService.create_case(
        db_session,
        CaseCreate(
            customer_id="CUST1001",
            subject="Special review required",
            priority="high",
            channel="web_chat"
        )
    )

    # NEW -> TRIAGING -> INVESTIGATING -> DECISION_PENDING -> HUMAN_REVIEW
    CaseService.transition_status(db_session, case, CaseStatus.TRIAGING.value, actor="Supervisor")
    CaseService.transition_status(db_session, case, CaseStatus.INVESTIGATING.value, actor="Intent Agent")
    CaseService.transition_status(db_session, case, CaseStatus.DECISION_PENDING.value, actor="Decision Engine")
    assert case.status == "DECISION_PENDING"

    CaseService.transition_status(
        db_session,
        case,
        CaseStatus.HUMAN_REVIEW.value,
        actor="Risk Engine",
        reason="High value transaction requires supervisor approval"
    )
    assert case.status == "HUMAN_REVIEW"

    # Verify transition from HUMAN_REVIEW -> ACTION_PENDING -> RESOLVED
    CaseService.transition_status(db_session, case, CaseStatus.ACTION_PENDING.value, actor="Human Lead", reason="Approved by supervisor")
    assert case.status == "ACTION_PENDING"

    CaseService.transition_status(db_session, case, CaseStatus.RESOLVED.value, actor="Resolution Agent", reason="Completed")
    assert case.status == "RESOLVED"
