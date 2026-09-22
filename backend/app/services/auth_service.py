import os
import hmac
import hashlib
import base64
import json
import time
import datetime
from typing import Optional, Dict, Any, List, Tuple
from sqlalchemy.orm import Session

from ..database.models import User, Organization, AuditLog, get_utc_now
from ..schemas.auth import (
    UserRole,
    Permission,
    ROLE_PERMISSIONS,
    TokenPayload,
    UserCreateRequest,
    UserRoleUpdateRequest,
    UserResponse,
    TokenResponse,
    SecurityAuditEntry
)

# JWT Secret Key
JWT_SECRET = os.getenv("JWT_SECRET", "supportos-super-secret-enterprise-signing-key-2026")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_SECONDS = 86400 * 7  # 7 days


class AuthService:
    """Enterprise authentication and RBAC service.

    Handles cryptographic password hashing, standard HS256 JWT issuance and validation,
    role-based permission resolution, multi-tenant isolation, and immutable security audit logs.
    """

    # ------------------ Password Cryptography ------------------
    @staticmethod
    def hash_password(password: str) -> str:
        """Secure PBKDF2-HMAC-SHA256 password hashing with random salt."""
        salt = os.urandom(16)
        iterations = 100000
        key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
        return f"pbkdf2:sha256:{iterations}${salt.hex()}${key.hex()}"

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify plain password against PBKDF2 hash."""
        try:
            if not hashed_password or not hashed_password.startswith("pbkdf2:sha256:"):
                # Dev fallback if plain text password exists
                return plain_password == hashed_password
            parts = hashed_password.split("$")
            if len(parts) != 3:
                return False
            header, salt_hex, key_hex = parts
            iterations = int(header.split(":")[2])
            salt = bytes.fromhex(salt_hex)
            expected_key = bytes.fromhex(key_hex)
            actual_key = hashlib.pbkdf2_hmac("sha256", plain_password.encode("utf-8"), salt, iterations)
            return hmac.compare_digest(actual_key, expected_key)
        except Exception:
            return False

    # ------------------ JWT Cryptography (HS256) ------------------
    @staticmethod
    def _b64_url_encode(data: bytes) -> str:
        return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")

    @staticmethod
    def _b64_url_decode(s: str) -> bytes:
        padding = "=" * (4 - (len(s) % 4)) if (len(s) % 4) != 0 else ""
        return base64.urlsafe_b64decode((s + padding).encode("utf-8"))

    @classmethod
    def create_jwt_token(cls, payload_dict: Dict[str, Any], expires_in: int = JWT_EXPIRATION_SECONDS) -> str:
        """Generates RFC 7519 compliant standard JSON Web Token signed with HMAC-SHA256."""
        header = {"alg": JWT_ALGORITHM, "typ": "JWT"}
        exp = int(time.time()) + expires_in
        payload = {**payload_dict, "exp": exp, "iat": int(time.time())}

        header_b64 = cls._b64_url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
        payload_b64 = cls._b64_url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
        signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")

        signature = hmac.new(JWT_SECRET.encode("utf-8"), signing_input, hashlib.sha256).digest()
        sig_b64 = cls._b64_url_encode(signature)

        return f"{header_b64}.{payload_b64}.{sig_b64}"

    @classmethod
    def decode_jwt_token(cls, token: str) -> Optional[Dict[str, Any]]:
        """Validates and decodes JWT signature and expiration."""
        try:
            parts = token.split(".")
            if len(parts) != 3:
                return None
            header_b64, payload_b64, sig_b64 = parts

            signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")
            expected_signature = hmac.new(JWT_SECRET.encode("utf-8"), signing_input, hashlib.sha256).digest()
            actual_signature = cls._b64_url_decode(sig_b64)

            if not hmac.compare_digest(actual_signature, expected_signature):
                return None

            payload = json.loads(cls._b64_url_decode(payload_b64).decode("utf-8"))
            if payload.get("exp") and payload["exp"] < time.time():
                return None  # Token expired

            return payload
        except Exception:
            return None

    # ------------------ RBAC & Permissions ------------------
    @staticmethod
    def get_permissions_for_role(role: UserRole) -> List[str]:
        """Resolves list of string permission codes for a given role."""
        perms = ROLE_PERMISSIONS.get(role, [])
        return [p.value for p in perms]

    @classmethod
    def has_permission(cls, user_role: UserRole, required_permission: str) -> bool:
        """Determines if a user role holds the required permission."""
        perms = cls.get_permissions_for_role(user_role)
        return required_permission in perms

    # ------------------ User Operations ------------------
    @classmethod
    def authenticate_user(
        cls, db: Session, email: str, password: str, org_id: Optional[str] = None
    ) -> Optional[Tuple[User, str]]:
        """Authenticates user credentials, validates tenant assignment, and issues signed JWT."""
        query = db.query(User).filter(User.email.ilike(email), User.is_active == True)
        if org_id:
            query = query.filter(User.organization_id == org_id)

        user = query.first()
        if not user:
            return None

        if not cls.verify_password(password, user.hashed_password):
            return None

        # Build token payload
        role_enum = UserRole(user.role)
        permissions = cls.get_permissions_for_role(role_enum)
        payload = {
            "sub": user.id,
            "email": user.email,
            "name": user.name,
            "role": user.role,
            "organization_id": user.organization_id,
            "permissions": permissions
        }
        token = cls.create_jwt_token(payload)

        # Log security audit event
        cls.log_security_audit(
            db=db,
            event_type="LOGIN",
            actor_id=user.id,
            actor_role=user.role,
            organization_id=user.organization_id,
            target_entity="User",
            target_id=user.id,
            action_summary=f"User {user.email} successfully logged in as {user.role}",
            details={"email": user.email, "role": user.role, "tenant": user.organization_id}
        )

        return user, token

    @classmethod
    def create_user(
        cls,
        db: Session,
        data: UserCreateRequest,
        actor_id: str = "SYSTEM",
        actor_role: str = "ADMIN"
    ) -> User:
        """Creates a new enterprise user assigned to an organization."""
        org_id = data.organization_id or "ORG-NOVACART"
        
        # Verify organization exists
        org = db.query(Organization).filter(Organization.id == org_id).first()
        if not org:
            org = Organization(
                id=org_id,
                name=org_id.replace("ORG-", "").title() + " Enterprise",
                slug=org_id.lower(),
                plan_tier="Enterprise",
                created_at=get_utc_now()
            )
            db.add(org)
            db.commit()

        user_id = f"USR-{os.urandom(4).hex().upper()}"
        user = User(
            id=user_id,
            organization_id=org_id,
            email=data.email.lower().strip(),
            hashed_password=cls.hash_password(data.password),
            name=data.name,
            role=data.role.value,
            is_active=True,
            created_at=get_utc_now()
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        # Log audit entry
        cls.log_security_audit(
            db=db,
            event_type="USER_MANAGEMENT",
            actor_id=actor_id,
            actor_role=actor_role,
            organization_id=org_id,
            target_entity="User",
            target_id=user.id,
            action_summary=f"Created user {user.email} with role {user.role} in tenant {org_id}",
            details={"email": user.email, "role": user.role, "user_id": user.id}
        )

        return user

    @classmethod
    def update_user_role(
        cls,
        db: Session,
        user_id: str,
        update: UserRoleUpdateRequest,
        actor_id: str,
        actor_role: str
    ) -> Optional[User]:
        """Updates a user's role or activation status and records an audit log."""
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return None

        old_role = user.role
        user.role = update.role.value
        if update.is_active is not None:
            user.is_active = update.is_active

        db.commit()
        db.refresh(user)

        cls.log_security_audit(
            db=db,
            event_type="PERMISSION_CHANGE",
            actor_id=actor_id,
            actor_role=actor_role,
            organization_id=user.organization_id,
            target_entity="User",
            target_id=user.id,
            action_summary=f"Changed user {user.email} role from {old_role} to {user.role}",
            details={"old_role": old_role, "new_role": user.role, "is_active": user.is_active}
        )
        return user

    @staticmethod
    def log_security_audit(
        db: Session,
        event_type: str,
        actor_id: str,
        actor_role: str,
        organization_id: str,
        target_entity: str,
        target_id: str,
        action_summary: str,
        details: Optional[Dict[str, Any]] = None
    ) -> AuditLog:
        """Persists immutable security audit record for compliance and forensics."""
        log = AuditLog(
            organization_id=organization_id,
            case_id=target_id if target_entity == "SupportCase" else None,
            entity_type=target_entity,
            entity_id=target_id,
            action=f"SEC_{event_type.upper()}",
            actor_type=actor_role.lower(),
            actor_id=actor_id,
            details_json=json.dumps({
                "event_type": event_type,
                "summary": action_summary,
                "extra": details or {},
                "timestamp": get_utc_now().isoformat()
            }),
            created_at=get_utc_now()
        )
        db.add(log)
        try:
            db.commit()
        except Exception:
            db.rollback()
        return log


auth_service = AuthService()
