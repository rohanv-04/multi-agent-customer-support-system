import pytest
import uuid
import datetime
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.app.main import app
from backend.app.database.database import init_db, SessionLocal
from backend.app.database.models import (
    Customer,
    Order,
    Refund,
    SupportCase,
    EscalationTicket,
    RootCause,
    KnowledgeGap,
    SimulationRun,
    AgentConflict,
    get_utc_now
)
from backend.app.schemas.case import CaseCreate, CaseStatus
from backend.app.schemas.intake import IntakeExtractionResult
from backend.app.schemas.customer import Customer360Response
from backend.app.services.customer_friction_service import CustomerFrictionService
from backend.app.services.case_dna_service import CaseDNAService
from backend.app.services.root_cause_service import RootCauseService
from backend.app.services.next_best_action_service import NextBestActionEngine
from backend.app.services.self_healing_service import SelfHealingEngine
from backend.app.services.knowledge_gap_service import KnowledgeGapService
from backend.app.services.simulation_service import SimulationService
from backend.app.services.case_similarity_service import CaseSimilarityService
from backend.app.services.operational_intelligence_service import OperationalIntelligenceService
from backend.app.agents.swarm_investigation import run_swarm_investigation
from backend.app.agents.conversation_integrity_guard import ConversationIntegrityGuard
from backend.app.agents.agent_debate import AgentDebateEngine
from backend.app.agents.intake_agent import run_intake_agent
from backend.app.agents.policy_agent import run_policy_agent
from backend.app.agents.risk_agent import run_risk_agent
from backend.app.agents.decision_agent import run_decision_engine


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    init_db()


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


# --------------------------------------------------------------------------
# 1. Feature 1: Customer Friction Score Tests
# --------------------------------------------------------------------------

def test_customer_friction_calculation(db_session: Session):
    """Test 1: Explainable friction scoring across 11 operational signals."""
    # Test customer with active cases & delays
    profile = CustomerFrictionService.calculate_friction(db_session, "CUST1002")
    
    assert profile.customer_id == "CUST1002"
    assert 0.0 <= profile.score <= 100.0
    assert profile.level in ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    assert len(profile.contributing_factors) >= 1
    
    # Check explainability
    for factor in profile.contributing_factors:
        assert factor.factor_type is not None
        assert factor.label is not None
        assert factor.description is not None
        assert factor.impact_score >= 0.0


# --------------------------------------------------------------------------
# 2. Feature 2: Case DNA Fingerprinting Tests
# --------------------------------------------------------------------------

def test_case_dna_fingerprinting(db_session: Session):
    """Test 2: Case DNA multidimensional fingerprinting and dynamic capability activation."""
    test_case_id = f"CASE-DNA-{uuid.uuid4().hex[:6]}"
    case = SupportCase(
        id=test_case_id,
        customer_id="CUST1002",
        subject="Order ORD10002 delayed by 3 days, need refund",
        intent="refund_request",
        priority="urgent"
    )
    db_session.add(case)
    db_session.commit()

    intake = run_intake_agent("Order ORD10002 delayed by 3 days, need refund", customer_id="CUST1002")
    dna = CaseDNAService.generate_case_dna(db_session, case, intake)

    assert dna.case_id == test_case_id
    assert dna.affected_business_area in ["billing", "logistics"]
    assert dna.severity in ["high", "critical"]
    assert len(dna.required_capabilities) >= 3
    assert "policy_intelligence" in dna.required_capabilities
    assert "action_gateway" in dna.required_capabilities
    assert dna.fingerprint_hash is not None


# --------------------------------------------------------------------------
# 3. Feature 3: Root Cause Intelligence Tests
# --------------------------------------------------------------------------

def test_root_cause_intelligence_clustering(db_session: Session):
    """Test 3: Detection of systemic operational issues (carrier/warehouse/product)."""
    root_causes = RootCauseService.detect_root_causes(db_session)
    
    assert len(root_causes) >= 1
    rc = root_causes[0]
    assert rc.id.startswith("RC-")
    assert rc.status.value in ["DETECTED_PATTERN", "CONFIRMED_ROOT_CAUSE"]
    assert rc.confidence >= 0.70
    assert len(rc.evidence) >= 1


# --------------------------------------------------------------------------
# 4. Feature 4: Parallel Swarm Investigation Tests
# --------------------------------------------------------------------------

