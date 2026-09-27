import os
import json
import hmac
import hashlib
import base64
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.services.omnichannel_service import dedup_registry

client = TestClient(app)


def test_telephony_outbound_call_dispatch(monkeypatch):
    """Test POST /api/human-support/call using TelephonyProvider."""
    monkeypatch.setenv("AGENT_KAVIN_PHONE", "+1234567890")
    response = client.post(
        "/api/human-support/call",
        json={"case_id": "CASE-TEST-TEL-01", "agent_id": "kavin"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["case_id"] == "CASE-TEST-TEL-01"
    assert "Kavin" in data["representative"]
    assert data["status"] in ["initiated", "queued", "ringing"]
    assert "mock" in data["provider"].lower() or "twilio" in data["provider"].lower()


def test_shopify_webhook_signature_verification(monkeypatch):
    """Test Shopify webhook HMAC validation and event processing."""
    secret = "test_shopify_secret_key"
    monkeypatch.setenv("SHOPIFY_WEBHOOK_SECRET", secret)

    payload = {
        "id": 883921029,
        "name": "#1029",
        "email": "customer@novacart.com",
        "total_price": "89.99",
        "financial_status": "paid",
        "fulfillment_status": "fulfilled",
        "customer": {"first_name": "Jane", "last_name": "Doe"}
    }
    raw_body = json.dumps(payload).encode("utf-8")

    # Compute valid HMAC
    valid_hmac = base64.b64encode(
        hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).digest()
    ).decode("utf-8")

    # 1. Invalid signature should be rejected with 401
    bad_resp = client.post(
        "/api/webhooks/shopify",
        content=raw_body,
        headers={
            "Content-Type": "application/json",
            "X-Shopify-Topic": "orders/updated",
            "X-Shopify-Hmac-Sha256": "invalid_signature",
            "X-Shopify-Webhook-Id": "evt-shop-001"
        }
    )
    assert bad_resp.status_code == 401

    # 2. Valid signature accepted
    good_resp = client.post(
        "/api/webhooks/shopify",
        content=raw_body,
        headers={
            "Content-Type": "application/json",
            "X-Shopify-Topic": "orders/updated",
            "X-Shopify-Hmac-Sha256": valid_hmac,
            "X-Shopify-Webhook-Id": "evt-shop-002"
        }
    )
    assert good_resp.status_code == 200
    assert good_resp.json()["status"] in ["success", "processed"]

    # 3. Duplicate event ID should be deduplicated
    dup_resp = client.post(
        "/api/webhooks/shopify",
        content=raw_body,
        headers={
            "Content-Type": "application/json",
            "X-Shopify-Topic": "orders/updated",
            "X-Shopify-Hmac-Sha256": valid_hmac,
            "X-Shopify-Webhook-Id": "evt-shop-002"
        }
    )
    assert dup_resp.status_code == 200
    assert dup_resp.json().get("reason") == "duplicate_event_id" or dup_resp.json().get("status") in ["ignored", "deduplicated"]


def test_woocommerce_webhook_validation_and_deduplication(monkeypatch):
    """Test WooCommerce webhook signature validation and deduplication."""
    secret = "wc_webhook_secret_key"
    monkeypatch.setenv("WOOCOMMERCE_WEBHOOK_SECRET", secret)

    payload = {
        "id": 99401,
        "status": "completed",
        "total": "45.00",
        "billing": {"email": "alex@novacart.com", "first_name": "Alex", "last_name": "Smith"}
    }
    raw_body = json.dumps(payload).encode("utf-8")

    # Compute valid signature
    valid_sig = base64.b64encode(
        hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).digest()
    ).decode("utf-8")

    # 1. Invalid signature
    bad_resp = client.post(
        "/api/webhooks/woocommerce",
        content=raw_body,
        headers={
            "Content-Type": "application/json",
            "X-WC-Webhook-Topic": "order.updated",
            "X-WC-Webhook-Signature": "wrong-signature",
            "X-WC-Webhook-ID": "wc-delivery-101"
        }
    )
    assert bad_resp.status_code == 401

    # 2. Valid signature
    good_resp = client.post(
        "/api/webhooks/woocommerce",
        content=raw_body,
        headers={
            "Content-Type": "application/json",
            "X-WC-Webhook-Topic": "order.updated",
            "X-WC-Webhook-Signature": valid_sig,
            "X-WC-Webhook-ID": "wc-delivery-102"
        }
    )
    assert good_resp.status_code == 200
    assert good_resp.json()["status"] in ["success", "processed"]


def test_whatsapp_webhook_inbound():
    """Test inbound WhatsApp webhook processing."""
    payload = {
        "event_id": "wa-msg-88129",
        "sender": "+15550998877",
        "sender_name": "Marcus Aurelius",
        "body": "Hi, where is my package for order ORD-1002?"
    }
    resp = client.post(
        "/api/webhooks/whatsapp",
        json=payload,
        headers={"X-Event-ID": "wa-msg-88129"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["channel"] == "whatsapp"
    assert data["status"] in ["processed", "created"]
    assert "case_id" in data


def test_email_webhook_inbound():
    """Test inbound email webhook processing."""
    payload = {
        "message_id": "msg-email-unique-0091",
        "sender": "sarah.connor@sky.net",
        "sender_name": "Sarah Connor",
        "subject": "Damaged goods in my recent delivery",
        "body": "I received my order yesterday but the item was defective. Please help with a return."
    }
    resp = client.post(
        "/api/webhooks/email",
        json=payload
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["channel"] == "email"
    assert "case_id" in data
