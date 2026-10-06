import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.session import Base
from app.db.seed import seed_database
from app.models.models import Commodity, Market, MarketPrice, User, ColdStore, FarmerSupply


def test_seed_database_idempotency():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)

    session = Session()
    # First seed run
    stats1 = seed_database(session)
    assert stats1["commodities"] == 1
    assert stats1["markets"] == 4
    assert stats1["cold_stores"] == 2
    assert stats1["farmers"] == 3

    # Second seed run must be idempotent (no duplicate constraints violated)
    stats2 = seed_database(session)
    assert session.query(Commodity).count() == 1
    assert session.query(Market).count() == 4
    assert session.query(ColdStore).count() == 2
    assert session.query(User).count() == 4  # 1 operator + 3 farmers

    session.close()
