"""add_employee_classification_and_monthly_payment

Revision ID: c3f8e1a7b9d2
Revises: e5b2c9a1d3f4
Create Date: 2026-10-26 16:35:00.000000

Changes:
1. Add `classification` column to `employees` table:
   - VARCHAR(50), nullable=False, server_default='regular'
   - Check constraint `check_employees_classification`: classification IN ('regular', 'contract')
2. Update `check_payment_lines_rate_type` check constraint on `employee_payment_lines`:
   - Drop old constraint ('daily', 'weekly', 'piece')
   - Create new constraint ('daily', 'weekly', 'piece', 'monthly')
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c3f8e1a7b9d2'
down_revision: Union[str, Sequence[str], None] = 'e5b2c9a1d3f4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add classification column with default 'regular' to employees table
    op.add_column(
        'employees',
        sa.Column('classification', sa.String(length=50), nullable=False, server_default='regular'),
    )
    op.create_check_constraint(
        'check_employees_classification',
        'employees',
        "classification IN ('regular', 'contract')",
    )

    # 2. Update employee_payment_lines rate_type check constraint to include 'monthly'
    op.drop_constraint('check_payment_lines_rate_type', 'employee_payment_lines', type_='check')
    op.create_check_constraint(
        'check_payment_lines_rate_type',
        'employee_payment_lines',
        "rate_type IN ('daily', 'weekly', 'piece', 'monthly')",
    )


def downgrade() -> None:
    # 1. Revert check constraint on employee_payment_lines
    op.drop_constraint('check_payment_lines_rate_type', 'employee_payment_lines', type_='check')
    op.create_check_constraint(
        'check_payment_lines_rate_type',
        'employee_payment_lines',
        "rate_type IN ('daily', 'weekly', 'piece')",
    )

    # 2. Revert classification on employees
    op.drop_constraint('check_employees_classification', 'employees', type_='check')
    op.drop_column('employees', 'classification')
