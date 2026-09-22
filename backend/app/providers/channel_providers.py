import uuid
import datetime
from typing import Dict, Any, Optional
from .base import BaseChannelProvider
from ..schemas.omnichannel import SupportRequest, ProviderMessageResponse, ChannelType


class WebChatProvider(BaseChannelProvider):
    """Provider for real-time web widget / live chat."""
    
    @property
    def channel_type(self) -> ChannelType:
        return ChannelType.WEB_CHAT

    @property
    def provider_name(self) -> str:
        return "SupportOS-WebChat-Provider"

    def normalize_inbound(self, payload: Dict[str, Any], headers: Optional[Dict[str, str]] = None) -> SupportRequest:
        request_id = payload.get("message_id") or payload.get("request_id") or f"chat-msg-{uuid.uuid4().hex[:12]}"
        customer_id = payload.get("customer_id")
        sender_id = payload.get("sender_id") or customer_id or "anonymous-chat-user"
        sender_name = payload.get("sender_name") or payload.get("user_name")
        body = payload.get("message") or payload.get("body") or payload.get("text", "")
        conversation_id = payload.get("conversation_id") or payload.get("session_id")
        
        return SupportRequest(
            request_id=request_id,
            channel=ChannelType.WEB_CHAT,
            customer_id=customer_id,
            sender_identifier=sender_id,
            sender_name=sender_name,
            subject=payload.get("subject") or "Live Chat Inquiry",
            body=body,
            conversation_id=conversation_id,
            metadata={
                "ip_address": payload.get("ip_address"),
                "user_agent": payload.get("user_agent"),
                "page_url": payload.get("page_url"),
                "socket_id": payload.get("socket_id")
            }
        )

    def send_outbound(
        self,
        recipient: str,
        body: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ProviderMessageResponse:
        now = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
        msg_id = f"chat-out-{uuid.uuid4().hex[:10]}"
        return ProviderMessageResponse(
            provider_name=self.provider_name,
            channel=ChannelType.WEB_CHAT,
            recipient=recipient,
            message_id=msg_id,
            status="sent",
            delivered_at=now,
            details={"delivered_via": "WebSocket/SSE", "recipient_session": recipient}
        )


class EmailProvider(BaseChannelProvider):
    """Provider for inbound and outbound Email (MIME/SMTP/SendGrid-compatible)."""

    @property
    def channel_type(self) -> ChannelType:
        return ChannelType.EMAIL

    @property
    def provider_name(self) -> str:
        return "SupportOS-Email-Provider"

    def normalize_inbound(self, payload: Dict[str, Any], headers: Optional[Dict[str, str]] = None) -> SupportRequest:
        from_email = payload.get("from") or payload.get("sender") or payload.get("from_email", "support-sender@example.com")
        request_id = payload.get("message_id") or payload.get("email_id") or f"email-{uuid.uuid4().hex[:12]}"
        subject = payload.get("subject") or "Support Email Inquiry"
        body = payload.get("body") or payload.get("text") or payload.get("html") or payload.get("content", "")
        customer_id = payload.get("customer_id")
        sender_name = payload.get("from_name") or payload.get("sender_name")

        return SupportRequest(
            request_id=request_id,
            channel=ChannelType.EMAIL,
            customer_id=customer_id,
            sender_identifier=from_email.lower().strip(),
            sender_name=sender_name,
            subject=subject,
            body=body,
            conversation_id=payload.get("thread_id") or payload.get("conversation_id"),
            metadata={
                "to": payload.get("to") or "support@novacart.com",
                "cc": payload.get("cc"),
                "in_reply_to": payload.get("in_reply_to"),
                "attachments": payload.get("attachments", []),
                "headers": headers or {}
            }
        )

    def send_outbound(
        self,
        recipient: str,
        body: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ProviderMessageResponse:
        now = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
        msg_id = f"email-out-{uuid.uuid4().hex[:10]}"
        return ProviderMessageResponse(
            provider_name=self.provider_name,
            channel=ChannelType.EMAIL,
            recipient=recipient,
            message_id=msg_id,
            status="sent",
            delivered_at=now,
            details={
                "subject": metadata.get("subject", "Update on your NovaCart Support Case") if metadata else "Support Update",
                "smtp_status": "250 OK: Message accepted for delivery"
            }
        )


class WhatsAppProvider(BaseChannelProvider):
    """Provider for WhatsApp Business API / Webhooks."""

    @property
    def channel_type(self) -> ChannelType:
        return ChannelType.WHATSAPP

    @property
    def provider_name(self) -> str:
        return "SupportOS-WhatsApp-Provider"

    def normalize_inbound(self, payload: Dict[str, Any], headers: Optional[Dict[str, str]] = None) -> SupportRequest:
        # Standard WhatsApp Webhook parsing (compatible with Meta/Twilio structure)
        phone = payload.get("from") or payload.get("wa_id") or payload.get("phone_number", "+10000000000")
        if phone.startswith("whatsapp:"):
            phone = phone.replace("whatsapp:", "")
        
        request_id = payload.get("message_id") or payload.get("id") or payload.get("SmsMessageSid") or f"wa-msg-{uuid.uuid4().hex[:12]}"
        
        # Message content extraction
        body = ""
        if "text" in payload and isinstance(payload["text"], dict):
            body = payload["text"].get("body", "")
        elif "body" in payload:
            body = payload["body"]
        elif "message" in payload:
            body = payload["message"]
        elif "Body" in payload:
            body = payload["Body"]

        customer_id = payload.get("customer_id")
        sender_name = payload.get("profile_name") or payload.get("name")

        return SupportRequest(
            request_id=request_id,
            channel=ChannelType.WHATSAPP,
            customer_id=customer_id,
            sender_identifier=phone,
            sender_name=sender_name,
            subject=f"WhatsApp Inquiry from {phone}",
            body=body,
            conversation_id=payload.get("conversation_id"),
            metadata={
                "wa_id": phone,
                "profile_name": sender_name,
                "timestamp": payload.get("timestamp"),
                "type": payload.get("type", "text")
            }
        )

    def send_outbound(
        self,
        recipient: str,
        body: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ProviderMessageResponse:
        now = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
        msg_id = f"wamid.{uuid.uuid4().hex[:16]}"
        return ProviderMessageResponse(
            provider_name=self.provider_name,
            channel=ChannelType.WHATSAPP,
            recipient=recipient,
            message_id=msg_id,
            status="sent",
            delivered_at=now,
            details={"template": metadata.get("template") if metadata else None, "network": "WhatsApp"}
        )


class APIProvider(BaseChannelProvider):
    """Provider for direct B2B / programmatic API ingestion."""

    @property
    def channel_type(self) -> ChannelType:
        return ChannelType.API

    @property
    def provider_name(self) -> str:
        return "SupportOS-DirectAPI-Provider"

    def normalize_inbound(self, payload: Dict[str, Any], headers: Optional[Dict[str, str]] = None) -> SupportRequest:
        request_id = payload.get("request_id") or payload.get("id") or f"api-req-{uuid.uuid4().hex[:12]}"
        customer_id = payload.get("customer_id") or payload.get("client_id") or "CUST-API"
        sender_id = payload.get("api_key_id") or payload.get("caller_id") or customer_id
        body = payload.get("query") or payload.get("message") or payload.get("body") or payload.get("prompt", "")
        subject = payload.get("subject") or "API Automated Support Request"

        return SupportRequest(
            request_id=request_id,
            channel=ChannelType.API,
            customer_id=customer_id,
            sender_identifier=str(sender_id),
            sender_name=payload.get("sender_name") or "API Client",
            subject=subject,
            body=body,
            conversation_id=payload.get("conversation_id"),
            metadata={
                "client_version": payload.get("client_version"),
                "priority_hint": payload.get("priority"),
                "callback_url": payload.get("callback_url"),
                "headers": headers or {}
            }
        )

    def send_outbound(
        self,
        recipient: str,
        body: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ProviderMessageResponse:
        now = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
        msg_id = f"api-res-{uuid.uuid4().hex[:10]}"
        return ProviderMessageResponse(
            provider_name=self.provider_name,
            channel=ChannelType.API,
            recipient=recipient,
            message_id=msg_id,
            status="sent",
            delivered_at=now,
            details={"callback_delivered": bool(metadata and metadata.get("callback_url"))}
        )


class SupportFormProvider(BaseChannelProvider):
    """Provider for structured Help Center / Web Portal contact forms."""

    @property
    def channel_type(self) -> ChannelType:
        return ChannelType.SUPPORT_FORM

    @property
    def provider_name(self) -> str:
        return "SupportOS-WebForm-Provider"

    def normalize_inbound(self, payload: Dict[str, Any], headers: Optional[Dict[str, str]] = None) -> SupportRequest:
        request_id = payload.get("form_submission_id") or payload.get("submission_id") or payload.get("request_id") or f"form-sub-{uuid.uuid4().hex[:12]}"
        email = payload.get("email") or payload.get("contact_email") or "form-user@example.com"
        name = payload.get("name") or payload.get("full_name") or "Web User"
        category = payload.get("category") or payload.get("issue_type") or "General Inquiry"
        order_number = payload.get("order_number") or payload.get("order_id")
        description = payload.get("description") or payload.get("message") or payload.get("details", "")
        subject = payload.get("subject") or f"[{category}] Web Form Submission"

        full_body = description
        if order_number:
            full_body = f"Order Number: {order_number}\nCategory: {category}\n\n{description}"

        customer_id = payload.get("customer_id")

        return SupportRequest(
            request_id=request_id,
            channel=ChannelType.SUPPORT_FORM,
            customer_id=customer_id,
            sender_identifier=email.lower().strip(),
            sender_name=name,
            subject=subject,
            body=full_body,
            conversation_id=payload.get("conversation_id"),
            metadata={
                "category": category,
                "order_number": order_number,
                "urgency": payload.get("urgency"),
                "form_version": payload.get("form_version", "1.0")
            }
        )

    def send_outbound(
        self,
        recipient: str,
        body: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ProviderMessageResponse:
        now = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
        msg_id = f"portal-notif-{uuid.uuid4().hex[:10]}"
        return ProviderMessageResponse(
            provider_name=self.provider_name,
            channel=ChannelType.SUPPORT_FORM,
            recipient=recipient,
            message_id=msg_id,
            status="sent",
            delivered_at=now,
            details={"portal_ticket_update": True}
        )
