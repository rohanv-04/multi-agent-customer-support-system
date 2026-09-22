import uuid
import pytest
from backend.app.database.database import init_db, SessionLocal
from backend.app.database.models import Refund, Order, EscalationTicket
from backend.app.graph.workflow import support_graph
from backend.app.graph.state import AgenticSupportState

@pytest.fixture(scope="session", autouse=True)
def setup_db():
    init_db()

def test_scenario_3_autonomous_refund():
    """Primary Acceptance Test:

    User: 'My order ORD10002 is delayed. If I'm eligible, refund it.'
    Expected:
    - Understands goal & extracts ORD10002
    - Plans steps
    - Executes get_order_status
    - Retrieves RAG policy
    - Checks refund eligibility (eligible)
    - Processes refund transaction in DB
    - Validates via Critic
    - Updates Memory
    - Returns final confirmation with refund receipt
    """
    # Ensure test order ORD10002 is clean and in Delayed status
    db = SessionLocal()
    order = db.query(Order).filter(Order.order_id == "ORD10002").first()
    if order:
        order.status = "Delayed"
    db.query(Refund).filter(Refund.order_id == "ORD10002").delete()
    db.commit()
    db.close()

    task_id = f"test-task-{uuid.uuid4().hex[:6]}"
    initial_state: AgenticSupportState = {
        "task_id": task_id,
        "customer_id": "CUST1002",
        "conversation_id": f"conv-{uuid.uuid4().hex[:6]}",
        "user_goal": "My order ORD10002 is delayed. If I'm eligible, refund it.",
        "messages": [],
        "intent": {},
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

    # Assertions
    assert final_state["status"] == "completed"
    assert final_state["confidence"] >= 0.75
    assert len(final_state["execution_trace"]) > 5

    # Check that tools were called
    tool_names = [tc.get("tool_name") for tc in final_state["tool_calls"]]
    assert "get_order_status" in tool_names
    assert "check_refund_eligibility" in tool_names
    assert "process_refund" in tool_names

    # Check real database change
    db = SessionLocal()
    refund = db.query(Refund).filter(Refund.order_id == "ORD10002").first()
    assert refund is not None
    assert refund.refund_amount == 499.00

    order = db.query(Order).filter(Order.order_id == "ORD10002").first()
    assert order.status == "Refunded"
    db.close()

    # Check final response mentions refund and transaction ID
    assert "refund" in final_state["final_response"].lower()
    assert refund.refund_id in final_state["final_response"]

def test_scenario_1_policy_inquiry():
    task_id = f"test-task-{uuid.uuid4().hex[:6]}"
    initial_state: AgenticSupportState = {
        "task_id": task_id,
        "customer_id": "CUST1001",
        "conversation_id": "conv-test",
        "user_goal": "What is your refund policy?",
        "messages": [],
        "intent": {},
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
    assert final_state["status"] == "completed"
    assert len(final_state["retrieved_docs"]) > 0
    assert "policy" in final_state["final_response"].lower()

def test_scenario_5_human_escalation():
    task_id = f"test-task-{uuid.uuid4().hex[:6]}"
    initial_state: AgenticSupportState = {
        "task_id": task_id,
        "customer_id": "CUST1001",
        "conversation_id": "conv-test",
        "user_goal": "I want to speak to a human.",
        "messages": [],
        "intent": {},
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
    assert final_state["requires_escalation"] is True
    assert final_state["escalation_dossier"] is not None
    assert "TICK-" in final_state["escalation_dossier"]["ticket_id"]

    # Verify ticket in DB
    db = SessionLocal()
    ticket = db.query(EscalationTicket).filter(EscalationTicket.task_id == task_id).first()
    assert ticket is not None
    db.close()

def test_scenario_2_multistep_reasoning():
    """Scenario 2: 'Check order ORD10001 and tell me if I'm eligible for a refund.'"""
    task_id = f"test-task-{uuid.uuid4().hex[:6]}"
    initial_state: AgenticSupportState = {
        "task_id": task_id,
        "customer_id": "CUST1001",
        "conversation_id": f"conv-{uuid.uuid4().hex[:6]}",
        "user_goal": "Check order ORD10001 and tell me if I'm eligible for a refund.",
        "messages": [],
        "intent": {},
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
    assert final_state["status"] == "completed"
    tool_names = [tc.get("tool_name") for tc in final_state["tool_calls"]]
    assert "get_order_status" in tool_names
    assert "check_refund_eligibility" in tool_names
    # Should not have processed refund because not requested to auto-refund yet
    assert "ORD10001" in final_state["final_response"]

def test_scenario_4_replanning_recovery():
    """Scenario 4: Re-planning when a step failure is detected."""
    task_id = f"test-task-{uuid.uuid4().hex[:6]}"
    # Trigger a task where Critic flags an issue
    initial_state: AgenticSupportState = {
        "task_id": task_id,
        "customer_id": "CUST1001",
        "conversation_id": f"conv-{uuid.uuid4().hex[:6]}",
        "user_goal": "Please check order ORD99999 and refund it.",
        "messages": [],
        "intent": {},
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
    # Since ORD99999 does not exist, get_order_status fails, Critic triggers replanning loop
    assert final_state["replan_count"] > 0
    traces = [t["action"] for t in final_state["execution_trace"]]
    assert any("re-planning" in t.lower() for t in traces)
