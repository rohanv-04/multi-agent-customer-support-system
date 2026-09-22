import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.database.database import init_db, SessionLocal
from backend.app.database.models import User, Organization, SupportCase, AuditLog, get_utc_now
from backend.app.services.auth_service import auth_service
from backend.app.schemas.auth import UserRole, Permission

client = TestClient(app)


@pytest.fixture(scope="module", autouse=True)
def setup_security_database():
    init_db()
    db = SessionLocal()
    now = get_utc_now()
    
    # Ensure Novacart and Acme tenant orgs exist
    if not db.query(Organization).filter(Organization.id == "ORG-NOVACART").first():
        db.add(Organization(id="ORG-NOVACART", name="NovaCart Enterprise", slug="novacart", plan_tier="Enterprise", created_at=now))
    if not db.query(Organization).filter(Organization.id == "ORG-ACME").first():
        db.add(Organization(id="ORG-ACME", name="Acme Corporation", slug="acmecorp", plan_tier="Enterprise", created_at=now))
    db.commit()

    # Seed test users for both tenants
    pwd = auth_service.hash_password("password123")
    users = [
        User(id="TEST-USR-ADMIN", organization_id="ORG-NOVACART", email="test_admin@novacart.com", hashed_password=pwd, name="Test Admin", role="ADMIN", is_active=True),
        User(id="TEST-USR-SUP", organization_id="ORG-NOVACART", email="test_sup@novacart.com", hashed_password=pwd, name="Test Supervisor", role="SUPERVISOR", is_active=True),
        User(id="TEST-USR-AGT", organization_id="ORG-NOVACART", email="test_agent@novacart.com", hashed_password=pwd, name="Test Agent", role="SUPPORT_AGENT", is_active=True),
        User(id="TEST-USR-CUST", organization_id="ORG-NOVACART", email="test_cust@novacart.com", hashed_password=pwd, name="Test Cust", role="CUSTOMER", is_active=True),
        # Acme Corp Tenant
        User(id="TEST-ACME-AGT", organization_id="ORG-ACME", email="test_acme_agent@acme.com", hashed_password=pwd, name="Acme Agent", role="SUPPORT_AGENT", is_active=True),
        User(id="TEST-ACME-CUST", organization_id="ORG-ACME", email="test_acme_cust@acme.com", hashed_password=pwd, name="Acme Cust", role="CUSTOMER", is_active=True),
    ]
    for u in users:
        existing = db.query(User).filter(User.id == u.id).first()
        if not existing:
            db.add(u)
    
    # Seed a case in Acme Corp tenant
    acme_case = db.query(SupportCase).filter(SupportCase.id == "CASE-ACME-001").first()
    if not acme_case:
        db.add(SupportCase(
            id="CASE-ACME-001",
            organization_id="ORG-ACME",
            customer_id="CUST2001",
            subject="Acme Router Firmware Issue",
            description="Router firmware 2.4 corrupted",
            priority="high",
            status="TRIAGING",
            created_at=now
        ))
    db.commit()
    db.close()


def get_token_for_user(user_id: str, email: str, role: str, org_id: str) -> str:
    perms = auth_service.get_permissions_for_role(UserRole(role))
    payload = {
        "sub": user_id,
        "email": email,
        "name": email.split("@")[0],
        "role": role,
        "organization_id": org_id,
        "permissions": perms
    }
    return auth_service.create_jwt_token(payload)


def test_password_hashing_and_verification():
    raw_pwd = "SuperSecretPassword2026!"
    hashed = auth_service.hash_password(raw_pwd)
    assert hashed.startswith("pbkdf2:sha256:")
    assert auth_service.verify_password(raw_pwd, hashed) is True
    assert auth_service.verify_password("WrongPassword", hashed) is False


def test_jwt_token_creation_and_validation():
    token = get_token_for_user("TEST-USR-ADMIN", "test_admin@novacart.com", "ADMIN", "ORG-NOVACART")
    decoded = auth_service.decode_jwt_token(token)
    assert decoded is not None
    assert decoded["sub"] == "TEST-USR-ADMIN"
    assert decoded["role"] == "ADMIN"
    assert decoded["organization_id"] == "ORG-NOVACART"
    assert "cases:view" in decoded["permissions"]
    assert "users:manage" in decoded["permissions"]

    # Invalid signature decode
    tampered = token[:-4] + "xyz1"
    assert auth_service.decode_jwt_token(tampered) is None


def test_login_api_and_audit_generation():
    # Valid Login
    res = client.post("/api/auth/login", json={
        "email": "test_admin@novacart.com",
        "password": "password123"
    })
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert data["user"]["role"] == "ADMIN"
    assert data["user"]["organization_id"] == "ORG-NOVACART"

    # Verify SEC_LOGIN audit log was written
    db = SessionLocal()
    login_log = db.query(AuditLog).filter(
        AuditLog.action == "SEC_LOGIN",
        AuditLog.actor_id == "TEST-USR-ADMIN"
    ).first()
    assert login_log is not None
    assert login_log.organization_id == "ORG-NOVACART"
    db.close()

    # Invalid Login
    fail_res = client.post("/api/auth/login", json={
        "email": "test_admin@novacart.com",
        "password": "wrong_password"
    })
    assert fail_res.status_code == 401


