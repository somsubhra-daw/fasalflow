from datetime import datetime, date
from decimal import Decimal
from typing import List, Optional
from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    CheckConstraint,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import relationship

from app.db.session import Base
from app.models.enums import (
    UserRole,
    SupplyStatus,
    BuyerType,
    DemandStatus,
    ColdStoreEventType,
)


# =====================================================================
# 1. USERS
# =====================================================================
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), nullable=False)
    # email or phone used as unique login identifier
    identifier = Column(String(150), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(SAEnum(UserRole, name="user_role_enum", native_enum=False), nullable=False, index=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    farmer_profile = relationship("Farmer", back_populates="user", uselist=False, cascade="all, delete-orphan")
    operator_profile = relationship("ColdStoreOperator", back_populates="user", uselist=False, cascade="all, delete-orphan")


# =====================================================================
# 2. COMMODITIES
# =====================================================================
class Commodity(Base):
    __tablename__ = "commodities"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    code = Column(String(50), unique=True, nullable=False, index=True)
    default_unit = Column(String(20), default="kg", nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    supplies = relationship("FarmerSupply", back_populates="commodity")
    demands = relationship("BuyerDemand", back_populates="commodity")
    market_prices = relationship("MarketPrice", back_populates="commodity")
    market_arrivals = relationship("MarketArrival", back_populates="commodity")
    cold_store_inventory = relationship("ColdStoreInventory", back_populates="commodity")


# =====================================================================
# 3. FARMERS & FARMS
# =====================================================================
class Farmer(Base):
    __tablename__ = "farmers"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    district = Column(String(100), nullable=False, index=True)
    block = Column(String(100), nullable=True)
    village = Column(String(100), nullable=True)
    phone = Column(String(20), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    user = relationship("User", back_populates="farmer_profile")
    farms = relationship("Farm", back_populates="farmer", cascade="all, delete-orphan")


class Farm(Base):
    __tablename__ = "farms"

    id = Column(Integer, primary_key=True, index=True)
    farmer_id = Column(Integer, ForeignKey("farmers.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(150), nullable=False)
    district = Column(String(100), nullable=False)
    block = Column(String(100), nullable=True)
    village = Column(String(100), nullable=True)
    latitude = Column(Numeric(9, 6), nullable=True)
    longitude = Column(Numeric(9, 6), nullable=True)
    area_acres = Column(Numeric(8, 2), nullable=True)
    irrigation_type = Column(String(50), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    farmer = relationship("Farmer", back_populates="farms")
    supplies = relationship("FarmerSupply", back_populates="farm", cascade="all, delete-orphan")


# =====================================================================
# 4. FARMER SUPPLY
# =====================================================================
class FarmerSupply(Base):
    __tablename__ = "farmer_supply"

    id = Column(Integer, primary_key=True, index=True)
    farm_id = Column(Integer, ForeignKey("farms.id", ondelete="CASCADE"), nullable=False, index=True)
    commodity_id = Column(Integer, ForeignKey("commodities.id", ondelete="RESTRICT"), nullable=False, index=True)
    quantity_kg = Column(Numeric(12, 2), nullable=False)
    expected_harvest_date = Column(Date, nullable=False, index=True)
    quality_grade = Column(String(20), default="A", nullable=False)
    status = Column(SAEnum(SupplyStatus, name="supply_status_enum", native_enum=False), default=SupplyStatus.PLANNED, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    farm = relationship("Farm", back_populates="supplies")
    commodity = relationship("Commodity", back_populates="supplies")

    __table_args__ = (
        CheckConstraint("quantity_kg > 0", name="chk_farmer_supply_quantity_positive"),
        Index("idx_farmer_supply_farm_commodity", "farm_id", "commodity_id"),
        Index("idx_farmer_supply_harvest_commodity", "commodity_id", "expected_harvest_date"),
    )


# =====================================================================
# 5. COLD STORE OPERATOR & COLD STORES
# =====================================================================
class ColdStoreOperator(Base):
    __tablename__ = "cold_store_operators"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    organization_name = Column(String(200), nullable=False)
    district = Column(String(100), nullable=False)
    address = Column(String(255), nullable=True)
    phone = Column(String(20), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    user = relationship("User", back_populates="operator_profile")
    cold_stores = relationship("ColdStore", back_populates="operator", cascade="all, delete-orphan")


class ColdStore(Base):
    __tablename__ = "cold_stores"

    id = Column(Integer, primary_key=True, index=True)
    operator_id = Column(Integer, ForeignKey("cold_store_operators.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(200), nullable=False)
    district = Column(String(100), nullable=False, index=True)
    block = Column(String(100), nullable=True)
    village = Column(String(100), nullable=True)
    address = Column(String(255), nullable=True)
    latitude = Column(Numeric(9, 6), nullable=True)
    longitude = Column(Numeric(9, 6), nullable=True)
    capacity_kg = Column(Numeric(14, 2), nullable=False)
    active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    operator = relationship("ColdStoreOperator", back_populates="cold_stores")
    events = relationship("ColdStoreEvent", back_populates="cold_store", cascade="all, delete-orphan")
    inventories = relationship("ColdStoreInventory", back_populates="cold_store", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint("capacity_kg > 0", name="chk_cold_store_capacity_positive"),
    )


# Read-optimized current inventory balance per cold store & commodity
class ColdStoreInventory(Base):
    __tablename__ = "cold_store_inventory"

    id = Column(Integer, primary_key=True, index=True)
    cold_store_id = Column(Integer, ForeignKey("cold_stores.id", ondelete="CASCADE"), nullable=False, index=True)
    commodity_id = Column(Integer, ForeignKey("commodities.id", ondelete="RESTRICT"), nullable=False, index=True)
    current_quantity_kg = Column(Numeric(14, 2), default=0, nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    cold_store = relationship("ColdStore", back_populates="inventories")
    commodity = relationship("Commodity", back_populates="cold_store_inventory")

    __table_args__ = (
        UniqueConstraint("cold_store_id", "commodity_id", name="uq_cold_store_commodity_inventory"),
        CheckConstraint("current_quantity_kg >= 0", name="chk_cold_store_inventory_non_negative"),
    )


# Immutable cold store events for audit trail
class ColdStoreEvent(Base):
    __tablename__ = "cold_store_events"

    id = Column(Integer, primary_key=True, index=True)
    cold_store_id = Column(Integer, ForeignKey("cold_stores.id", ondelete="CASCADE"), nullable=False, index=True)
    commodity_id = Column(Integer, ForeignKey("commodities.id", ondelete="RESTRICT"), nullable=False, index=True)
    event_type = Column(SAEnum(ColdStoreEventType, name="cold_store_event_type_enum", native_enum=False), nullable=False)
    quantity_kg = Column(Numeric(12, 2), nullable=False)
    event_date = Column(Date, nullable=False)
    reference = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    cold_store = relationship("ColdStore", back_populates="events")

    __table_args__ = (
        CheckConstraint("quantity_kg > 0", name="chk_cold_store_event_quantity_positive"),
        Index("idx_cold_store_event_query", "cold_store_id", "commodity_id", "event_date"),
    )


# =====================================================================
# 6. BUYERS & BUYER DEMAND
# =====================================================================
class Buyer(Base):
    __tablename__ = "buyers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), nullable=False)
    buyer_type = Column(SAEnum(BuyerType, name="buyer_type_enum", native_enum=False), default=BuyerType.WHOLESALER, nullable=False)
    district = Column(String(100), nullable=False, index=True)
    latitude = Column(Numeric(9, 6), nullable=True)
    longitude = Column(Numeric(9, 6), nullable=True)
    phone = Column(String(20), nullable=True)
    active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    demands = relationship("BuyerDemand", back_populates="buyer", cascade="all, delete-orphan")


class BuyerDemand(Base):
    __tablename__ = "buyer_demand"

    id = Column(Integer, primary_key=True, index=True)
    buyer_id = Column(Integer, ForeignKey("buyers.id", ondelete="CASCADE"), nullable=False, index=True)
    commodity_id = Column(Integer, ForeignKey("commodities.id", ondelete="RESTRICT"), nullable=False, index=True)
    quantity_kg = Column(Numeric(12, 2), nullable=False)
    required_from = Column(Date, nullable=False, index=True)
    required_until = Column(Date, nullable=False, index=True)
    quality_grade = Column(String(20), default="A", nullable=False)
    max_price_per_kg = Column(Numeric(10, 2), nullable=False)
    status = Column(SAEnum(DemandStatus, name="demand_status_enum", native_enum=False), default=DemandStatus.ACTIVE, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    buyer = relationship("Buyer", back_populates="demands")
    commodity = relationship("Commodity", back_populates="demands")

    __table_args__ = (
        CheckConstraint("quantity_kg > 0", name="chk_buyer_demand_quantity_positive"),
        CheckConstraint("max_price_per_kg >= 0", name="chk_buyer_demand_price_non_negative"),
        CheckConstraint("required_until >= required_from", name="chk_buyer_demand_date_window"),
        Index("idx_buyer_demand_commodity_dates", "commodity_id", "required_from", "required_until"),
    )


# =====================================================================
# 7. MARKETS, PRICES, ARRIVALS
# =====================================================================
class Market(Base):
    __tablename__ = "markets"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), nullable=False)
    district = Column(String(100), nullable=False, index=True)
    block = Column(String(100), nullable=True)
    latitude = Column(Numeric(9, 6), nullable=True)
    longitude = Column(Numeric(9, 6), nullable=True)
    active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    prices = relationship("MarketPrice", back_populates="market", cascade="all, delete-orphan")
    arrivals = relationship("MarketArrival", back_populates="market", cascade="all, delete-orphan")


class MarketPrice(Base):
    __tablename__ = "market_prices"

    id = Column(Integer, primary_key=True, index=True)
    market_id = Column(Integer, ForeignKey("markets.id", ondelete="CASCADE"), nullable=False, index=True)
    commodity_id = Column(Integer, ForeignKey("commodities.id", ondelete="RESTRICT"), nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)
    min_price_per_kg = Column(Numeric(10, 2), nullable=False)
    modal_price_per_kg = Column(Numeric(10, 2), nullable=False)
    max_price_per_kg = Column(Numeric(10, 2), nullable=False)
    source = Column(String(50), default="synthetic", nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    market = relationship("Market", back_populates="prices")
    commodity = relationship("Commodity", back_populates="market_prices")

    __table_args__ = (
        CheckConstraint("min_price_per_kg >= 0", name="chk_market_price_min_non_negative"),
        CheckConstraint("modal_price_per_kg >= min_price_per_kg", name="chk_market_price_modal_gte_min"),
        CheckConstraint("max_price_per_kg >= modal_price_per_kg", name="chk_market_price_max_gte_modal"),
        UniqueConstraint("market_id", "commodity_id", "date", name="uq_market_commodity_date_price"),
        Index("idx_market_price_lookup", "commodity_id", "market_id", "date"),
    )


class MarketArrival(Base):
    __tablename__ = "market_arrivals"

    id = Column(Integer, primary_key=True, index=True)
    market_id = Column(Integer, ForeignKey("markets.id", ondelete="CASCADE"), nullable=False, index=True)
    commodity_id = Column(Integer, ForeignKey("commodities.id", ondelete="RESTRICT"), nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)
    quantity_kg = Column(Numeric(12, 2), nullable=False)
    source = Column(String(50), default="synthetic", nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    market = relationship("Market", back_populates="arrivals")
    commodity = relationship("Commodity", back_populates="market_arrivals")

    __table_args__ = (
        CheckConstraint("quantity_kg >= 0", name="chk_market_arrival_quantity_non_negative"),
        UniqueConstraint("market_id", "commodity_id", "date", name="uq_market_commodity_date_arrival"),
        Index("idx_market_arrival_lookup", "commodity_id", "market_id", "date"),
    )
