"""clean redundant indexes on primary keys and composite leading columns

Revision ID: c5e9f8a12345
Revises: 3f829d10e5aa
Create Date: 2026-10-06 22:52:30.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c5e9f8a12345'
down_revision = '3f829d10e5aa'
branch_labels = None
depends_on = None


# Tables and redundant primary key indexes
PK_INDEXES = [
    ('ix_users_id', 'users'),
    ('ix_commodities_id', 'commodities'),
    ('ix_farmers_id', 'farmers'),
    ('ix_farms_id', 'farms'),
    ('ix_farmer_supply_id', 'farmer_supply'),
    ('ix_cold_store_operators_id', 'cold_store_operators'),
    ('ix_cold_stores_id', 'cold_stores'),
    ('ix_cold_store_inventory_id', 'cold_store_inventory'),
    ('ix_cold_store_events_id', 'cold_store_events'),
    ('ix_buyers_id', 'buyers'),
    ('ix_buyer_demand_id', 'buyer_demand'),
    ('ix_markets_id', 'markets'),
    ('ix_market_prices_id', 'market_prices'),
    ('ix_market_arrivals_id', 'market_arrivals'),
]

# Redundant single-column indexes covered by composite indexes or unique constraints
COMPOSITE_COVERED_INDEXES = [
    ('ix_farmer_supply_farm_id', 'farmer_supply', ['farm_id']),
    ('ix_farmer_supply_commodity_id', 'farmer_supply', ['commodity_id']),
    ('ix_cold_store_events_cold_store_id', 'cold_store_events', ['cold_store_id']),
    ('ix_buyer_demand_commodity_id', 'buyer_demand', ['commodity_id']),
    ('ix_market_prices_market_id', 'market_prices', ['market_id']),
    ('ix_market_prices_commodity_id', 'market_prices', ['commodity_id']),
    ('ix_market_arrivals_market_id', 'market_arrivals', ['market_id']),
    ('ix_market_arrivals_commodity_id', 'market_arrivals', ['commodity_id']),
]


def upgrade() -> None:
    # 1. Drop redundant primary key indexes
    for idx_name, table_name in PK_INDEXES:
        op.drop_index(idx_name, table_name=table_name, if_exists=True)

    # 2. Drop redundant single-column indexes covered by composites
    for idx_name, table_name, _ in COMPOSITE_COVERED_INDEXES:
        op.drop_index(idx_name, table_name=table_name, if_exists=True)


def downgrade() -> None:
    # 1. Re-create single-column covered indexes
    for idx_name, table_name, cols in COMPOSITE_COVERED_INDEXES:
        op.create_index(idx_name, table_name, cols, unique=False)

    # 2. Re-create primary key indexes
    for idx_name, table_name in PK_INDEXES:
        op.create_index(idx_name, table_name, ['id'], unique=False)
