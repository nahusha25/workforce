"""create_employee_payments_tables

Revision ID: c7482a19ef51
Revises: 2115387ba7d2
Create Date: 2026-10-08 12:45:00.000000

Phase 5B — Employee Payments Domain
Creates employee_payments header table and employee_payment_lines detail table
with partial unique indexes for double-payment prevention and active lock management.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'c7482a19ef51'
down_revision: Union[str, Sequence[str], None] = '2115387ba7d2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create employee_payments table
    op.create_table(
        'employee_payments',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('payment_number', sa.String(50), nullable=False),
        sa.Column('idempotency_key', sa.String(100), nullable=False),
        sa.Column('employee_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('employees.id'), nullable=False),
        sa.Column('period_start', sa.Date(), nullable=False),
        sa.Column('period_end', sa.Date(), nullable=False),
        sa.Column('status', sa.String(20), server_default='draft', nullable=False),
        sa.Column('total_amount', sa.Numeric(12, 2), server_default='0.00', nullable=False),
        sa.Column('total_days', sa.Numeric(6, 2), server_default='0.00', nullable=False),
        sa.Column('total_quantity', sa.Numeric(10, 2), server_default='0.00', nullable=False),
        sa.Column('payment_date', sa.Date(), nullable=True),
        sa.Column('payment_method', sa.String(50), nullable=True),
        sa.Column('reference_number', sa.String(100), nullable=True),
        sa.Column('remarks', sa.Text(), nullable=True),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('approved_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('paid_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('paid_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('cancelled_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('cancelled_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('cancellation_reason', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("status IN ('draft', 'approved', 'paid', 'cancelled')", name='check_employee_payments_status'),
        sa.CheckConstraint("period_end >= period_start", name='check_employee_payments_period_dates'),
    )

    op.create_index('ix_employee_payments_payment_number', 'employee_payments', ['payment_number'], unique=True)
    op.create_index('ix_employee_payments_idempotency_key', 'employee_payments', ['idempotency_key'], unique=True)
    op.create_index('ix_employee_payments_employee_id', 'employee_payments', ['employee_id'], unique=False)
    op.create_index('ix_employee_payments_period_dates', 'employee_payments', ['period_start', 'period_end'], unique=False)
    op.create_index('ix_employee_payments_status', 'employee_payments', ['status'], unique=False)

    # 2. Create employee_payment_lines table
    op.create_table(
        'employee_payment_lines',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('payment_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('employee_payments.id', ondelete='CASCADE'), nullable=False),
        sa.Column('source_attendance_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('attendance_records.id', ondelete='SET NULL'), nullable=True),
        sa.Column('source_daily_work_entry_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('daily_work_entries.id', ondelete='SET NULL'), nullable=True),
        sa.Column('source_date', sa.Date(), nullable=False),
        sa.Column('rate_type', sa.String(20), nullable=False),
        sa.Column('rate_amount', sa.Numeric(10, 2), nullable=False),
        sa.Column('rate_effective_from', sa.Date(), nullable=False),
        sa.Column('rate_effective_to', sa.Date(), nullable=True),
        sa.Column('days', sa.Numeric(6, 2), server_default='0.00', nullable=False),
        sa.Column('quantity', sa.Numeric(10, 2), server_default='0.00', nullable=False),
        sa.Column('amount', sa.Numeric(12, 2), nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("rate_type IN ('daily', 'weekly', 'piece')", name='check_payment_lines_rate_type'),
        sa.CheckConstraint(
            "(source_attendance_id IS NOT NULL AND source_daily_work_entry_id IS NULL) OR "
            "(source_attendance_id IS NULL AND source_daily_work_entry_id IS NOT NULL)",
            name='check_payment_lines_exactly_one_source',
        ),
    )

    op.create_index('ix_employee_payment_lines_payment_id', 'employee_payment_lines', ['payment_id'], unique=False)
    op.create_index('ix_employee_payment_lines_source_date', 'employee_payment_lines', ['source_date'], unique=False)
    op.create_index('ix_employee_payment_lines_is_active', 'employee_payment_lines', ['is_active'], unique=False)

    # Partial unique indexes for double-payment concurrency prevention
    op.create_index(
        'uq_active_payment_attendance',
        'employee_payment_lines',
        ['source_attendance_id'],
        unique=True,
        postgresql_where=sa.text('is_active = TRUE AND source_attendance_id IS NOT NULL'),
    )
    op.create_index(
        'uq_active_payment_work_entry',
        'employee_payment_lines',
        ['source_daily_work_entry_id'],
        unique=True,
        postgresql_where=sa.text('is_active = TRUE AND source_daily_work_entry_id IS NOT NULL'),
    )


def downgrade() -> None:
    op.drop_index('uq_active_payment_work_entry', table_name='employee_payment_lines')
    op.drop_index('uq_active_payment_attendance', table_name='employee_payment_lines')
    op.drop_index('ix_employee_payment_lines_is_active', table_name='employee_payment_lines')
    op.drop_index('ix_employee_payment_lines_source_date', table_name='employee_payment_lines')
    op.drop_index('ix_employee_payment_lines_payment_id', table_name='employee_payment_lines')
    op.drop_table('employee_payment_lines')

    op.drop_index('ix_employee_payments_status', table_name='employee_payments')
    op.drop_index('ix_employee_payments_period_dates', table_name='employee_payments')
    op.drop_index('ix_employee_payments_employee_id', table_name='employee_payments')
    op.drop_index('ix_employee_payments_idempotency_key', table_name='employee_payments')
    op.drop_index('ix_employee_payments_payment_number', table_name='employee_payments')
    op.drop_table('employee_payments')
