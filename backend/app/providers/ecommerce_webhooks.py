import os
import hmac
import hashlib
import base64
import json
import logging
from typing import Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session

from ..database.models import Order, Customer, SupportCase, CaseMessage, CaseEvent, get_utc_now
from ..schemas.case import CasePriority
from ..schemas.omnichannel import ChannelType
from ..services.omnichannel_service import dedup_registry

logger = logging.getLogger("ecommerce_webhooks")


class ShopifyWebhookAdapter:
    """Enterprise webhook adapter for Shopify store events with HMAC verification and idempotency."""

    @classmethod
    def verify_signature(cls, raw_body: bytes, hmac_header: Optional[str]) -> bool:
        """Verifies X-Shopify-Hmac-Sha256 header against SHOPIFY_WEBHOOK_SECRET."""
        secret = os.getenv("SHOPIFY_WEBHOOK_SECRET")
        if not secret:
            # If not configured in dev/test, warn and allow testing if explicitly disabled
            if os.getenv("ENVIRONMENT") == "development" or os.getenv("DISABLE_WEBHOOK_VERIFY") == "true":
                return True
            logger.warning("SHOPIFY_WEBHOOK_SECRET not configured, rejecting webhook.")
            return False

        if not hmac_header:
            return False

        digest = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).digest()
        computed_hmac = base64.b64encode(digest).decode("utf-8")
        return hmac.compare_digest(computed_hmac, hmac_header)

    @classmethod
    def process_event(
        cls,
        db: Session,
        topic: str,
        webhook_id: str,
        payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process Shopify order and fulfillment events with deduplication."""
        # 1. Idempotency Check
        if dedup_registry.is_event_duplicate(webhook_id, namespace="shopify"):
            logger.info(f"Duplicate Shopify webhook event {webhook_id} ignored.")
            return {"status": "ignored", "reason": "duplicate_event_id", "webhook_id": webhook_id}

        order_id = str(payload.get("name") or payload.get("order_number") or payload.get("id"))
        customer_data = payload.get("customer", {})
        customer_email = customer_data.get("email") or payload.get("email", "shopify-user@novacart.com")
        customer_name = f"{customer_data.get('first_name', '')} {customer_data.get('last_name', '')}".strip() or "NovaCart Customer"

        # Find or update order in local database
        existing_order = db.query(Order).filter(Order.order_id == order_id).first()

        now = get_utc_now()
        import datetime
        cust_id = "CUST1002"  # Fallback to standard seeded customer or create
        existing_cust = db.query(Customer).filter(Customer.customer_id == cust_id).first()
        if not existing_cust:
            existing_cust = db.query(Customer).first()
            if existing_cust:
                cust_id = existing_cust.customer_id

        if not existing_order:
            total_price = float(payload.get("total_price") or payload.get("current_total_price") or 0.0)
            existing_order = Order(
                order_id=order_id,
                customer_id=cust_id,
                status=payload.get("financial_status") or "Processing",
                total_amount=total_price,
                currency=payload.get("currency", "USD"),
                items_json=json.dumps(payload.get("line_items", [])),
                order_date=now,
                expected_delivery=now + datetime.timedelta(days=3),
                created_at=now
            )
            db.add(existing_order)
            db.commit()

        # Handle specific topics
        if topic in ["orders/cancelled", "orders/cancel"]:
            existing_order.status = "Cancelled"
            db.commit()
            return {"status": "success", "action": "order_cancelled", "order_id": order_id}

        elif topic in ["fulfillments/create", "fulfillments/update"]:
            tracking_number = payload.get("tracking_number") or (payload.get("tracking_numbers", [None])[0] if payload.get("tracking_numbers") else None)
            if tracking_number:
                existing_order.tracking_number = tracking_number
                existing_order.carrier = payload.get("tracking_company") or "NovaExpress"
                existing_order.status = "In Transit"
                db.commit()
            return {"status": "success", "action": "fulfillment_updated", "order_id": order_id}

        return {"status": "success", "action": "processed", "order_id": order_id, "topic": topic}


class WooCommerceWebhookAdapter:
    """Enterprise webhook adapter for WooCommerce store events with HMAC verification."""

    @classmethod
    def verify_signature(cls, raw_body: bytes, signature_header: Optional[str]) -> bool:
        """Verifies X-WC-Webhook-Signature against WOOCOMMERCE_WEBHOOK_SECRET."""
        secret = os.getenv("WOOCOMMERCE_WEBHOOK_SECRET")
        if not secret:
            if os.getenv("ENVIRONMENT") == "development" or os.getenv("DISABLE_WEBHOOK_VERIFY") == "true":
                return True
            logger.warning("WOOCOMMERCE_WEBHOOK_SECRET not configured, rejecting webhook.")
            return False

        if not signature_header:
            return False

        digest = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).digest()
        computed_signature = base64.b64encode(digest).decode("utf-8")
        return hmac.compare_digest(computed_signature, signature_header)

    @classmethod
    def process_event(
        cls,
        db: Session,
        event: str,
        webhook_id: str,
        payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process WooCommerce order events with deduplication."""
        if dedup_registry.is_event_duplicate(webhook_id, namespace="woocommerce"):
            logger.info(f"Duplicate WooCommerce webhook event {webhook_id} ignored.")
            return {"status": "ignored", "reason": "duplicate_event_id", "webhook_id": webhook_id}

        order_id = f"WC-{payload.get('id')}"
        now = get_utc_now()
        import datetime
        cust_id = "CUST1002"
        existing_cust = db.query(Customer).filter(Customer.customer_id == cust_id).first()
        if not existing_cust:
            existing_cust = db.query(Customer).first()
            if existing_cust:
                cust_id = existing_cust.customer_id

        existing_order = db.query(Order).filter(Order.order_id == order_id).first()

        if not existing_order:
            total_price = float(payload.get("total", 0.0))
            existing_order = Order(
                order_id=order_id,
                customer_id=cust_id,
                status=payload.get("status", "Processing"),
                total_amount=total_price,
                currency=payload.get("currency", "USD"),
                items_json=json.dumps(payload.get("line_items", [])),
                order_date=now,
                expected_delivery=now + datetime.timedelta(days=3),
                created_at=now
            )
            db.add(existing_order)
            db.commit()
        else:
            existing_order.status = payload.get("status", existing_order.status)
            db.commit()

        return {"status": "success", "action": "processed", "order_id": order_id, "event": event}
