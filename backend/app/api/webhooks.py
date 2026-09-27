import os
import json
import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Request, Header, status
from sqlalchemy.orm import Session

from ..database.database import get_db
from ..providers.ecommerce_webhooks import ShopifyWebhookAdapter, WooCommerceWebhookAdapter
from ..services.omnichannel_service import omnichannel_service, dedup_registry

router = APIRouter(prefix="/api/webhooks", tags=["External Store & Channel Webhooks"])
logger = logging.getLogger("api_webhooks")


@router.post("/shopify")
async def shopify_webhook(
    request: Request,
    x_shopify_topic: Optional[str] = Header(None),
    x_shopify_hmac_sha256: Optional[str] = Header(None),
    x_shopify_webhook_id: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    """Secure inbound endpoint for Shopify store webhooks with HMAC validation."""
    raw_body = await request.body()

    if not ShopifyWebhookAdapter.verify_signature(raw_body, x_shopify_hmac_sha256):
        logger.warning("Shopify webhook rejected due to invalid HMAC signature")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": {"code": "INVALID_SIGNATURE", "message": "Shopify HMAC verification failed"}}
        )

    try:
        payload = json.loads(raw_body.decode("utf-8"))
    except Exception as e:
        raise HTTPException(status_code=400, detail={"error": {"code": "MALFORMED_JSON", "message": str(e)}})

    webhook_id = x_shopify_webhook_id or str(payload.get("id", "shopify-evt-unknown"))
    topic = x_shopify_topic or "orders/updated"

    result = ShopifyWebhookAdapter.process_event(
        db=db,
        topic=topic,
        webhook_id=webhook_id,
        payload=payload
    )
    return result


@router.post("/woocommerce")
async def woocommerce_webhook(
    request: Request,
    x_wc_webhook_topic: Optional[str] = Header(None),
    x_wc_webhook_signature: Optional[str] = Header(None),
    x_wc_webhook_id: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    """Secure inbound endpoint for WooCommerce webhooks with HMAC validation."""
    raw_body = await request.body()

    if not WooCommerceWebhookAdapter.verify_signature(raw_body, x_wc_webhook_signature):
        logger.warning("WooCommerce webhook rejected due to invalid signature")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": {"code": "INVALID_SIGNATURE", "message": "WooCommerce HMAC verification failed"}}
        )

    try:
        payload = json.loads(raw_body.decode("utf-8"))
    except Exception as e:
        raise HTTPException(status_code=400, detail={"error": {"code": "MALFORMED_JSON", "message": str(e)}})

    webhook_id = x_wc_webhook_id or str(payload.get("id", "wc-evt-unknown"))
    event = x_wc_webhook_topic or "action.order.updated"

    result = WooCommerceWebhookAdapter.process_event(
        db=db,
        event=event,
        webhook_id=webhook_id,
        payload=payload
    )
    return result


@router.post("/whatsapp")
async def whatsapp_webhook(
    request: Request,
    x_hub_signature_256: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    """Inbound WhatsApp Cloud API webhook handler."""
    raw_body = await request.body()
    try:
        payload = json.loads(raw_body.decode("utf-8"))
    except Exception:
        payload = {}

    headers = dict(request.headers)
    support_req = omnichannel_service.normalize_inbound("whatsapp", payload, headers)
    result = omnichannel_service.process_inbound_request(db, support_req, trigger_workflow=True)
    return result.model_dump()


@router.post("/email")
async def email_webhook(
    request: Request,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    """Inbound Email provider webhook handler (SendGrid/Postmark format)."""
    raw_body = await request.body()
    try:
        payload = json.loads(raw_body.decode("utf-8"))
    except Exception:
        payload = {}

    headers = dict(request.headers)
    support_req = omnichannel_service.normalize_inbound("email", payload, headers)
    result = omnichannel_service.process_inbound_request(db, support_req, trigger_workflow=True)
    return result.model_dump()
