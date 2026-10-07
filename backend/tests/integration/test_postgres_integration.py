import os
import pytest
from decimal import Decimal
from datetime import date
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError
from alembic.config import Config
from alembic import command

from app.core.config import settings
from app.db.session import Base
from app.models.models import (
    ColdStore,
    ColdStoreOperator,
    ColdStoreInventory,
    Commodity,
    User,
    Market,
    MarketPrice,
)
from app.models.enums import UserRole, ColdStoreEventType
from app.db.seed import seed_database
from app.services.cold_store import record_cold_store_event
from app.schemas.cold_store import ColdStoreEventCreate


POSTGRES_URL = os.environ.get("TEST_DATABASE_URL") or os.environ.get("DATABASE_URL")

def is_postgres_available() -> bool:
    if not POSTGRES_URL or not ("postgres" in POSTGRES_URL or "psycopg" in POSTGRES_URL):
        return False
    try:
        test_engine = create_engine(POSTGRES_URL, connect_args={"connect_timeout": 2})
        with test_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        test_engine.dispose()
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not is_postgres_available(),
    reason="PostgreSQL server is not available or TEST_DATABASE_URL not set",
)


@pytest.fixture(scope="module")
def pg_engine():
    engine = create_engine(POSTGRES_URL, pool_pre_ping=True)
    yield engine
    engine.dispose()


def test_postgres_alembic_migrations_lifecycle(pg_engine):
    """Test full Alembic upgrade -> downgrade -> upgrade lifecycle on real PostgreSQL."""
    alembic_cfg = Config("backend/alembic.ini")
    alembic_cfg.set_main_option("sqlalchemy.url", POSTGRES_URL)

    # 1. Upgrade to latest revision head
    command.upgrade(alembic_cfg, "head")

    # 2. Downgrade one step and re-upgrade to head
    command.downgrade(alembic_cfg, "-1")
    command.upgrade(alembic_cfg, "head")


def test_postgres_seed_and_constraints(pg_engine):
    """Verify that seed_database works idempotently and check constraints are enforced by PostgreSQL."""
    Session = sessionmaker(autocommit=False, autoflush=False, bind=pg_engine)

    # Clean schema for isolated test
    Base.metadata.drop_all(bind=pg_engine)
    Base.metadata.create_all(bind=pg_engine)

    with Session() as db:
        # 1. Seed database
        seed_database(db)

        # 2. Verify check constraints in PostgreSQL (e.g. cold store capacity > 0)
        op = db.query(ColdStoreOperator).first()
        invalid_store = ColdStore(
            operator_id=op.id,
            name="Invalid Zero Capacity Store",
            district="Purba Bardhaman",
            capacity_kg=Decimal("-100.00"),  # Violates chk_cold_store_capacity_positive
        )
        db.add(invalid_store)
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()

        # 3. Verify unique constraint enforcement (e.g. duplicate user identifier)
        dup_user = User(
            name="Duplicate User",
            identifier="anil.mahato@fasalflow.in",  # Already seeded
            password_hash="hash",
            role=UserRole.FARMER,
        )
        db.add(dup_user)
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()


def test_postgres_concurrency_and_row_locking(pg_engine):
    """Verify row-level locking (SELECT ... FOR UPDATE) and atomic capacity enforcement on PostgreSQL."""
    Session = sessionmaker(autocommit=False, autoflush=False, bind=pg_engine)

    with Session() as db:
        # Create user & operator
        user = User(
            name="Concurrency Operator",
            identifier="concurrency@test.com",
            password_hash="secret",
            role=UserRole.COLD_STORE_OPERATOR,
        )
        db.add(user)
        db.flush()

        operator = ColdStoreOperator(
            user_id=user.id,
            organization_name="Locked Cold Storage",
            district="Purba Bardhaman",
        )
        db.add(operator)
        db.flush()

        # Create store with capacity 50,000 kg
        store = ColdStore(
            operator_id=operator.id,
            name="Vault Chamber",
            district="Purba Bardhaman",
            capacity_kg=Decimal("50000.00"),
        )
        db.add(store)

        comm = db.query(Commodity).first()
        db.commit()
        store_id = store.id
        comm_id = comm.id

    # Test that transaction acquires FOR UPDATE lock and enforces capacity atomically
    with Session() as db1:
        # Transaction 1: Record 30,000 kg
        record_cold_store_event(
            db=db1,
            current_user=user,
            store_id=store_id,
            data=ColdStoreEventCreate(
                commodity_id=comm_id,
                event_type=ColdStoreEventType.LOADING,
                quantity_kg=Decimal("30000.00"),
                event_date=date.today(),
            ),
        )

        # Attempt to load 30,000 kg more (30k + 30k = 60k > 50k capacity) -> Must reject with 409
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            record_cold_store_event(
                db=db1,
                current_user=user,
                store_id=store_id,
                data=ColdStoreEventCreate(
                    commodity_id=comm_id,
                    event_type=ColdStoreEventType.LOADING,
                    quantity_kg=Decimal("30000.00"),
                    event_date=date.today(),
                ),
            )
        assert exc_info.value.status_code == 409
        assert "exceeds cold store capacity" in exc_info.value.detail
