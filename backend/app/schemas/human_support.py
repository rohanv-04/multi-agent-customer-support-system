from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field


class RepresentativeInfo(BaseModel):
    id: str = Field(..., description="Unique ID of the support representative")
    name: str = Field(..., description="Full display name of the representative")
    phone: str = Field(..., description="Direct contact phone number")
    available: bool = Field(default=True, description="Availability status")


class HumanSupportAssignmentRequest(BaseModel):
    customer_id: Optional[str] = Field(None, description="ID of the customer requesting human support")
    notes: Optional[str] = Field(None, description="Optional customer note or intent description")


class HumanSupportAssignmentResponse(BaseModel):
    assignment_id: str
    case_id: str
    customer_id: str
    representative: RepresentativeInfo
    assignment_method: str = "RANDOM"
    status: str = "ASSIGNED"
    assigned_at: datetime
    tel_link: str = Field(..., description="Formatted tel: link for phone dialer")


class CallInitiatedResponse(BaseModel):
    assignment_id: str
    case_id: str
    status: str = "CALL_INITIATED"
    recorded_at: datetime
    representative_name: str
    phone: str
    tel_link: str
