import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.database.database import init_db, SessionLocal
from backend.app.database.models import Customer, Order, Refund, SupportCase, EscalationTicket, CustomerMemory
from backend.app.services.customer_intelligence_service import CustomerIntelligenceService

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


def test_customer_360_service_aggregation(db_session):
    """Test Customer 360 aggregates all 11 required dimensions correctly."""
    c360 = CustomerIntelligenceService.get_customer_360(db_session, "CUST1002")
    assert c360 is not None

    # 1. Profile & Account Status
    assert c360.profile.customer_id == "CUST1002"
    assert c360.profile.name == "Elena Rostova"
    assert c360.account_status == "Active"

    # 2. Loyalty / Tier
    assert c360.loyalty.tier in ["Platinum", "Gold", "Silver", "Standard"]
    assert c360.loyalty.lifetime_spend > 0
    assert len(c360.loyalty.perks) > 0

    # 3. Orders & Payments
    assert len(c360.orders) >= 1
    assert len(c360.payments) >= 1
    delayed_orders = [o for o in c360.orders if o.status == "Delayed"]
    assert len(delayed_orders) >= 1
    assert delayed_orders[0].carrier is not None

    # 4. Refunds & Resolutions
    assert isinstance(c360.refunds, list)
    assert isinstance(c360.previous_resolutions, list)

    # 5. Cases & Complaints
    assert isinstance(c360.cases, list)
    assert isinstance(c360.previous_cases, list)
    assert isinstance(c360.previous_complaints, list)
    assert isinstance(c360.open_cases_count, int)

    # 6. Persistent Memories
    assert len(c360.memories) >= 1

    # 7. Risk Assessment
    assert "risk_level" in c360.risk_assessment
    assert "churn_signals" in c360.risk_assessment
    assert "loyalty_score" in c360.risk_assessment


def test_api_get_customer_360():
    """Test GET /api/customers/{id}/360 returns structured response or 404."""
    # Successful fetch
    response = client.get("/api/customers/CUST1002/360")
    assert response.status_code == 200
    data = response.json()

    assert data["profile"]["customer_id"] == "CUST1002"
    assert "loyalty" in data
    assert "orders" in data
    assert "payments" in data
    assert "refunds" in data
    assert "previous_cases" in data
    assert "previous_complaints" in data
    assert "previous_resolutions" in data
    assert "memories" in data
    assert "open_cases_count" in data
    assert "risk_assessment" in data

    # 404 Not Found
    err_response = client.get("/api/customers/NON_EXISTENT_ID/360")
    assert err_response.status_code == 404
    assert "not found" in err_response.json()["detail"].lower()


def test_api_get_customer_cases():
    """Test GET /api/customers/{id}/cases returns customer cases."""
    response = client.get("/api/customers/CUST1002/cases")
    assert response.status_code == 200
    cases = response.json()
    assert isinstance(cases, list)

    err_response = client.get("/api/customers/NON_EXISTENT_ID/cases")
    assert err_response.status_code == 404


def test_api_get_customer_orders():
    """Test GET /api/customers/{id}/orders returns customer orders."""
    response = client.get("/api/customers/CUST1002/orders")
    assert response.status_code == 200
    orders = response.json()
    assert isinstance(orders, list)
    assert len(orders) >= 1
    assert "order_id" in orders[0]
    assert "status" in orders[0]
    assert "items" in orders[0]

    err_response = client.get("/api/customers/NON_EXISTENT_ID/orders")
    assert err_response.status_code == 404


def test_api_get_customer_activity():
    """Test GET /api/customers/{id}/activity returns unified activity stream."""
    response = client.get("/api/customers/CUST1002/activity")
    assert response.status_code == 200
    activities = response.json()
    assert isinstance(activities, list)
    assert len(activities) >= 1

    types = {a["activity_type"] for a in activities}
    assert "order" in types

    err_response = client.get("/api/customers/NON_EXISTENT_ID/activity")
    assert err_response.status_code == 404
