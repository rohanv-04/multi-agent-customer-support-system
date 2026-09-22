from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database.database import get_db
from ..database.models import User, Organization
from ..schemas.auth import (
    UserRole,
    Permission,
    UserLoginRequest,
    UserCreateRequest,
    UserRoleUpdateRequest,
    UserResponse,
    TokenResponse,
    OrganizationResponse
)
from ..services.auth_service import auth_service, JWT_EXPIRATION_SECONDS
from ..core.security import get_current_user, require_permission, require_role

router = APIRouter(prefix="/api/auth", tags=["Enterprise Authentication & RBAC"])


@router.post("/login", response_model=TokenResponse)
def login(request: UserLoginRequest, db: Session = Depends(get_db)):
    """Authenticate user with email/password and issue standard JWT access token."""
    res = auth_service.authenticate_user(
        db=db,
        email=request.email,
        password=request.password,
        org_id=request.organization_id
    )
    if not res:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials or inactive account"
        )
    user, token = res
    role_enum = UserRole(user.role)
    permissions = auth_service.get_permissions_for_role(role_enum)

    user_resp = UserResponse(
        id=user.id,
        email=user.email,
        name=user.name,
        role=role_enum,
        organization_id=user.organization_id,
        is_active=user.is_active,
        permissions=permissions,
        created_at=user.created_at
    )
    return TokenResponse(
        access_token=token,
        token_type="Bearer",
        expires_in=JWT_EXPIRATION_SECONDS,
        user=user_resp
    )


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    """Retrieve current authenticated user profile, assigned role, and resolved permissions."""
    role_enum = UserRole(current_user.role)
    permissions = auth_service.get_permissions_for_role(role_enum)
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        name=current_user.name,
        role=role_enum,
        organization_id=current_user.organization_id,
        is_active=current_user.is_active,
        permissions=permissions,
        created_at=current_user.created_at
    )


@router.post("/switch-role", response_model=TokenResponse)
def switch_role(
    role: UserRole,
    organization_id: str = "ORG-NOVACART",
    db: Session = Depends(get_db)
):
    """Demo & Evaluation Helper: Instantly issues JWT token for desired enterprise role and tenant."""
    user = db.query(User).filter(User.role == role.value, User.organization_id == organization_id).first()
    if not user:
        # Create on the fly if needed
        default_pwd = auth_service.hash_password("password123")
        user = User(
            id=f"USR-{role.value[:3]}-DEMO",
            organization_id=organization_id,
            email=f"{role.value.lower()}@{organization_id.lower().replace('org-', '')}.com",
            hashed_password=default_pwd,
            name=f"{role.value.title().replace('_', ' ')} Demo",
            role=role.value,
            is_active=True
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    permissions = auth_service.get_permissions_for_role(role)
    payload = {
        "sub": user.id,
        "email": user.email,
        "name": user.name,
        "role": user.role,
        "organization_id": user.organization_id,
        "permissions": permissions
    }
    token = auth_service.create_jwt_token(payload)

    user_resp = UserResponse(
        id=user.id,
        email=user.email,
        name=user.name,
        role=role,
        organization_id=user.organization_id,
        is_active=user.is_active,
        permissions=permissions,
        created_at=user.created_at
    )
    return TokenResponse(
        access_token=token,
        token_type="Bearer",
        expires_in=JWT_EXPIRATION_SECONDS,
        user=user_resp
    )


@router.get("/users", response_model=List[UserResponse])
def list_users(
    current_user: User = Depends(require_permission(Permission.MANAGE_USERS.value)),
    db: Session = Depends(get_db)
):
    """List all users within the current user's organization boundary (Requires MANAGE_USERS permission)."""
    users = db.query(User).filter(User.organization_id == current_user.organization_id).all()
    results = []
    for u in users:
        role_enum = UserRole(u.role)
        results.append(UserResponse(
            id=u.id,
            email=u.email,
            name=u.name,
            role=role_enum,
            organization_id=u.organization_id,
            is_active=u.is_active,
            permissions=auth_service.get_permissions_for_role(role_enum),
            created_at=u.created_at
        ))
    return results


@router.post("/users", response_model=UserResponse)
def create_user(
    request: UserCreateRequest,
    current_user: User = Depends(require_permission(Permission.MANAGE_USERS.value)),
    db: Session = Depends(get_db)
):
    """Create a new user within tenant (Requires MANAGE_USERS permission)."""
    # Force creation in caller's organization unless ADMIN
    org_id = current_user.organization_id
    if current_user.role == UserRole.ADMIN.value and request.organization_id:
        org_id = request.organization_id

    existing = db.query(User).filter(User.email.ilike(request.email.strip())).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"User with email '{request.email}' already exists"
        )

    req = UserCreateRequest(
        email=request.email,
        password=request.password,
        name=request.name,
        role=request.role,
        organization_id=org_id
    )
    new_user = auth_service.create_user(
        db=db,
        data=req,
        actor_id=current_user.id,
        actor_role=current_user.role
    )
    role_enum = UserRole(new_user.role)
    return UserResponse(
        id=new_user.id,
        email=new_user.email,
        name=new_user.name,
        role=role_enum,
        organization_id=new_user.organization_id,
        is_active=new_user.is_active,
        permissions=auth_service.get_permissions_for_role(role_enum),
        created_at=new_user.created_at
    )


@router.patch("/users/{user_id}/role", response_model=UserResponse)
def update_user_role(
    user_id: str,
    request: UserRoleUpdateRequest,
    current_user: User = Depends(require_permission(Permission.MANAGE_USERS.value)),
    db: Session = Depends(get_db)
):
    """Update role or active status for a tenant user (Requires MANAGE_USERS permission)."""
    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # Enforce tenant isolation
    if target_user.organization_id != current_user.organization_id and current_user.role != UserRole.ADMIN.value:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot modify user from another tenant")

    updated = auth_service.update_user_role(
        db=db,
        user_id=user_id,
        update=request,
        actor_id=current_user.id,
        actor_role=current_user.role
    )
    role_enum = UserRole(updated.role)
    return UserResponse(
        id=updated.id,
        email=updated.email,
        name=updated.name,
        role=role_enum,
        organization_id=updated.organization_id,
        is_active=updated.is_active,
        permissions=auth_service.get_permissions_for_role(role_enum),
        created_at=updated.created_at
    )


@router.get("/organizations", response_model=List[OrganizationResponse])
def list_organizations(
    db: Session = Depends(get_db)
):
    """List available tenant organizations."""
    orgs = db.query(Organization).all()
    return [OrganizationResponse.model_validate(o) for o in orgs]