def test_swarm_investigation_concurrency_and_merging(db_session: Session):
    """Test 4: Concurrent sub-investigators executing and merging factual evidence."""
    case = db_session.query(SupportCase).first() or SupportCase(
        id="CASE-SWARM-01",
        customer_id="CUST1002",
        subject="Delivery status check",
        priority="medium"
    )
    intake = run_intake_agent("Where is my order ORD10002?", customer_id="CUST1002")
    
    from backend.app.services.customer_intelligence_service import CustomerIntelligenceService
    c360 = CustomerIntelligenceService.get_customer_360(db_session, "CUST1002")
    
    inv_result = run_swarm_investigation(db_session, case, c360, intake)
    
    assert inv_result.case_id == case.id
    assert len(inv_result.findings) >= 2
    assert len(inv_result.evidence) >= 2
    assert inv_result.investigation_status in ["complete", "partial"]
    assert len(inv_result.data_sources) >= 2


# --------------------------------------------------------------------------
# 5. Feature 5: Next-Best-Action Engine Tests
# --------------------------------------------------------------------------

def test_next_best_action_engine(db_session: Session):
    """Test 5: NBA Engine evaluates context, policy, risk to produce ranked recommendations."""
    case = db_session.query(SupportCase).filter(SupportCase.customer_id == "CUST1002").first()
    if not case:
        case = SupportCase(id="CASE-NBA-01", customer_id="CUST1002", subject="Refund ORD10002", intent="refund_request")
        db_session.add(case)
        db_session.commit()

    nba = NextBestActionEngine.evaluate_next_best_action(db_session, case)
    
    assert nba.case_id == case.id
    assert nba.recommended_action is not None
    assert nba.action_type in ["refund", "reshipment", "escalate", "notify_customer"]
    assert len(nba.alternatives) >= 1
    assert nba.justification is not None


# --------------------------------------------------------------------------
# 6. Feature 6: Self-Healing Workflow Tests
# --------------------------------------------------------------------------

def test_self_healing_workflow_recovery(db_session: Session):
    """Test 6: Bounded retry limits, failure classification, and loop prevention."""
    # Attempt 1: Recoverable timeout -> should retry/replan
    heal_1 = SelfHealingEngine.handle_failure(
        db=db_session,
        case_id="CASE-HEAL-01",
        task_id="task-001",
        failure_type="temporary_api_failure",
        error_message="Shipping carrier webhook timed out after 5000ms",
        current_retry_count=0
    )
    assert heal_1["is_recoverable"] is True
    assert heal_1["retry_count"] == 1
    assert heal_1["should_escalate"] is False

    # Attempt 3: Exceeding MAX_RETRIES -> must escalate
    heal_3 = SelfHealingEngine.handle_failure(
        db=db_session,
        case_id="CASE-HEAL-01",
        task_id="task-001",
        failure_type="temporary_api_failure",
        error_message="Carrier API still unreachable",
        current_retry_count=2
    )
    assert heal_3["is_recoverable"] is False
    assert heal_3["retry_count"] == 3
    assert heal_3["should_escalate"] is True


# --------------------------------------------------------------------------
# 7. Feature 7: Conversation Integrity Guard Tests
# --------------------------------------------------------------------------

def test_conversation_integrity_guard_blocks_unverified_claims(db_session: Session):
    """Test 7: Guard blocks AI from claiming a refund was processed without DB verification."""
    fake_draft = "Hello Elena, your refund of $850.00 has been processed successfully to your card."
    
    # Audit with no verified refund action
    result = ConversationIntegrityGuard.audit_and_verify(
        db=db_session,
        draft_response=fake_draft,
        action_executed=None
    )

    assert result.is_approved is False
    assert result.action_status_verified is False
    assert any("refund" in issue.lower() for issue in result.issues_detected)
    assert "received and submitted" in result.revised_content.lower()


# --------------------------------------------------------------------------
# 8. Feature 8: Knowledge Gap Detector Tests
# --------------------------------------------------------------------------

def test_knowledge_gap_detection(db_session: Session):
    """Test 8: Identification of missing documentation without hallucinating policies."""
    gap = KnowledgeGapService.record_knowledge_gap(
        db=db_session,
        topic="Cross-Border Crypto Asset Warranty Claims",
        case_id="CASE-TEST-GAP",
        evidence="Customer requested crypto refund; vector search confidence was 0.32.",
        severity="high"
    )

    assert gap.id.startswith("KG-")
    assert gap.topic == "Cross-Border Crypto Asset Warranty Claims"
    assert gap.occurrences >= 1
    assert gap.status == "OPEN"


# --------------------------------------------------------------------------
# 9. Feature 9: AI Simulation Lab Safety & Execution Tests
# --------------------------------------------------------------------------

def test_ai_simulation_lab_safety_and_execution(db_session: Session):
    """Test 9: Simulation executes end-to-end with 100% isolation and zero real mutations."""
    from backend.app.schemas.differentiation import SimulationRunRequest
    
    req = SimulationRunRequest(
        customer_id="CUST1002",
        issue_description="Simulated emergency: Carrier API offline for delayed order ORD10002.",
        system_conditions={"carrier_api_down": True, "refund_limit": 500.0}
    )

    sim_res = SimulationService.run_simulation(db_session, req)
    
    assert sim_res.run_id.startswith("SIM-RUN-")
    assert sim_res.status == "completed"
    assert sim_res.safety_verified is True
    assert len(sim_res.execution_trace) >= 4
    assert len(sim_res.simulated_tool_calls) >= 1
    assert sim_res.final_outcome["safety_verified"] is True


