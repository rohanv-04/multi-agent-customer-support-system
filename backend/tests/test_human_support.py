import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.main import app
from backend.app.database.database import init_db, SessionLocal
from backend.app.database.models import SupportCase, CaseEvent, HumanSupportAssignment, Customer, Organization
from backend.app.services.human_support_service import human_support_service, SUPPORT_CONTACTS
from backend.app.agents.intake_agent import run_intake_agent

@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    init_db()

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Test 1: Human-support request detection
def test_human_support_request_detection():
    phrases = [
        "I want to talk to a human.",
        "Connect me to an agent please",
        "I want customer support",
        "Can I speak with someone?",
        "Transfer me to a human representative",
        "I don't want to talk to the bot, let me talk to a real person"
    ]
    for p in phrases:
        res = run_intake_agent(user_goal=p, customer_id="CUST1002")
        assert res.intent == "human_escalation", f"Failed to detect human escalation for '{p}'"
        assert res.requested_action == "escalate_to_human"


# Test 2: Normal conversations do not automatically trigger human assignment
def test_normal_conversations_do_not_trigger_human_assignment():
    normal_phrases = [
        "Where is my package for order ORD10001?",
        "What is the return policy for electronics?",
        "Can I change my shipping address?",
        "How do I apply a discount code?"
    ]
    for p in normal_phrases:
        res = run_intake_agent(user_goal=p, customer_id="CUST1002")
        assert res.intent != "human_escalation", f"Incorrectly triggered human escalation for '{p}'"


# Test 3: Centralized support contacts configuration
def test_configured_support_team():
    contacts = human_support_service.get_configured_contacts()
    assert len(contacts) == 3
    contact_ids = {c["id"] for c in contacts}
    assert contact_ids == {"kavin", "rohan", "narahari"}

    contact_map = {c["id"]: c["phone"] for c in contacts}
    assert contact_map["kavin"] == "7200212576"
    assert contact_map["rohan"] == "8025136089"
    assert contact_map["narahari"] == "7396892041"


# Test 4: Random representative assignment & all 3 can be selected across runs
def test_random_representative_selection_distribution():
    selected_names = set()
    # Using fixed seeds to test deterministic multi-selection
    for seed in range(50):
        rep = human_support_service.select_representative(seed=seed)
        assert rep["name"] in ["Kavin", "Rohan", "Narahari"]
        selected_names.add(rep["name"])

    # All three representatives must be reachable across random distribution
    assert selected_names == {"Kavin", "Rohan", "Narahari"}


# Test 5: Service assignment creates DB records, case events, and returns single representative with tel: link
def test_service_assign_human_support(db_session):
    case_id = "CASE-TEST-001"
    customer_id = "CUST1002"

    res = human_support_service.assign_human_support(
        db=db_session,
        case_id=case_id,
        customer_id=customer_id,
        seed=42
    )

    assert res.assignment_id.startswith("HSA-")
    assert res.case_id == case_id
    assert res.customer_id == customer_id
    assert res.status == "ASSIGNED"
    assert res.assignment_method == "RANDOM"
    assert res.representative.name in ["Kavin", "Rohan", "Narahari"]
    assert res.representative.phone in ["7200212576", "8025136089", "7396892041"]
    assert res.tel_link == f"tel:{res.representative.phone}"

    # Verify persistence in HumanSupportAssignment table
    db_assignment = db_session.query(HumanSupportAssignment).filter(HumanSupportAssignment.id == res.assignment_id).first()
    assert db_assignment is not None
    assert db_assignment.representative_name == res.representative.name
    assert db_assignment.phone == res.representative.phone
    assert db_assignment.status == "ASSIGNED"

    # Verify CaseEvent entries
    events = db_session.query(CaseEvent).filter(CaseEvent.case_id == case_id).all()
    event_types = [e.event_type for e in events]
    assert "HUMAN_CONTACT_REQUESTED" in event_types
    assert "HUMAN_AGENT_ASSIGNED" in event_types

    # Verify assigned event summary mentions representative name
    assigned_event = next(e for e in events if e.event_type == "HUMAN_AGENT_ASSIGNED")
    assert res.representative.name in assigned_event.summary


# Test 6: API endpoint POST /api/cases/{case_id}/human-support
def test_api_request_human_support(client, db_session):
    case_id = "CASE-API-99"
    response = client.post(
        f"/api/cases/{case_id}/human-support",
        json={"customer_id": "CUST1002", "notes": "Customer requested callback"}
    )
    assert response.status_code == 200
    data = response.json()

    assert "assignment_id" in data
    assert data["case_id"] == case_id
    assert data["customer_id"] == "CUST1002"
    assert data["status"] == "ASSIGNED"
    assert data["assignment_method"] == "RANDOM"
    assert data["representative"]["name"] in ["Kavin", "Rohan", "Narahari"]
    assert data["tel_link"].startswith("tel:")
    assert data["tel_link"] == f"tel:{data['representative']['phone']}"


# Test 7: Recording CALL_INITIATED updates status & logs event without marking COMPLETED
def test_record_call_initiated(client, db_session):
    case_id = "CASE-CALL-01"
    # 1. Assign representative
    assign_res = human_support_service.assign_human_support(
        db=db_session,
        case_id=case_id,
        customer_id="CUST1002"
    )
    assignment_id = assign_res.assignment_id

    # 2. Customer clicks "Call Now"
    call_res = client.post(f"/api/cases/{case_id}/human-support/{assignment_id}/call")
    assert call_res.status_code == 200
    call_data = call_res.json()

    assert call_data["assignment_id"] == assignment_id
    assert call_data["status"] == "CALL_INITIATED"
    assert call_data["tel_link"] == f"tel:{assign_res.representative.phone}"

    # Verify DB assignment is NOT COMPLETED, but CALL_INITIATED
    db_assignment = db_session.query(HumanSupportAssignment).filter(HumanSupportAssignment.id == assignment_id).first()
    assert db_assignment.status == "CALL_INITIATED"

    # Verify CaseEvent CALL_INITIATED is logged
    call_event = (
        db_session.query(CaseEvent)
        .filter(CaseEvent.case_id == case_id, CaseEvent.event_type == "CALL_INITIATED")
        .first()
    )
    assert call_event is not None
    assert "Call Now" in call_event.summary


# Test 8: GET /api/cases/{case_id}/human-support returns active assignment
def test_get_active_assignment_api(client, db_session):
    case_id = "CASE-FETCH-01"
    assign_res = human_support_service.assign_human_support(
        db=db_session,
        case_id=case_id,
        customer_id="CUST1002"
    )

    fetch_res = client.get(f"/api/cases/{case_id}/human-support")
    assert fetch_res.status_code == 200
    data = fetch_res.json()
    assert data["assignment_id"] == assign_res.assignment_id
    assert data["representative"]["name"] == assign_res.representative.name
