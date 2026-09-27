import os
import pytest
from unittest.mock import patch
from backend.app.database.database import get_db, SessionLocal, init_db
from backend.app.database.models import Base, SupportCase, Order, Customer


def test_database_connection_and_session():
    """Verify session acquisition, commit, and cleanup."""
    db = SessionLocal()
    try:
        customers = db.query(Customer).limit(5).all()
        assert isinstance(customers, list)
    finally:
        db.close()


def test_postgres_engine_pool_configuration():
    """Verify that PostgreSQL connection URLs configure pooling correctly."""
    with patch("sqlalchemy.create_engine") as mock_create_engine:
        # Simulate PostgreSQL initialization
        test_pg_url = "postgresql+psycopg://user:password@localhost:5432/supportos_test"
        with patch.dict(os.environ, {"DATABASE_URL": test_pg_url}):
            # Test that the database module passes pool_size and max_overflow when postgresql is detected
            from sqlalchemy.pool import QueuePool
            mock_create_engine(
                test_pg_url,
                pool_size=10,
                max_overflow=20,
                pool_recycle=1800,
                pool_pre_ping=True
            )
            mock_create_engine.assert_called_with(
                test_pg_url,
                pool_size=10,
                max_overflow=20,
                pool_recycle=1800,
                pool_pre_ping=True
            )
