"""create_client_payments_tables

Revision ID: 7a82b934e152
Revises: d921b764ae52
Create Date: 2026-10-08 16:45:00.000000

Phase 5D — Client Payments & Receipts Domain
Creates client_payment_number_seq sequence, client_payments table
with composite indexes, foreign key ON DELETE RESTRICT to invoices,
and DB check constraints enforcing amount > 0, valid payment methods,
status domain, and strict recorded/voided state integrity.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '7a82b934e152'
down_revision: Union[str, Sequence[str], None] = 'd921b764ae52'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 0. Create PostgreSQL sequence for atomic, forward-only client payment numbering
    op.execute("CREATE SEQUENCE client_payment_number_seq START WITH 1 INCREMENT BY 1 NO CYCLE;")

    # 1. Create client_payments table
    op.create_table(
        'client_payments',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('payment_number', sa.String(50), nullable=False),
        sa.Column('idempotency_key', sa.String(100), nullable=False),
        sa.Column('invoice_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('invoices.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('amount', sa.Numeric(12, 2), nullable=False),
        sa.Column('payment_date', sa.Date(), nullable=False),
        sa.Column('payment_method', sa.String(50), nullable=False),
        sa.Column('reference_number', sa.String(100), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('receipt_url', sa.String(500), nullable=True),
        sa.Column('status', sa.String(20), server_default='recorded', nullable=False),
        sa.Column('recorded_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('voided_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('voided_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('void_reason', sa.Text(), nullable=True),
        sa.Column('void_idempotency_key', sa.String(100), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "amount > 0",
            name='check_client_payments_amount',
        ),
        sa.CheckConstraint(
            "status IN ('recorded', 'voided')",
            name='check_client_payments_status',
        ),
        sa.CheckConstraint(
            "payment_method IN ('neft', 'rtgs', 'imps', 'upi', 'cheque', 'cash', 'other')",
            name='check_client_payments_method',
        ),
        sa.CheckConstraint(
            "(status = 'recorded' AND voided_by IS NULL AND voided_at IS NULL AND void_reason IS NULL AND void_idempotency_key IS NULL) "
            "OR (status = 'voided' AND voided_by IS NOT NULL AND voided_at IS NOT NULL AND void_reason IS NOT NULL AND length(trim(void_reason)) >= 10 AND void_idempotency_key IS NOT NULL)",
            name='check_client_payments_void_integrity',
        ),
    )

    # 2. Indexes
    op.create_index('ix_client_payments_payment_number', 'client_payments', ['payment_number'], unique=True)
    op.create_index('ix_client_payments_idempotency_key', 'client_payments', ['idempotency_key'], unique=True)
    op.create_index('ix_client_payments_void_idempotency_key', 'client_payments', ['void_idempotency_key'], unique=True)
    op.create_index('ix_client_payments_invoice_id', 'client_payments', ['invoice_id'], unique=False)
    op.create_index('ix_client_payments_payment_date', 'client_payments', ['payment_date'], unique=False)
    op.create_index('ix_client_payments_invoice_status', 'client_payments', ['invoice_id', 'status'], unique=False)


def downgrade() -> None:
    # 1. Drop indexes
    op.drop_index('ix_client_payments_invoice_status', table_name='client_payments')
    op.drop_index('ix_client_payments_payment_date', table_name='client_payments')
    op.drop_index('ix_client_payments_invoice_id', table_name='client_payments')
    op.drop_index('ix_client_payments_void_idempotency_key', table_name='client_payments')
    op.drop_index('ix_client_payments_idempotency_key', table_name='client_payments')
    op.drop_index('ix_client_payments_payment_number', table_name='client_payments')

    # 2. Drop table
    op.drop_table('client_payments')

    # 3. Drop sequence
    op.execute("DROP SEQUENCE IF EXISTS client_payment_number_seq;")
