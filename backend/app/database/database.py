import os
import json
import datetime
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from .models import (
    Base,
    get_utc_now,
    Organization,
    User,
    Customer,
    Order,
    Conversation,
    Message,
    SupportCase,
    CaseMessage,
    CaseEvent,
    AgentRun,
    AgentAction,
    EscalationTicket,
    AuditLog,
    CustomerMemory,
    KnowledgeDocument
)

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./novacart.db")

if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False}
    )
else:
    engine = create_engine(
        DATABASE_URL,
        pool_size=int(os.getenv("DB_POOL_SIZE", "10")),
        max_overflow=int(os.getenv("DB_MAX_OVERFLOW", "20")),
        pool_timeout=int(os.getenv("DB_POOL_TIMEOUT", "30")),
        pool_recycle=int(os.getenv("DB_POOL_RECYCLE", "1800")),
        pool_pre_ping=True
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def check_and_migrate_db():
    """Safely apply incremental SQLite schema updates to existing databases without data loss."""
    if not DATABASE_URL.startswith("sqlite"):
        return
    try:
        with engine.connect() as conn:
            # Check customers.organization_id
            cols_cust = [row[1] for row in conn.execute(text("PRAGMA table_info(customers)")).fetchall()]
            if "organization_id" not in cols_cust:
                conn.execute(text("ALTER TABLE customers ADD COLUMN organization_id VARCHAR(50) DEFAULT 'ORG-NOVACART'"))
                conn.commit()

            # Check agent_actions columns
            cols_actions = [row[1] for row in conn.execute(text("PRAGMA table_info(agent_actions)")).fetchall()]
            if "case_id" not in cols_actions:
                conn.execute(text("ALTER TABLE agent_actions ADD COLUMN case_id VARCHAR(50)"))
                conn.commit()
            if "requested_by" not in cols_actions:
                conn.execute(text("ALTER TABLE agent_actions ADD COLUMN requested_by VARCHAR(100)"))
                conn.commit()
            if "status" not in cols_actions:
                conn.execute(text("ALTER TABLE agent_actions ADD COLUMN status VARCHAR(50) DEFAULT 'completed'"))
                conn.commit()
            if "input_metadata" not in cols_actions:
                conn.execute(text("ALTER TABLE agent_actions ADD COLUMN input_metadata TEXT"))
                conn.commit()
            if "result_metadata" not in cols_actions:
                conn.execute(text("ALTER TABLE agent_actions ADD COLUMN result_metadata TEXT"))
                conn.commit()

            # Check escalations.case_id & organization_id
            cols_esc = [row[1] for row in conn.execute(text("PRAGMA table_info(escalations)")).fetchall()]
            if "case_id" not in cols_esc:
                conn.execute(text("ALTER TABLE escalations ADD COLUMN case_id VARCHAR(50)"))
                conn.commit()
            if "organization_id" not in cols_esc:
                conn.execute(text("ALTER TABLE escalations ADD COLUMN organization_id VARCHAR(50) DEFAULT 'ORG-NOVACART'"))
                conn.commit()

            # Check audit_logs.organization_id
            cols_audit = [row[1] for row in conn.execute(text("PRAGMA table_info(audit_logs)")).fetchall()]
            if "organization_id" not in cols_audit:
                conn.execute(text("ALTER TABLE audit_logs ADD COLUMN organization_id VARCHAR(50) DEFAULT 'ORG-NOVACART'"))
                conn.commit()
    except Exception as e:
        print(f"[Migration Notice]: {e}")

def init_db():
    Base.metadata.create_all(bind=engine)
    check_and_migrate_db()
    seed_demo_data()

def seed_demo_data():
    db = SessionLocal()
    try:
        now = get_utc_now()

        # Ensure default organization exists
        org = db.query(Organization).filter(Organization.id == "ORG-NOVACART").first()
        if not org:
            org = Organization(
                id="ORG-NOVACART",
                name="NovaCart Enterprise",
                slug="novacart",
                plan_tier="Enterprise",
                created_at=now
            )
            db.add(org)
            db.commit()

        # Ensure secondary tenant organization exists for multi-tenant testing
        acme_org = db.query(Organization).filter(Organization.id == "ORG-ACME").first()
        if not acme_org:
            acme_org = Organization(
                id="ORG-ACME",
                name="Acme Corporation",
                slug="acmecorp",
                plan_tier="Enterprise",
                created_at=now
            )
            db.add(acme_org)
            db.commit()

        # Seed Standard RBAC Users if not present
        if db.query(User).count() == 0:
            from ..services.auth_service import auth_service
            default_pwd = auth_service.hash_password("password123")
            demo_users = [
                User(id="USR-ADMIN-01", organization_id="ORG-NOVACART", email="admin@novacart.com", hashed_password=default_pwd, name="Alice Admin", role="ADMIN", is_active=True, created_at=now),
                User(id="USR-MGR-01", organization_id="ORG-NOVACART", email="manager@novacart.com", hashed_password=default_pwd, name="Mona Manager", role="MANAGER", is_active=True, created_at=now),
                User(id="USR-SUP-01", organization_id="ORG-NOVACART", email="supervisor@novacart.com", hashed_password=default_pwd, name="Sam Supervisor", role="SUPERVISOR", is_active=True, created_at=now),
                User(id="USR-AGT-01", organization_id="ORG-NOVACART", email="agent@novacart.com", hashed_password=default_pwd, name="Bob Agent", role="SUPPORT_AGENT", is_active=True, created_at=now),
                User(id="USR-CUST-01", organization_id="ORG-NOVACART", email="customer@novacart.com", hashed_password=default_pwd, name="Charlie Customer", role="CUSTOMER", is_active=True, created_at=now),
                # Tenant 2 (Acme Corp)
                User(id="USR-ACME-ADMIN", organization_id="ORG-ACME", email="acme_admin@acmecorp.com", hashed_password=default_pwd, name="Acme Admin", role="ADMIN", is_active=True, created_at=now),
                User(id="USR-ACME-AGT", organization_id="ORG-ACME", email="acme_agent@acmecorp.com", hashed_password=default_pwd, name="Acme Agent", role="SUPPORT_AGENT", is_active=True, created_at=now),
                User(id="USR-ACME-CUST", organization_id="ORG-ACME", email="acme_customer@acmecorp.com", hashed_password=default_pwd, name="Acme Customer", role="CUSTOMER", is_active=True, created_at=now),
            ]
            db.add_all(demo_users)
            db.commit()

        # Update existing customers with default organization_id if null
        db.query(Customer).filter(Customer.organization_id.is_(None)).update(
            {"organization_id": "ORG-NOVACART"}, synchronize_session=False
        )
        db.commit()

        # Seed Acme Corp tenant customer and order for cross-tenant testing if absent
        acme_cust = db.query(Customer).filter(Customer.customer_id == "CUST2001").first()
        if not acme_cust:
            acme_cust = Customer(
                customer_id="CUST2001",
                organization_id="ORG-ACME",
                name="Acme Client",
                email="client@acmecorp.com",
                phone="+1-555-0999",
                tier="Platinum",
                account_status="Active",
                created_at=now
            )
            db.add(acme_cust)
            acme_order = Order(
                order_id="ORD20001",
                customer_id="CUST2001",
                status="Shipped",
                items_json=json.dumps([{"item_id": "ITM-900", "name": "Acme Industrial Router", "qty": 1, "price": 1200.00}]),
                total_amount=1200.00,
                currency="USD",
                tracking_number="ACM-110099",
                carrier="NovaExpress",
                order_date=now - datetime.timedelta(days=2),
                expected_delivery=now + datetime.timedelta(days=1),
                delay_reason=None
            )
            db.add(acme_order)
            db.commit()

        # Check if customer demo data is already seeded
        if db.query(Customer).count() > 0:
            return

        # Seed Customers
        customers = [
            Customer(
                customer_id="CUST1001",
                organization_id="ORG-NOVACART",
                name="Alex Mercer",
                email="alex.mercer@example.com",
                phone="+1-555-0101",
                tier="Standard",
                account_status="Active"
            ),
            Customer(
                customer_id="CUST1002",
                organization_id="ORG-NOVACART",
                name="Elena Rostova",
                email="elena.rostova@example.com",
                phone="+1-555-0102",
                tier="Platinum",
                account_status="Active"
            ),
            Customer(
                customer_id="CUST1003",
                organization_id="ORG-NOVACART",
                name="Marcus Vance",
                email="marcus.vance@example.com",
                phone="+1-555-0103",
                tier="Gold",
                account_status="Active"
            ),
            Customer(
                customer_id="CUST1004",
                organization_id="ORG-NOVACART",
                name="Sarah Jenkins",
                email="sarah.j@example.com",
                phone="+1-555-0104",
                tier="Silver",
                account_status="Active"
            ),
            Customer(
                customer_id="CUST1005",
                organization_id="ORG-NOVACART",
                name="David Chen",
                email="david.chen@example.com",
                phone="+1-555-0105",
                tier="Standard",
                account_status="Active"
            ),
        ]
        db.add_all(customers)
        db.commit()

        # Seed Orders
        orders = [
            Order(
                order_id="ORD10001",
                customer_id="CUST1001",
                status="Shipped",
                items_json=json.dumps([
                    {"item_id": "ITM-901", "name": "Sony WH-1000XM5 Wireless Headphones", "qty": 1, "price": 349.99}
                ]),
                total_amount=349.99,
                currency="USD",
                tracking_number="FX-8849201",
                carrier="FedEx",
                order_date=now - datetime.timedelta(days=4),
                expected_delivery=now - datetime.timedelta(days=1),
                delay_reason="Minor weather delay in transit hub (within 1 day)"
            ),
            Order(
                order_id="ORD10002",
                customer_id="CUST1002",
                status="Delayed",
                items_json=json.dumps([
                    {"item_id": "ITM-402", "name": "Apple iPad Pro 11-inch M4 256GB", "qty": 1, "price": 499.00}
                ]),
                total_amount=499.00,
                currency="USD",
                tracking_number="NV-992014",
                carrier="NovaExpress",
                order_date=now - datetime.timedelta(days=8),
                expected_delivery=now - datetime.timedelta(days=4),
                delay_reason="Fulfillment center transit interruption - 4 days overdue (> 3 days policy threshold)"
            ),
            Order(
                order_id="ORD10003",
                customer_id="CUST1003",
                status="Delivered",
                items_json=json.dumps([
                    {"item_id": "ITM-205", "name": "Mechanical Gaming Keyboard RGB", "qty": 1, "price": 149.50}
                ]),
                total_amount=149.50,
                currency="USD",
                tracking_number="UPS-771234",
                carrier="UPS",
                order_date=now - datetime.timedelta(days=50),
                expected_delivery=now - datetime.timedelta(days=47),
                actual_delivery=now - datetime.timedelta(days=46),
                delay_reason=None
            ),
            Order(
                order_id="ORD10004",
                customer_id="CUST1004",
                status="Processing",
                items_json=json.dumps([
                    {"item_id": "ITM-310", "name": "Ergonomic Mesh Executive Chair", "qty": 1, "price": 289.00}
                ]),
                total_amount=289.00,
                currency="USD",
                tracking_number="NV-104921",
                carrier="NovaExpress",
                order_date=now - datetime.timedelta(hours=6),
                expected_delivery=now + datetime.timedelta(days=3),
                delay_reason=None
            ),
            Order(
                order_id="ORD10005",
                customer_id="CUST1005",
                status="Cancelled",
                items_json=json.dumps([
                    {"item_id": "ITM-550", "name": "Ultra-wide Curved Gaming Monitor 34-inch", "qty": 1, "price": 450.00}
                ]),
                total_amount=450.00,
                currency="USD",
                tracking_number=None,
                carrier=None,
                order_date=now - datetime.timedelta(days=10),
                expected_delivery=now - datetime.timedelta(days=6),
                delay_reason="Cancelled prior to shipment upon customer request"
            ),
        ]
        db.add_all(orders)
        db.commit()

        # Seed Initial Customer Memory
        memories = [
            CustomerMemory(
                customer_id="CUST1002",
                memory_type="preference",
                key="preferred_contact",
                value="Prefers swift automated resolution and email receipts."
            ),
            CustomerMemory(
                customer_id="CUST1002",
                memory_type="tier_note",
                key="vip_status",
                value="Platinum VIP member with >$3,500 lifetime spend. Expedited handling authorized."
            )
        ]
        db.add_all(memories)
        db.commit()

    finally:
        db.close()
