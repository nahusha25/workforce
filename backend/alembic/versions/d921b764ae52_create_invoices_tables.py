"""create_invoices_tables

Revision ID: d921b764ae52
Revises: c7482a19ef51
Create Date: 2026-10-08 13:45:00.000000

Phase 5C — Invoicing Domain
Creates invoice_number_seq sequence, invoices header table, and invoice_line_items detail table
with composite indexes, single-source check constraints, and partial unique indexes for source locking.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'd921b764ae52'
down_revision: Union[str, Sequence[str], None] = 'c7482a19ef51'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 0. Create PostgreSQL sequence for atomic, forward-only invoice numbering
    op.execute("CREATE SEQUENCE invoice_number_seq START WITH 1 INCREMENT BY 1;")

    # 1. Create invoices table
    op.create_table(
        'invoices',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('invoice_number', sa.String(50), nullable=False),
        sa.Column('idempotency_key', sa.String(100), nullable=False),
        sa.Column('client_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('clients.id'), nullable=False),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('projects.id'), nullable=False),
        sa.Column('site_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('sites.id'), nullable=False),
        sa.Column('period_start', sa.Date(), nullable=False),
        sa.Column('period_end', sa.Date(), nullable=False),
        sa.Column('status', sa.String(20), server_default='draft', nullable=False),
        sa.Column('subtotal_work', sa.Numeric(12, 2), server_default='0.00', nullable=False),
        sa.Column('subtotal_material', sa.Numeric(12, 2), server_default='0.00', nullable=False),
        sa.Column('tax_amount', sa.Numeric(12, 2), server_default='0.00', nullable=False),
        sa.Column('total_amount', sa.Numeric(12, 2), server_default='0.00', nullable=False),
        sa.Column('paid_amount', sa.Numeric(12, 2), server_default='0.00', nullable=False),
        sa.Column('issue_date', sa.Date(), nullable=True),
        sa.Column('due_date', sa.Date(), nullable=True),
        sa.Column('client_po_number', sa.String(100), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('remarks', sa.Text(), nullable=True),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('issued_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('issued_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('cancelled_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('cancelled_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('cancellation_reason', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "status IN ('draft', 'issued', 'partially_paid', 'paid', 'cancelled')",
            name='check_invoices_status',
        ),
        sa.CheckConstraint("period_end >= period_start", name='check_invoices_period_dates'),
        sa.CheckConstraint("subtotal_work >= 0", name='check_invoices_subtotal_work'),
        sa.CheckConstraint("subtotal_material >= 0", name='check_invoices_subtotal_material'),
        sa.CheckConstraint("tax_amount >= 0", name='check_invoices_tax_amount'),
        sa.CheckConstraint("total_amount >= 0", name='check_invoices_total_amount'),
        sa.CheckConstraint("paid_amount >= 0", name='check_invoices_paid_amount'),
        sa.CheckConstraint(
            "due_date IS NULL OR issue_date IS NULL OR due_date >= issue_date",
            name='check_invoices_due_date',
        ),
    )

    op.create_index('ix_invoices_invoice_number', 'invoices', ['invoice_number'], unique=True)
    op.create_index('ix_invoices_idempotency_key', 'invoices', ['idempotency_key'], unique=True)
    op.create_index('ix_invoices_client_id', 'invoices', ['client_id'], unique=False)
    op.create_index('ix_invoices_project_id', 'invoices', ['project_id'], unique=False)
    op.create_index('ix_invoices_site_id', 'invoices', ['site_id'], unique=False)
    op.create_index('ix_invoices_period_start', 'invoices', ['period_start'], unique=False)
    op.create_index('ix_invoices_period_end', 'invoices', ['period_end'], unique=False)
    op.create_index('ix_invoices_period_dates', 'invoices', ['period_start', 'period_end'], unique=False)
    op.create_index('ix_invoices_status', 'invoices', ['status'], unique=False)

    # 2. Create invoice_line_items table
    op.create_table(
        'invoice_line_items',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('invoice_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('invoices.id', ondelete='CASCADE'), nullable=False),
        sa.Column('line_type', sa.String(20), nullable=False),
        sa.Column('source_daily_work_entry_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('daily_work_entries.id', ondelete='SET NULL'), nullable=True),
        sa.Column('source_material_transaction_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('material_transactions.id', ondelete='SET NULL'), nullable=True),
        sa.Column('source_date', sa.Date(), nullable=False),
        sa.Column('item_description', sa.Text(), nullable=False),
        sa.Column('quantity', sa.Numeric(10, 2), nullable=False),
        sa.Column('uom', sa.String(50), nullable=False),
        sa.Column('standard_rate', sa.Numeric(12, 2), nullable=False),
        sa.Column('unit_rate', sa.Numeric(12, 2), nullable=False),
        sa.Column('line_amount', sa.Numeric(12, 2), nullable=False),
        sa.Column('rate_override_reason', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("line_type IN ('work', 'material')", name='check_invoice_lines_line_type'),
        sa.CheckConstraint(
            "(line_type = 'work' AND source_daily_work_entry_id IS NOT NULL AND source_material_transaction_id IS NULL) OR "
            "(line_type = 'material' AND source_material_transaction_id IS NOT NULL AND source_daily_work_entry_id IS NULL)",
            name='check_invoice_lines_exactly_one_source',
        ),
        sa.CheckConstraint("quantity > 0", name='check_invoice_lines_quantity'),
        sa.CheckConstraint("standard_rate >= 0", name='check_invoice_lines_standard_rate'),
        sa.CheckConstraint("unit_rate >= 0", name='check_invoice_lines_unit_rate'),
        sa.CheckConstraint("line_amount >= 0", name='check_invoice_lines_line_amount'),
    )

    op.create_index('ix_invoice_line_items_invoice_id', 'invoice_line_items', ['invoice_id'], unique=False)
    op.create_index('ix_invoice_line_items_source_date', 'invoice_line_items', ['source_date'], unique=False)
    op.create_index('ix_invoice_line_items_is_active', 'invoice_line_items', ['is_active'], unique=False)

    # Partial unique indexes for source locking & double-billing prevention
    op.create_index(
        'uq_active_invoice_work_entry',
        'invoice_line_items',
        ['source_daily_work_entry_id'],
        unique=True,
        postgresql_where=sa.text('is_active = TRUE AND source_daily_work_entry_id IS NOT NULL'),
    )
    op.create_index(
        'uq_active_invoice_material',
        'invoice_line_items',
        ['source_material_transaction_id'],
        unique=True,
        postgresql_where=sa.text('is_active = TRUE AND source_material_transaction_id IS NOT NULL'),
    )


def downgrade() -> None:
    op.drop_index('uq_active_invoice_material', table_name='invoice_line_items')
    op.drop_index('uq_active_invoice_work_entry', table_name='invoice_line_items')
    op.drop_index('ix_invoice_line_items_is_active', table_name='invoice_line_items')
    op.drop_index('ix_invoice_line_items_source_date', table_name='invoice_line_items')
    op.drop_index('ix_invoice_line_items_invoice_id', table_name='invoice_line_items')
    op.drop_table('invoice_line_items')

    op.drop_index('ix_invoices_status', table_name='invoices')
    op.drop_index('ix_invoices_period_dates', table_name='invoices')
    op.drop_index('ix_invoices_period_end', table_name='invoices')
    op.drop_index('ix_invoices_period_start', table_name='invoices')
    op.drop_index('ix_invoices_site_id', table_name='invoices')
    op.drop_index('ix_invoices_project_id', table_name='invoices')
    op.drop_index('ix_invoices_client_id', table_name='invoices')
    op.drop_index('ix_invoices_idempotency_key', table_name='invoices')
    op.drop_index('ix_invoices_invoice_number', table_name='invoices')
    op.drop_table('invoices')

    op.execute("DROP SEQUENCE IF EXISTS invoice_number_seq;")
