"""add declared and remaining quantity tracking to farmer supply

Revision ID: 3f829d10e5aa
Revises: 07044488077b
Create Date: 2026-10-06 22:42:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '3f829d10e5aa'
down_revision = '07044488077b'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Add declared_quantity_kg and remaining_quantity_kg columns
    op.add_column('farmer_supply', sa.Column('declared_quantity_kg', sa.Numeric(precision=12, scale=2), nullable=True))
    op.add_column('farmer_supply', sa.Column('remaining_quantity_kg', sa.Numeric(precision=12, scale=2), nullable=True))

    # 2. Backfill existing data from quantity_kg if present
    op.execute(
        "UPDATE farmer_supply "
        "SET declared_quantity_kg = quantity_kg, remaining_quantity_kg = quantity_kg "
        "WHERE declared_quantity_kg IS NULL"
    )

    # 3. Set columns to NOT NULL
    op.alter_column('farmer_supply', 'declared_quantity_kg', nullable=False)
    op.alter_column('farmer_supply', 'remaining_quantity_kg', nullable=False)

    # 4. Drop legacy quantity_kg column
    op.drop_column('farmer_supply', 'quantity_kg')

    # 5. Add check constraints
    op.create_check_constraint(
        'chk_farmer_supply_declared_qty_positive',
        'farmer_supply',
        'declared_quantity_kg > 0'
    )
    op.create_check_constraint(
        'chk_farmer_supply_remaining_qty_non_negative',
        'farmer_supply',
        'remaining_quantity_kg >= 0'
    )
    op.create_check_constraint(
        'chk_farmer_supply_remaining_lte_declared',
        'farmer_supply',
        'remaining_quantity_kg <= declared_quantity_kg'
    )


def downgrade() -> None:
    op.drop_constraint('chk_farmer_supply_remaining_lte_declared', 'farmer_supply', type_='check')
    op.drop_constraint('chk_farmer_supply_remaining_qty_non_negative', 'farmer_supply', type_='check')
    op.drop_constraint('chk_farmer_supply_declared_qty_positive', 'farmer_supply', type_='check')

    op.add_column('farmer_supply', sa.Column('quantity_kg', sa.Numeric(precision=12, scale=2), nullable=True))
    op.execute("UPDATE farmer_supply SET quantity_kg = remaining_quantity_kg WHERE quantity_kg IS NULL")
    op.alter_column('farmer_supply', 'quantity_kg', nullable=False)

    op.drop_column('farmer_supply', 'remaining_quantity_kg')
    op.drop_column('farmer_supply', 'declared_quantity_kg')
