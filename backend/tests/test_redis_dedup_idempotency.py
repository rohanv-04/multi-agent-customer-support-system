import pytest
from backend.app.services.omnichannel_service import dedup_registry
from backend.app.services.action_gateway import ActionGateway
from backend.app.schemas.action_gateway import ActionRequest
from backend.app.database.database import SessionLocal
from backend.app.database.models import Order, Customer, SupportCase, get_utc_now


def test_request_deduplication():
    dedup_registry.clear()
    is_dup1 = dedup_registry.is_duplicate("REQ-001", "customer@novacart.com", "Where is my item?", "email")
    assert is_dup1 is False

    # Second submission with same request ID
    is_dup2 = dedup_registry.is_duplicate("REQ-001", "customer@novacart.com", "Where is my item?", "email")
    assert is_dup2 is True

    # Same content repeated
    is_dup3 = dedup_registry.is_duplicate("REQ-002", "customer@novacart.com", "Where is my item?", "email")
    assert is_dup3 is True


def test_event_id_deduplication():
    dedup_registry.clear()
    assert dedup_registry.is_event_duplicate("evt_shopify_12345", "shopify") is False
    # Replay of same event
    assert dedup_registry.is_event_duplicate("evt_shopify_12345", "shopify") is True


def test_action_gateway_idempotency():
    dedup_registry.clear()
    db = SessionLocal()
    now = get_utc_now()
    import uuid
    order_id = f"ORD-IDEMP-{uuid.uuid4().hex[:8].upper()}"

    # Setup test order
    order = Order(
        order_id=order_id,
        customer_id="CUST1002",
        status="Shipped",
        items_json='[{"name": "Wireless Mouse", "price": 120.00}]',
        total_amount=120.00,
        currency="USD",
        order_date=now,
        expected_delivery=now
    )
    db.add(order)
    db.commit()

    idempotency_key = f"IDEMP-KEY-{uuid.uuid4().hex[:8]}"

    req = ActionRequest(
        case_id="CASE-TEST-IDEMP",
        action_type="refund",
        actor_role="supervisor",
        requested_by="Supervisor Test",
        parameters={"order_id": order_id, "refund_amount": 120.00, "reason": "Idempotency test"},
        idempotency_key=idempotency_key
    )

    # First execution
    res1 = ActionGateway.execute_action(db=db, request=req)
    assert res1.status in ["VERIFIED", "EXECUTED"]

    # Second execution with identical idempotency_key must be suppressed and return previous result
    res2 = ActionGateway.execute_action(db=db, request=req)
    assert res2.action_id == res1.action_id
    assert res2.status == res1.status

    db.close()
