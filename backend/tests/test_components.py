import os
import pytest
from backend.app.database.database import init_db, SessionLocal
from backend.app.database.models import Customer, Order
from backend.app.tools.order_tool import get_order_status
from backend.app.tools.customer_tool import get_customer_info
from backend.app.tools.eligibility_tool import check_refund_eligibility
from backend.app.tools.refund_tool import process_refund
from backend.app.rag.vector_store import policy_store
from backend.app.rag.retrieval import retrieve_policy_knowledge

@pytest.fixture(scope="function", autouse=True)
def setup_test_db():
    init_db()
    db = SessionLocal()
    order = db.query(Order).filter(Order.order_id == "ORD10002").first()
    if order:
        order.status = "Delayed"
    db.commit()
    db.close()

def test_database_seed():
    db = SessionLocal()
    cust = db.query(Customer).filter(Customer.customer_id == "CUST1002").first()
    assert cust is not None
    assert cust.tier == "Platinum"

    order = db.query(Order).filter(Order.order_id == "ORD10002").first()
    assert order is not None
    assert order.status == "Delayed"
    db.close()

def test_order_tool():
    res = get_order_status("ORD10002")
    assert res["success"] is True
    assert res["status"] == "Delayed"
    assert res["carrier"] == "NovaExpress"

def test_customer_tool():
    res = get_customer_info("CUST1002")
    assert res["success"] is True
    assert res["name"] == "Elena Rostova"
    assert len(res["orders"]) > 0

def test_eligibility_tool_delayed_eligible():
    # ORD10002 is severely delayed (> 3 days past due) -> eligible
    res = check_refund_eligibility("ORD10002", "CUST1002")
    assert res["eligible"] is True
    assert res["refund_amount"] == 499.00
    assert "Shipping Delays" in res["policy_applied"]

def test_eligibility_tool_expired_ineligible():
    # ORD10003 was delivered > 30 days ago -> ineligible
    res = check_refund_eligibility("ORD10003", "CUST1003")
    assert res["eligible"] is False
    assert "30 days" in res["reason"].lower()

def test_rag_retrieval():
    policy_store.kb_dir = "knowledge_base"
    policy_store.index_documents()
    res = retrieve_policy_knowledge("What is the refund policy for delayed orders?")
    assert res["found"] is True
    assert len(res["citations"]) > 0
    assert "refund" in res["combined_context"].lower()
