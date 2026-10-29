"""create_payroll_overtime_settings

Revision ID: b1e4c8f0a2d5
Revises: 9a5b6c7d8e1f
Create Date: 2026-10-13 17:35:00.000000

Payroll Overtime Batch 1:
- Create payroll_overtime_settings table with effective dating (effective_from, effective_to),
  standard workday hours, overtime multiplier, constraints and indexes.
- Idempotently insert initial default configuration (7.00h standard workday, 1.50x multiplier)
  effective from 2026-01-01.
- Add nullable/default-safe overtime snapshot columns to employee_payments and employee_payment_lines.
- Preserve all existing payment records and their semantic values.
"""
from typing import Sequence, Union
import uuid

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'b1e4c8f0a2d5'
down_revision: Union[str, Sequence[str], None] = '9a5b6c7d8e1f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create payroll_overtime_settings table
    op.create_table(
        'payroll_overtime_settings',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('standard_workday_hours', sa.Numeric(5, 2), server_default='7.00', nullable=False),
        sa.Column('overtime_multiplier', sa.Numeric(4, 2), server_default='1.50', nullable=False),
        sa.Column('effective_from', sa.Date(), nullable=False),
        sa.Column('effective_to', sa.Date(), nullable=True),
        sa.Column('description', sa.String(255), nullable=True),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            'standard_workday_hours > 0 AND standard_workday_hours <= 24',
            name='check_overtime_standard_hours_valid',
        ),
        sa.CheckConstraint(
            'overtime_multiplier >= 1.0 AND overtime_multiplier <= 5.0',
            name='check_overtime_multiplier_valid',
        ),
        sa.CheckConstraint(
            'effective_to IS NULL OR effective_to >= effective_from',
            name='check_overtime_effective_dates',
        ),
    )

    op.create_index(
        'ix_payroll_overtime_settings_effective_from',
        'payroll_overtime_settings',
        ['effective_from'],
        unique=False,
    )
    op.create_index(
        'ix_payroll_overtime_settings_effective_to',
        'payroll_overtime_settings',
        ['effective_to'],
        unique=False,
    )
    op.create_index(
        'ix_payroll_overtime_settings_dates',
        'payroll_overtime_settings',
        ['effective_from', 'effective_to'],
        unique=False,
    )

    # 2. Idempotently insert initial default configuration effective from 2026-01-01
    bind = op.get_bind()
    existing = bind.execute(
        sa.text("SELECT id FROM payroll_overtime_settings WHERE effective_from = '2026-01-01'")
    ).fetchone()
    if not existing:
        initial_id = str(uuid.uuid4())
        bind.execute(
            sa.text(
                """
                INSERT INTO payroll_overtime_settings (
                    id,
                    standard_workday_hours,
                    overtime_multiplier,
                    effective_from,
                    effective_to,
                    description,
                    created_at
                ) VALUES (
                    :id,
                    7.00,
                    1.50,
                    '2026-01-01',
                    NULL,
                    'Default initial standard workday (7.00h) and overtime multiplier (1.50x)',
                    NOW()
                )
                """
            ),
            {"id": initial_id},
        )

    # 3. Add overtime snapshot columns to employee_payments
    op.add_column(
        'employee_payments',
        sa.Column('total_regular_amount', sa.Numeric(12, 2), server_default='0.00', nullable=False),
    )
    op.add_column(
        'employee_payments',
        sa.Column('total_overtime_hours', sa.Numeric(8, 2), server_default='0.00', nullable=False),
    )
    op.add_column(
        'employee_payments',
        sa.Column('total_overtime_amount', sa.Numeric(12, 2), server_default='0.00', nullable=False),
    )

    # Backfill existing payment headers: regular amount equals total_amount, overtime is 0.00
    op.execute(
        sa.text(
            """
            UPDATE employee_payments
            SET total_regular_amount = total_amount
            WHERE total_regular_amount = 0.00 AND total_amount > 0.00
            """
        )
    )

    # 4. Add overtime snapshot columns to employee_payment_lines
    op.add_column(
        'employee_payment_lines',
        sa.Column('regular_hours', sa.Numeric(6, 2), nullable=True),
    )
    op.add_column(
        'employee_payment_lines',
        sa.Column('overtime_hours', sa.Numeric(6, 2), server_default='0.00', nullable=True),
    )
    op.add_column(
        'employee_payment_lines',
        sa.Column('standard_day_hours', sa.Numeric(5, 2), nullable=True),
    )
    op.add_column(
        'employee_payment_lines',
        sa.Column('hourly_equivalent_rate', sa.Numeric(10, 2), nullable=True),
    )
    op.add_column(
        'employee_payment_lines',
        sa.Column('overtime_multiplier', sa.Numeric(4, 2), nullable=True),
    )
    op.add_column(
        'employee_payment_lines',
        sa.Column('regular_amount', sa.Numeric(12, 2), nullable=True),
    )
    op.add_column(
        'employee_payment_lines',
        sa.Column('overtime_amount', sa.Numeric(12, 2), server_default='0.00', nullable=True),
    )

    # Backfill existing payment lines: regular amount equals line amount, overtime amount is 0.00
    op.execute(
        sa.text(
            """
            UPDATE employee_payment_lines
            SET regular_amount = amount,
                overtime_amount = 0.00
            WHERE regular_amount IS NULL
            """
        )
    )


def downgrade() -> None:
    # 1. Drop overtime snapshot columns from employee_payment_lines (preserving table and existing data)
    op.drop_column('employee_payment_lines', 'overtime_amount')
    op.drop_column('employee_payment_lines', 'regular_amount')
    op.drop_column('employee_payment_lines', 'overtime_multiplier')
    op.drop_column('employee_payment_lines', 'hourly_equivalent_rate')
    op.drop_column('employee_payment_lines', 'standard_day_hours')
    op.drop_column('employee_payment_lines', 'overtime_hours')
    op.drop_column('employee_payment_lines', 'regular_hours')

    # 2. Drop overtime snapshot columns from employee_payments (preserving table and existing data)
    op.drop_column('employee_payments', 'total_overtime_amount')
    op.drop_column('employee_payments', 'total_overtime_hours')
    op.drop_column('employee_payments', 'total_regular_amount')

    # 3. Drop indexes and payroll_overtime_settings table
    op.drop_index('ix_payroll_overtime_settings_dates', table_name='payroll_overtime_settings')
    op.drop_index('ix_payroll_overtime_settings_effective_to', table_name='payroll_overtime_settings')
    op.drop_index('ix_payroll_overtime_settings_effective_from', table_name='payroll_overtime_settings')
    op.drop_table('payroll_overtime_settings')
