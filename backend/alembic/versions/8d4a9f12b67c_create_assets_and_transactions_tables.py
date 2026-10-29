"""create_assets_and_transactions_tables

Revision ID: 8d4a9f12b67c
Revises: 7a82b934e152
Create Date: 2026-10-13 12:05:00.000000

Asset Management Batch 1
Creates asset_tag_seq sequence, assets table with location consistency
check constraints (single central warehouse vs site assignment),
and immutable asset_transactions audit ledger.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '8d4a9f12b67c'
down_revision: Union[str, Sequence[str], None] = '7a82b934e152'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 0. Create PostgreSQL sequence for atomic, forward-only asset tag numbering (e.g. AST-000001)
    op.execute("CREATE SEQUENCE asset_tag_seq START WITH 1 INCREMENT BY 1 NO CYCLE;")

    # 1. Create assets table
    op.create_table(
        'assets',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('asset_tag', sa.String(50), nullable=False),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('category', sa.String(100), nullable=False),
        sa.Column('serial_number', sa.String(100), nullable=True),
        sa.Column('manufacturer', sa.String(100), nullable=True),
        sa.Column('model_number', sa.String(100), nullable=True),
        sa.Column('purchase_date', sa.Date(), nullable=True),
        sa.Column('purchase_cost', sa.Numeric(12, 2), nullable=True),
        sa.Column('warranty_expiry_date', sa.Date(), nullable=True),
        sa.Column('condition', sa.String(30), server_default='new', nullable=False),
        sa.Column('status', sa.String(30), server_default='available', nullable=False),
        sa.Column('location_type', sa.String(20), server_default='warehouse', nullable=False),
        sa.Column('current_site_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('sites.id', ondelete='RESTRICT'), nullable=True),
        sa.Column('current_custodian_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('employees.id', ondelete='SET NULL'), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "condition IN ('new', 'good', 'fair', 'damaged', 'unusable')",
            name='check_assets_condition',
        ),
        sa.CheckConstraint(
            "status IN ('available', 'under_maintenance', 'damaged', 'lost', 'retired', 'issued_employee', 'in_transit')",
            name='check_assets_status',
        ),
        sa.CheckConstraint(
            "location_type IN ('warehouse', 'site')",
            name='check_assets_location_type',
        ),
        sa.CheckConstraint(
            "(location_type = 'warehouse' AND current_site_id IS NULL) "
            "OR (location_type = 'site' AND current_site_id IS NOT NULL)",
            name='check_assets_location_consistency',
        ),
        sa.CheckConstraint(
            "purchase_cost IS NULL OR purchase_cost >= 0",
            name='check_assets_purchase_cost',
        ),
    )

    # Indexes on assets
    op.create_index('ix_assets_asset_tag', 'assets', ['asset_tag'], unique=True)
    op.create_index('ix_assets_name', 'assets', ['name'], unique=False)
    op.create_index('ix_assets_category', 'assets', ['category'], unique=False)
    op.create_index('ix_assets_serial_number', 'assets', ['serial_number'], unique=False)
    op.create_index('ix_assets_status', 'assets', ['status'], unique=False)
    op.create_index('ix_assets_location_type', 'assets', ['location_type'], unique=False)
    op.create_index('ix_assets_current_site_id', 'assets', ['current_site_id'], unique=False)
    op.create_index('ix_assets_current_custodian_id', 'assets', ['current_custodian_id'], unique=False)
    op.create_index('ix_assets_location_site', 'assets', ['location_type', 'current_site_id'], unique=False)
    op.create_index('ix_assets_status_condition', 'assets', ['status', 'condition'], unique=False)

    # 2. Create asset_transactions table
    op.create_table(
        'asset_transactions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('asset_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('assets.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('transaction_type', sa.String(50), nullable=False),
        sa.Column('from_location_type', sa.String(20), nullable=True),
        sa.Column('to_location_type', sa.String(20), nullable=True),
        sa.Column('from_site_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('sites.id', ondelete='SET NULL'), nullable=True),
        sa.Column('to_site_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('sites.id', ondelete='SET NULL'), nullable=True),
        sa.Column('from_employee_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('employees.id', ondelete='SET NULL'), nullable=True),
        sa.Column('to_employee_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('employees.id', ondelete='SET NULL'), nullable=True),
        sa.Column('condition_before', sa.String(30), nullable=True),
        sa.Column('condition_after', sa.String(30), nullable=True),
        sa.Column('transaction_date', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('performed_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('remarks', sa.Text(), nullable=True),
        sa.Column('idempotency_key', sa.String(100), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "transaction_type IN ('registered', 'reassigned', 'issued', 'returned', 'status_change', 'condition_update', 'maintenance', 'retired')",
            name='check_asset_transactions_type',
        ),
    )

    # Indexes on asset_transactions
    op.create_index('ix_asset_transactions_asset_id', 'asset_transactions', ['asset_id'], unique=False)
    op.create_index('ix_asset_transactions_transaction_type', 'asset_transactions', ['transaction_type'], unique=False)
    op.create_index('ix_asset_transactions_transaction_date', 'asset_transactions', ['transaction_date'], unique=False)
    op.create_index('ix_asset_transactions_idempotency_key', 'asset_transactions', ['idempotency_key'], unique=True)
    op.create_index('ix_asset_transactions_asset_date', 'asset_transactions', ['asset_id', 'transaction_date'], unique=False)
    op.create_index('ix_asset_transactions_to_site_id', 'asset_transactions', ['to_site_id'], unique=False)
    op.create_index('ix_asset_transactions_from_site_id', 'asset_transactions', ['from_site_id'], unique=False)


def downgrade() -> None:
    # 1. Drop asset_transactions indexes and table
    op.drop_index('ix_asset_transactions_from_site_id', table_name='asset_transactions')
    op.drop_index('ix_asset_transactions_to_site_id', table_name='asset_transactions')
    op.drop_index('ix_asset_transactions_asset_date', table_name='asset_transactions')
    op.drop_index('ix_asset_transactions_idempotency_key', table_name='asset_transactions')
    op.drop_index('ix_asset_transactions_transaction_date', table_name='asset_transactions')
    op.drop_index('ix_asset_transactions_transaction_type', table_name='asset_transactions')
    op.drop_index('ix_asset_transactions_asset_id', table_name='asset_transactions')
    op.drop_table('asset_transactions')

    # 2. Drop assets indexes and table
    op.drop_index('ix_assets_status_condition', table_name='assets')
    op.drop_index('ix_assets_location_site', table_name='assets')
    op.drop_index('ix_assets_current_custodian_id', table_name='assets')
    op.drop_index('ix_assets_current_site_id', table_name='assets')
    op.drop_index('ix_assets_location_type', table_name='assets')
    op.drop_index('ix_assets_status', table_name='assets')
    op.drop_index('ix_assets_serial_number', table_name='assets')
    op.drop_index('ix_assets_category', table_name='assets')
    op.drop_index('ix_assets_name', table_name='assets')
    op.drop_index('ix_assets_asset_tag', table_name='assets')
    op.drop_table('assets')

    # 3. Drop sequence
    op.execute("DROP SEQUENCE IF EXISTS asset_tag_seq;")
