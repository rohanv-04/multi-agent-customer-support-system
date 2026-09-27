import os
import uuid
import datetime
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

logger = logging.getLogger("telephony")


class TelephonyProvider(ABC):
    """Abstract interface for third-party voice calling providers (Twilio, Vonage, SIP)."""

    @abstractmethod
    def initiate_outbound_call(
        self,
        to_phone: str,
        from_phone: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Initiate outbound voice call to representative or customer."""
        pass

    @abstractmethod
    def get_call_status(self, call_sid: str) -> Dict[str, Any]:
        """Fetch current call status."""
        pass


class MockTelephonyProvider(TelephonyProvider):
    """Deterministic simulation provider for development, testing, and CI/CD environments."""

    def __init__(self):
        self._calls: Dict[str, Dict[str, Any]] = {}

    def initiate_outbound_call(
        self,
        to_phone: str,
        from_phone: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        call_sid = f"CA-MOCK-{uuid.uuid4().hex[:12].upper()}"
        now = datetime.datetime.now(datetime.timezone.utc)
        record = {
            "call_sid": call_sid,
            "provider": "MockTelephonyProvider",
            "status": "queued",
            "to_phone": to_phone,
            "from_phone": from_phone,
            "initiated_at": now.isoformat(),
            "metadata": metadata or {},
            "billable": False,
            "message": "Call simulated successfully. In production, this dials via carrier provider."
        }
        self._calls[call_sid] = record
        logger.info(f"[MockTelephony] Outbound call simulated {call_sid} to {to_phone}")
        return record

    def get_call_status(self, call_sid: str) -> Dict[str, Any]:
        return self._calls.get(call_sid, {"call_sid": call_sid, "status": "in-progress"})


class TwilioTelephonyProvider(TelephonyProvider):
    """Production Twilio Voice API provider utilizing official REST API."""

    def __init__(self):
        self.account_sid = os.getenv("TWILIO_ACCOUNT_SID")
        self.auth_token = os.getenv("TWILIO_AUTH_TOKEN")
        self.caller_id = os.getenv("TWILIO_CALLER_ID", "+18005550199")

    def initiate_outbound_call(
        self,
        to_phone: str,
        from_phone: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        import httpx

        if not self.account_sid or not self.auth_token:
            logger.warning("Twilio credentials missing. Falling back to safe mock call.")
            return MockTelephonyProvider().initiate_outbound_call(to_phone, from_phone or self.caller_id, metadata)

        url = f"https://api.twilio.com/2010-04-01/Accounts/{self.account_sid}/Calls.json"
        effective_from = from_phone or self.caller_id
        twiml = "<Response><Say>Connecting your NovaCart support agent.</Say><Dial>" + to_phone + "</Dial></Response>"

        try:
            with httpx.Client(timeout=10.0) as client:
                res = client.post(
                    url,
                    auth=(self.account_sid, self.auth_token),
                    data={
                        "To": to_phone,
                        "From": effective_from,
                        "Twiml": twiml
                    }
                )
                if res.status_code in [200, 201]:
                    data = res.json()
                    return {
                        "call_sid": data.get("sid"),
                        "provider": "Twilio",
                        "status": data.get("status", "queued"),
                        "to_phone": to_phone,
                        "from_phone": effective_from,
                        "billable": True,
                        "initiated_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
                    }
                else:
                    logger.error(f"Twilio API error ({res.status_code}): {res.text}")
                    return {
                        "call_sid": f"CA-ERR-{uuid.uuid4().hex[:8]}",
                        "provider": "Twilio",
                        "status": "failed",
                        "error": res.text
                    }
        except Exception as e:
            logger.error(f"Failed to dial via Twilio: {e}")
            return {
                "call_sid": f"CA-ERR-{uuid.uuid4().hex[:8]}",
                "provider": "Twilio",
                "status": "failed",
                "error": str(e)
            }

    def get_call_status(self, call_sid: str) -> Dict[str, Any]:
        import httpx
        if not self.account_sid or not self.auth_token:
            return {"call_sid": call_sid, "status": "completed"}
        url = f"https://api.twilio.com/2010-04-01/Accounts/{self.account_sid}/Calls/{call_sid}.json"
        try:
            with httpx.Client(timeout=10.0) as client:
                res = client.get(url, auth=(self.account_sid, self.auth_token))
                if res.status_code == 200:
                    return res.json()
        except Exception:
            pass
        return {"call_sid": call_sid, "status": "unknown"}


def get_telephony_provider() -> TelephonyProvider:
    """Factory creating configured telephony adapter based on TELEPHONY_PROVIDER environment setting."""
    provider_name = os.getenv("TELEPHONY_PROVIDER", "mock").lower()
    if provider_name == "twilio":
        return TwilioTelephonyProvider()
    return MockTelephonyProvider()
