import os
import json
import datetime
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from .models import (
    Base,
    get_utc_now,
    Organization,
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

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
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

            # Check escalations.case_id
            cols_esc = [row[1] for row in conn.execute(text("PRAGMA table_info(escalations)")).fetchall()]
            if "case_id" not in cols_esc:
                conn.execute(text("ALTER TABLE escalations ADD COLUMN case_id VARCHAR(50)"))
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

        # Update existing customers with default organization_id if null
        db.query(Customer).filter(Customer.organization_id.is_(None)).update(
            {"organization_id": "ORG-NOVACART"}, synchronize_session=False
        )
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
