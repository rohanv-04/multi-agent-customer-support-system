from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from ..schemas.omnichannel import SupportRequest, ProviderMessageResponse, ChannelType


class BaseChannelProvider(ABC):
    """
    Abstract interface for omnichannel communication providers.
    Allows real external providers (e.g., Twilio, SendGrid, Webhooks) or mock providers
    to be swapped seamlessly without hardcoding channel-specific business logic into agents.
    """

    @property
    @abstractmethod
    def channel_type(self) -> ChannelType:
        """Returns the specific channel handled by this provider."""
        pass

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Returns human-readable name of the provider."""
        pass

    @abstractmethod
    def normalize_inbound(self, payload: Dict[str, Any], headers: Optional[Dict[str, str]] = None) -> SupportRequest:
        """
        Parses raw channel-specific webhook/payload into a normalized SupportRequest.
        """
        pass

    @abstractmethod
    def send_outbound(
        self,
        recipient: str,
        body: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ProviderMessageResponse:
        """
        Sends an outbound message to the customer over this provider's channel.
        """
        pass