def test_unauthorized_access_rejection():
    # Protected endpoint without token or with invalid token
    res = client.get("/api/cases", headers={"Authorization": "Bearer invalid_garbage_token"})
    assert res.status_code == 401


def test_role_based_access_control_restrictions():
    # 1. CUSTOMER cannot view audit logs (requires 'audit:view')
    cust_token = get_token_for_user("TEST-USR-CUST", "test_cust@novacart.com", "CUSTOMER", "ORG-NOVACART")
    audit_res = client.get("/api/audit/logs", headers={"Authorization": f"Bearer {cust_token}"})
    assert audit_res.status_code == 403
    assert "Forbidden" in audit_res.json()["detail"]

    # 2. SUPPORT_AGENT cannot manage users (requires 'users:manage')
    agent_token = get_token_for_user("TEST-USR-AGT", "test_agent@novacart.com", "SUPPORT_AGENT", "ORG-NOVACART")
    user_res = client.get("/api/auth/users", headers={"Authorization": f"Bearer {agent_token}"})
    assert user_res.status_code == 403

    # 3. SUPERVISOR can view audit logs
    sup_token = get_token_for_user("TEST-USR-SUP", "test_sup@novacart.com", "SUPERVISOR", "ORG-NOVACART")
    sup_audit_res = client.get("/api/audit/logs", headers={"Authorization": f"Bearer {sup_token}"})
    assert sup_audit_res.status_code == 200

    # 4. ADMIN can view users and audit logs
    admin_token = get_token_for_user("TEST-USR-ADMIN", "test_admin@novacart.com", "ADMIN", "ORG-NOVACART")
    admin_users_res = client.get("/api/auth/users", headers={"Authorization": f"Bearer {admin_token}"})
    assert admin_users_res.status_code == 200


def test_cross_tenant_isolation():
    # 1. Novacart agent attempts to access Acme case -> 403 Forbidden
    novacart_token = get_token_for_user("TEST-USR-AGT", "test_agent@novacart.com", "SUPPORT_AGENT", "ORG-NOVACART")
    cross_res = client.get("/api/cases/CASE-ACME-001", headers={"Authorization": f"Bearer {novacart_token}"})
    assert cross_res.status_code == 403
    assert "restricted to organization" in cross_res.json()["detail"]

    # 2. Acme agent accessing Acme case -> 200 OK
    acme_token = get_token_for_user("TEST-ACME-AGT", "test_acme_agent@acme.com", "SUPPORT_AGENT", "ORG-ACME")
    acme_res = client.get("/api/cases/CASE-ACME-001", headers={"Authorization": f"Bearer {acme_token}"})
    assert acme_res.status_code == 200
    assert acme_res.json()["id"] == "CASE-ACME-001"

    # 3. List cases scoping: Acme agent sees only Acme cases
    list_res = client.get("/api/cases", headers={"Authorization": f"Bearer {acme_token}"})
    assert list_res.status_code == 200
    cases = list_res.json()
    assert all(c["organization_id"] == "ORG-ACME" for c in cases)


def test_permission_changes_and_user_management_audit():
    import uuid
    admin_token = get_token_for_user("TEST-USR-ADMIN", "test_admin@novacart.com", "ADMIN", "ORG-NOVACART")
    unique_email = f"ops_{uuid.uuid4().hex[:6]}@novacart.com"

    # Create new tenant user via API
    new_user_res = client.post("/api/auth/users", headers={"Authorization": f"Bearer {admin_token}"}, json={
        "email": unique_email,
        "name": "Ops Analyst",
        "password": "password123",
        "role": "SUPPORT_AGENT"
    })
    assert new_user_res.status_code == 200
    created_id = new_user_res.json()["id"]

    # Update role to SUPERVISOR
    patch_res = client.patch(f"/api/auth/users/{created_id}/role", headers={"Authorization": f"Bearer {admin_token}"}, json={
        "role": "SUPERVISOR",
        "is_active": True
    })
    assert patch_res.status_code == 200
    assert patch_res.json()["role"] == "SUPERVISOR"

    # Verify SEC_USER_MANAGEMENT and SEC_PERMISSION_CHANGE audit records
    db = SessionLocal()
    audit_entries = db.query(AuditLog).filter(AuditLog.entity_id == created_id).all()
    actions = [a.action for a in audit_entries]
    assert "SEC_USER_MANAGEMENT" in actions
    assert "SEC_PERMISSION_CHANGE" in actions
    db.close()
