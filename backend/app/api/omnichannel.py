from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Request, Header
from sqlalchemy.orm import Session

from ..database.database import get_db
from ..schemas.omnichannel import (
    ChannelType,
    SupportRequest,
    InboundProcessingResult,
    ProviderMessageResponse
)
from ..services.omnichannel_service import omnichannel_service

router = APIRouter(prefix="/api/omnichannel", tags=["omnichannel"])


@router.get("/channels")
def list_supported_channels():
    """List all supported communication channels and active provider adapters."""
    return {
        "channels": [c.value for c in ChannelType],
        "providers": [
            {"channel": "web_chat", "provider": "SupportOS-WebChat-Provider", "status": "active"},
            {"channel": "email", "provider": "SupportOS-Email-Provider", "status": "active"},
            {"channel": "whatsapp", "provider": "SupportOS-WhatsApp-Provider", "status": "active"},
            {"channel": "api", "provider": "SupportOS-DirectAPI-Provider", "status": "active"},
            {"channel": "support_form", "provider": "SupportOS-WebForm-Provider", "status": "active"}
        ]
    }


@router.post("/inbound/{channel}", response_model=InboundProcessingResult)
async def inbound_channel_webhook(
    channel: str,
    payload: Dict[str, Any],
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Ingests and normalizes an inbound webhook/message from any external channel.
    Executes deduplication, customer resolution, case linking/creation, and AI workflow.
    """
    valid_channels = [c.value for c in ChannelType]
    if channel.lower() not in valid_channels:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid channel '{channel}'. Supported channels: {valid_channels}"
        )

    headers = dict(request.headers)
    try:
        support_req = omnichannel_service.normalize_inbound(channel.lower(), payload, headers)
        result = omnichannel_service.process_inbound_request(db, support_req, trigger_workflow=True)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process inbound message: {str(e)}")


class OutboundSendRequest(Dict[str, Any]):
    pass


@router.post("/send", response_model=ProviderMessageResponse)
def send_outbound_message(
    payload: Dict[str, Any],
    db: Session = Depends(get_db)
):
    """
    Dispatches an outbound communication over the designated channel provider.
    """
    case_id = payload.get("case_id")
    channel = payload.get("channel")
    recipient = payload.get("recipient")
    body = payload.get("body")
    metadata = payload.get("metadata")

    if not all([case_id, channel, recipient, body]):
        raise HTTPException(
            status_code=400,
            detail="Missing required parameters: 'case_id', 'channel', 'recipient', 'body'"
        )

    try:
        return omnichannel_service.dispatch_outbound(
            db=db,
            case_id=case_id,
            channel=channel,
            recipient=recipient,
            body=body,
            metadata=metadata
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send outbound message: {str(e)}")
