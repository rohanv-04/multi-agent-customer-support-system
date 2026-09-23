import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.database.database import init_db, SessionLocal
from backend.app.database.models import Order, Customer, SupportCase
from backend.app.agents.intake_agent import run_intake_agent
from backend.app.agents.supervisor import format_final_customer_response

@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    init_db()

@pytest.fixture
def client():
    return TestClient(app)

# 1. Natural multi-turn dialogue with missing order ID
def test_conversational_missing_order_id_turn_1(client):
    response = client.post(
        "/api/chat",
        json={
            "message": "Hey, my order hasn't arrived yet.",
            "customer_id": "CUST1002"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["intent"]["intent"] == "order_status_inquiry"
    # AI asks for order number naturally without robotic menus or errors
    assert "order number" in data["response"].lower() or "share" in data["response"].lower()
    # Does NOT include repeated human escalation prompt
    assert "Would you like to speak with a human?" not in data["response"]

# 2. Multi-turn follow-up providing order ID
def test_conversational_provide_order_id_turn_2(client):
    conv_id = "conv-test-realistic-01"
    # Turn 1
    client.post(
        "/api/chat",
        json={
            "message": "My order is late.",
            "customer_id": "CUST1002",
            "conversation_id": conv_id
        }
    )

    # Turn 2: User gives order number
    res2 = client.post(
        "/api/chat",
        json={
            "message": "It's ORD10002",
            "customer_id": "CUST1002",
            "conversation_id": conv_id
        }
    )
    assert res2.status_code == 200
    data2 = res2.json()
    assert "ORD10002" in data2["response"]
    # Check that tools investigated real order ORD10002
    tool_names = [tc["tool_name"] for tc in data2["tool_calls"]]
    assert "get_order_status" in tool_names

# 3. Multi-turn follow-up requesting refund for the same order
def test_conversational_refund_followup_turn_3(client):
    conv_id = "conv-test-realistic-02"
    # Turn 1: Order inquiry with ORD10002
    client.post(
        "/api/chat",
        json={
            "message": "Check status of order ORD10002",
            "customer_id": "CUST1002",
            "conversation_id": conv_id
        }
    )

    # Turn 2: Follow-up asking for refund without repeating order number
    res2 = client.post(
        "/api/chat",
        json={
            "message": "Can I get a refund?",
            "customer_id": "CUST1002",
            "conversation_id": conv_id
        }
    )
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["intent"]["intent"] == "refund_request"
    assert data2["intent"]["entities"]["order_id"] == "ORD10002"
    # Verified refund processed per policy
    assert "refund" in data2["response"].lower()

# 4. Policy inquiry is clear, concise, and grounded
def test_conversational_policy_inquiry(client):
    res = client.post(
        "/api/chat",
        json={
            "message": "What is your refund policy?",
            "customer_id": "CUST1001"
        }
    )
    assert res.status_code == 200
    data = res.json()
    assert data["intent"]["intent"] == "policy_inquiry"
    assert len(data["response"]) > 20
    assert "policy" in data["response"].lower() or "refund" in data["response"].lower()

# 5. Explicit human escalation
def test_conversational_explicit_human_request(client):
    res = client.post(
        "/api/chat",
        json={
            "message": "I want to speak with someone.",
            "customer_id": "CUST1002"
        }
    )
    assert res.status_code == 200
    data = res.json()
    assert data["requires_escalation"] is True
    assert "human" in data["response"].lower()

# 6. Response formatter does not generate robotic menus
def test_response_formatter_naturalness():
    # Normal order status response
    resp = format_final_customer_response(
        intent_data={"intent": "order_status_inquiry", "entities": {"order_id": "ORD10001"}},
        observations=[],
        tool_calls=[{
            "tool_name": "get_order_status",
            "status": "success",
            "result": {
                "status": "In Transit",
                "carrier": "NovaExpress",
                "tracking_number": "TRK-987654",
                "delay_reason": None
            }
        }]
    )
    assert "Please choose an option" not in resp
    assert "Select your issue" not in resp
    assert "ORD10001" in resp
    assert "NovaExpress" in resp