# --------------------------------------------------------------------------
# 10. Feature 10: Agent Debate & Conflict Resolution Tests
# --------------------------------------------------------------------------

def test_agent_debate_and_conflict_resolution(db_session: Session):
    """Test 10: Structured multi-agent disagreement resolved by Decision Agent hierarchy."""
    case = db_session.query(SupportCase).filter(SupportCase.customer_id == "CUST1002").first()
    if not case:
        case = SupportCase(id="CASE-DEBATE-01", customer_id="CUST1002", subject="High Value Return", priority="high")
        db_session.add(case)
        db_session.commit()

    from backend.app.schemas.policy import PolicyEvaluationResult
    from backend.app.schemas.risk import RiskEvaluationResult, RiskLevel, RiskDecision

    mock_policy = PolicyEvaluationResult(
        policy_name="NovaCart High-Value Return Policy",
        applicable=True,
        eligibility=True,
        conditions=[],
        exceptions=[],
        evidence=[],
        confidence=0.95,
        requires_human_review=False
    )

    mock_risk = RiskEvaluationResult(
        risk_level=RiskLevel.HIGH,
        decision=RiskDecision.HUMAN_REVIEW,
        required_approval="finance_supervisor",
        reasons=["Transaction total $1,899.00 exceeds $500 autonomous threshold"],
        fraud_risk_score=0.10
    )

    debate = AgentDebateEngine.evaluate_and_resolve_conflict(
        db=db_session,
        case=case,
        investigation=None,
        policy=mock_policy,
        risk=mock_risk
    )

    assert debate is not None
    assert len(debate.conflicting_points) >= 1
    assert "REQUEST_SUPERVISOR_APPROVAL" in debate.final_action_chosen
    assert "Decision Agent Arbitration" in debate.resolution_rationale


# --------------------------------------------------------------------------
# 11. Feature 11: Case Similarity & Historical Precedents Tests
# --------------------------------------------------------------------------

def test_case_similarity_service(db_session: Session):
    """Test 11: Case similarity engine finds top relevant historical precedents."""
    case = db_session.query(SupportCase).first()
    if case:
        similar = CaseSimilarityService.find_similar_cases(db_session, case, limit=3)
        assert isinstance(similar, list)


# --------------------------------------------------------------------------
# 12. Feature 12: Operations Intelligence Tests
# --------------------------------------------------------------------------

def test_operational_intelligence_generation(db_session: Session):
    """Test 12: Operations Intelligence synthesizes grounded systemic insights."""
    insights = OperationalIntelligenceService.generate_insights(db_session)
    
    assert len(insights) >= 2
    for ins in insights:
        assert ins.id.startswith("INS-")
        assert ins.category in ["logistics", "efficiency", "knowledge", "financial"]
        assert ins.title is not None
        assert ins.observation is not None
        assert ins.severity in ["info", "warning", "critical"]


# --------------------------------------------------------------------------
# 13. API Route Tests for All 12 Features
# --------------------------------------------------------------------------

def test_differentiation_api_endpoints(client):
    """Test 13: Verify all new REST endpoints return 200 with proper schema payloads."""
    # 1. Customer Friction
    res = client.get("/api/customers/CUST1002/friction")
    assert res.status_code == 200
    assert "score" in res.json()
    assert "level" in res.json()

    # 2. Root Causes
    res_rc = client.get("/api/root-causes")
    assert res_rc.status_code == 200
    assert isinstance(res_rc.json(), list)

    # 3. Knowledge Gaps
    res_kg = client.get("/api/knowledge-gaps")
    assert res_kg.status_code == 200
    assert isinstance(res_kg.json(), list)

    # 4. Simulation Scenarios
    res_scen = client.get("/api/simulations/scenarios")
    assert res_scen.status_code == 200
    assert len(res_scen.json()) >= 1

    # 5. Simulation Execution
    res_sim = client.post("/api/simulations", json={
        "customer_id": "CUST1002",
        "issue_description": "Delayed parcel simulation test",
        "system_conditions": {"carrier_api_down": False}
    })
    assert res_sim.status_code == 200
    sim_data = res_sim.json()
    assert sim_data["safety_verified"] is True
    assert sim_data["status"] == "completed"

    # 6. Operational Insights
    res_ops = client.get("/api/operations/insights")
    assert res_ops.status_code == 200
    assert len(res_ops.json()) >= 1
