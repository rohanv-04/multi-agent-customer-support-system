import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.database.database import init_db, SessionLocal
from backend.app.database.models import SupportCase, AgentAction, CaseEvent
from backend.app.schemas.case import CaseCreate
from backend.app.services.case_service import CaseService
from backend.app.services.customer_intelligence_service import CustomerIntelligenceService
from backend.app.agents.intake_agent import run_intake_agent
from backend.app.agents.investigation_agent import run_investigation_agent
from backend.app.schemas.investigation import InvestigationResult
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


def test_intake_agent_structured_extraction():
    """Test Intake Agent extracts typed Pydantic models with all mandatory fields."""
    result = run_intake_agent(
        user_goal="My headphones order ORD10002 has been delayed for 4 days! This is ridiculous and unacceptable, refund me now.",
        customer_id="CUST1002"
    )

    assert result.intent == "refund_request"
    assert result.sub_intent == "severe_delay_refund"
    assert result.order_id == "ORD10002"
    assert result.customer_id == "CUST1002"
    assert result.product == "Sony WH-1000XM5 Wireless Headphones"
    assert result.requested_action == "issue_refund"
    assert result.urgency == "high"
    assert result.sentiment == "frustrated"
    assert "frustrated_customer_sentiment" in result.priority_indicators
    assert "order_entity_ORD10002" in result.priority_indicators
    assert result.relevant_entities["order_id"] == "ORD10002"
    assert result.confidence >= 0.9


def test_investigation_agent_execution_and_tool_logging(db_session):
    """Test Investigation Agent queries tools, records AgentAction/CaseEvents, and returns structured result."""
    # 1. Create a SupportCase
    case = CaseService.create_case(
        db_session,
        CaseCreate(
            customer_id="CUST1002",
            subject="Delayed package ORD10002",
            description="Package delayed past delivery window.",
            channel="web_chat",
            priority="high",
            initial_message="Where is ORD10002?"
        )
    )

    # 2. Get Customer 360
    c360 = CustomerIntelligenceService.get_customer_360(db_session, "CUST1002")
    assert c360 is not None

    # 3. Run Intake
    intake = run_intake_agent("Refund my delayed order ORD10002", customer_id="CUST1002")

    # 4. Run Investigation Agent
    inv_res: InvestigationResult = run_investigation_agent(
        db=db_session,
        case=case,
        customer_360=c360,
        intake=intake,
        task_id="test-inv-task"
    )

    # 5. Verify Output Structure
    assert inv_res.case_id == case.id
    assert len(inv_res.findings) >= 1
    assert len(inv_res.evidence) >= 1
    assert "database.orders" in inv_res.data_sources
    assert "carrier.tracking" in inv_res.data_sources
    assert "customer.loyalty" in [e.source for e in inv_res.evidence]
    assert inv_res.recommended_next_step is not None
    assert inv_res.investigation_status in ["complete", "partial", "needs_customer_input", "escalate"]

    # 6. Verify AgentAction and CaseEvent Database Logs
    actions = db_session.query(AgentAction).filter(AgentAction.case_id == case.id).all()
    action_types = [a.action_type for a in actions]
    assert "get_order_status" in action_types
    assert "check_refund_eligibility" in action_types

    events = db_session.query(CaseEvent).filter(CaseEvent.case_id == case.id).all()
    event_types = [e.event_type for e in events]
    assert "investigation_completed" in event_types


def test_investigation_missing_information_handling(db_session):
    """Test Investigation Agent identifies missing order ID and flags unresolved question."""
    case = CaseService.create_case(
        db_session,
        CaseCreate(
            customer_id="CUST1001",
            subject="General refund request",
            description="I want a refund but didn't mention order number.",
            channel="web_chat",
            priority="medium"
        )
    )
    c360 = CustomerIntelligenceService.get_customer_360(db_session, "CUST1001")
    intake = run_intake_agent("Please refund my purchase", customer_id="CUST1001")

    inv_res = run_investigation_agent(
        db=db_session,
        case=case,
        customer_360=c360,
        intake=intake,
        task_id="test-missing-task"
    )

    assert len(inv_res.unresolved_questions) >= 1
    assert "order identifier" in inv_res.unresolved_questions[0].lower() or "not found" in inv_res.unresolved_questions[0].lower()
    assert inv_res.investigation_status == "needs_customer_input"


def test_workflow_end_to_end_with_investigation():
    """Test full LangGraph workflow execution with Investigation Agent."""
    state: AgenticSupportState = {
        "task_id": "test-flow-360",
        "customer_id": "CUST1002",
        "conversation_id": "conv-test-360",
        "case_id": None,
        "user_goal": "Please check my order ORD10002, it is late and I want a refund",
        "messages": [{"role": "user", "content": "Please check my order ORD10002, it is late and I want a refund"}],
        "customer_360": None,
        "intent": {},
        "investigation_result": None,
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

    final_state = support_graph.invoke(state)

    assert final_state["status"] in ["completed", "escalated"]
    assert final_state["customer_360"] is not None
    assert final_state["investigation_result"] is not None
    assert len(final_state["investigation_result"]["findings"]) >= 1
    assert len(final_state["investigation_result"]["evidence"]) >= 1

    # Verify execution trace contains Investigation Agent
    trace_agents = [t["agent"] for t in final_state["execution_trace"]]
    assert "Investigation Agent" in trace_agents
