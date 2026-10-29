"""create_material_inventory_tables

Revision ID: e5b2c9a1d3f4
Revises: b1e4c8f0a2d5
Create Date: 2026-10-14 18:00:00.000000

Material Inventory Batch 2:
- Create material_stocks table to track available consumable quantities per client site.
- Enforce non-negative quantity check constraint and unique (site_id, material_id).
- Create material_stock_movements append-only audit ledger for stock changes.
- Movement types constrained to: inward, consumed, returned, adjustment.
- Positive movement quantity, non-negative balance_after, unique idempotency key.
- Safe downgrade protection preventing silent data loss of populated inventory or movements.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e5b2c9a1d3f4'
down_revision: Union[str, Sequence[str], None] = 'b1e4c8f0a2d5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create material_stocks table
    op.create_table(
        'material_stocks',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('site_id', sa.UUID(), nullable=False),
        sa.Column('material_id', sa.UUID(), nullable=False),
        sa.Column('quantity', sa.Numeric(precision=10, scale=2), server_default=sa.text('0.00'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint('quantity >= 0', name='check_material_stocks_quantity_non_negative'),
        sa.ForeignKeyConstraint(['material_id'], ['materials.id'], ),
        sa.ForeignKeyConstraint(['site_id'], ['sites.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('site_id', 'material_id', name='uq_material_stocks_site_material'),
    )
    op.create_index('ix_material_stocks_site_id', 'material_stocks', ['site_id'], unique=False)
    op.create_index('ix_material_stocks_material_id', 'material_stocks', ['material_id'], unique=False)

    # 2. Create material_stock_movements table
    op.create_table(
        'material_stock_movements',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('site_id', sa.UUID(), nullable=False),
        sa.Column('material_id', sa.UUID(), nullable=False),
        sa.Column('movement_type', sa.String(length=30), nullable=False),
        sa.Column('quantity', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('balance_after', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('material_transaction_id', sa.UUID(), nullable=True),
        sa.Column('idempotency_key', sa.String(length=100), nullable=False),
        sa.Column('remarks', sa.Text(), nullable=True),
        sa.Column('created_by', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "movement_type IN ('inward', 'consumed', 'returned', 'adjustment')",
            name='check_stock_movement_type',
        ),
        sa.CheckConstraint('quantity > 0', name='check_stock_movement_quantity_positive'),
        sa.CheckConstraint('balance_after >= 0', name='check_stock_movement_balance_after_non_negative'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
        sa.ForeignKeyConstraint(['material_id'], ['materials.id'], ),
        sa.ForeignKeyConstraint(['material_transaction_id'], ['material_transactions.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['site_id'], ['sites.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_material_stock_movements_site_id', 'material_stock_movements', ['site_id'], unique=False)
    op.create_index('ix_material_stock_movements_material_id', 'material_stock_movements', ['material_id'], unique=False)
    op.create_index(
        'ix_material_stock_movements_site_material',
        'material_stock_movements',
        ['site_id', 'material_id'],
        unique=False,
    )
    op.create_index('ix_material_stock_movements_movement_type', 'material_stock_movements', ['movement_type'], unique=False)
    op.create_index(
        'ix_material_stock_movements_material_transaction_id',
        'material_stock_movements',
        ['material_transaction_id'],
        unique=False,
    )
    op.create_index('ix_material_stock_movements_idempotency_key', 'material_stock_movements', ['idempotency_key'], unique=True)
    op.create_index('ix_material_stock_movements_created_by', 'material_stock_movements', ['created_by'], unique=False)
    op.create_index('ix_material_stock_movements_created_at', 'material_stock_movements', ['created_at'], unique=False)


def downgrade() -> None:
    # Safe downgrade guard: abort if ANY row exists in material_stock_movements or material_stocks
    bind = op.get_bind()
    has_movements = bind.execute(sa.text("SELECT EXISTS (SELECT 1 FROM material_stock_movements LIMIT 1)")).scalar()
    has_stocks = bind.execute(sa.text("SELECT EXISTS (SELECT 1 FROM material_stocks LIMIT 1)")).scalar()
    if has_movements or has_stocks:
        raise RuntimeError(
            "Downgrade aborted: material inventory or movement records exist in database. "
            "Downgrade must not silently delete actual inventory or movement data."
        )

    # 1. Drop material_stock_movements table and indexes
    op.drop_index('ix_material_stock_movements_created_at', table_name='material_stock_movements')
    op.drop_index('ix_material_stock_movements_created_by', table_name='material_stock_movements')
    op.drop_index('ix_material_stock_movements_idempotency_key', table_name='material_stock_movements')
    op.drop_index('ix_material_stock_movements_material_transaction_id', table_name='material_stock_movements')
    op.drop_index('ix_material_stock_movements_movement_type', table_name='material_stock_movements')
    op.drop_index('ix_material_stock_movements_site_material', table_name='material_stock_movements')
    op.drop_index('ix_material_stock_movements_material_id', table_name='material_stock_movements')
    op.drop_index('ix_material_stock_movements_site_id', table_name='material_stock_movements')
    op.drop_table('material_stock_movements')

    # 2. Drop material_stocks table and indexes
    op.drop_index('ix_material_stocks_material_id', table_name='material_stocks')
    op.drop_index('ix_material_stocks_site_id', table_name='material_stocks')
    op.drop_table('material_stocks')
