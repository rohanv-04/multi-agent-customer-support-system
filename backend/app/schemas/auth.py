import datetime
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, EmailStr, Field


class UserRole(str, Enum):
    CUSTOMER = "CUSTOMER"
    SUPPORT_AGENT = "SUPPORT_AGENT"
    SUPERVISOR = "SUPERVISOR"
    MANAGER = "MANAGER"
    ADMIN = "ADMIN"


class Permission(str, Enum):
    VIEW_CASES = "cases:view"
    MODIFY_CASES = "cases:modify"
    EXECUTE_ACTIONS = "actions:execute"
    APPROVE_ACTIONS = "actions:approve"
    VIEW_CUSTOMER_DATA = "customer:view"
    VIEW_ANALYTICS = "analytics:view"
    MODIFY_POLICIES = "policies:modify"
    VIEW_AUDIT_LOGS = "audit:view"
    MANAGE_USERS = "users:manage"
    MANAGE_ORG_SETTINGS = "org:manage"


# Role-to-Permissions Mapping Definition
ROLE_PERMISSIONS: Dict[UserRole, List[Permission]] = {
    UserRole.CUSTOMER: [
        Permission.VIEW_CASES,
        Permission.VIEW_CUSTOMER_DATA,
    ],
    UserRole.SUPPORT_AGENT: [
        Permission.VIEW_CASES,
        Permission.MODIFY_CASES,
        Permission.EXECUTE_ACTIONS,
        Permission.VIEW_CUSTOMER_DATA,
    ],
    UserRole.SUPERVISOR: [
        Permission.VIEW_CASES,
        Permission.MODIFY_CASES,
        Permission.EXECUTE_ACTIONS,
        Permission.APPROVE_ACTIONS,
        Permission.VIEW_CUSTOMER_DATA,
        Permission.VIEW_ANALYTICS,
        Permission.VIEW_AUDIT_LOGS,
    ],
    UserRole.MANAGER: [
        Permission.VIEW_CASES,
        Permission.MODIFY_CASES,
        Permission.EXECUTE_ACTIONS,
        Permission.APPROVE_ACTIONS,
        Permission.VIEW_CUSTOMER_DATA,
        Permission.VIEW_ANALYTICS,
        Permission.VIEW_AUDIT_LOGS,
        Permission.MODIFY_POLICIES,
        Permission.MANAGE_USERS,
    ],
    UserRole.ADMIN: [
        Permission.VIEW_CASES,
        Permission.MODIFY_CASES,
        Permission.EXECUTE_ACTIONS,
        Permission.APPROVE_ACTIONS,
        Permission.VIEW_CUSTOMER_DATA,
        Permission.VIEW_ANALYTICS,
        Permission.VIEW_AUDIT_LOGS,
        Permission.MODIFY_POLICIES,
        Permission.MANAGE_USERS,
        Permission.MANAGE_ORG_SETTINGS,
    ],
}


class TokenPayload(BaseModel):
    sub: str  # User ID
    email: str
    name: str
    role: UserRole
    organization_id: str
    permissions: List[str]
    exp: Optional[int] = None


class UserLoginRequest(BaseModel):
    email: str
    password: str
    organization_id: Optional[str] = None


class UserCreateRequest(BaseModel):
    email: str
    password: str
    name: str
    role: UserRole = UserRole.SUPPORT_AGENT
    organization_id: Optional[str] = None


class UserRoleUpdateRequest(BaseModel):
    role: UserRole
    is_active: Optional[bool] = None


from pydantic import BaseModel, EmailStr, Field, ConfigDict


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: str
    name: str
    role: UserRole
    organization_id: str
    is_active: bool
    permissions: List[str] = []
    created_at: datetime.datetime


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "Bearer"
    expires_in: int
    user: UserResponse


class OrganizationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    slug: str
    plan_tier: str
    created_at: datetime.datetime


class SecurityAuditEntry(BaseModel):
    event_type: str  # LOGIN, PERMISSION_CHANGE, SENSITIVE_ACTION, APPROVAL, POLICY_CHANGE, USER_MANAGEMENT
    actor_id: str
    actor_role: str
    organization_id: str
    target_entity: str
    target_id: str
    action_summary: str
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)
