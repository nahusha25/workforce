"""employee_details

Revision ID: c8d8f3f9be17
Revises: 47573e73e776
Create Date: 2026-08-14 12:42:53.755644

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'c8d8f3f9be17'
down_revision: str | Sequence[str] | None = '47573e73e776'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'employee_roles',
        sa.Column('employee_id', sa.UUID(as_uuid=True), sa.ForeignKey('employees.id'), primary_key=True),
        sa.Column('role_id', sa.UUID(as_uuid=True), sa.ForeignKey('roles.id'), primary_key=True)
    )
    op.create_table(
        'employee_rate_history',
        sa.Column('id', sa.UUID(as_uuid=True), primary_key=True),
        sa.Column('employee_id', sa.UUID(as_uuid=True), sa.ForeignKey('employees.id'), nullable=False),
        sa.Column('rate_type', sa.String(), nullable=False),
        sa.Column('rate_amount', sa.Numeric(), nullable=False),
        sa.Column('effective_from', sa.Date(), nullable=False),
        sa.Column('effective_to', sa.Date(), nullable=True),
        sa.Column('changed_by', sa.UUID(as_uuid=True), sa.ForeignKey('employees.id'), nullable=False),
        sa.CheckConstraint('rate_amount >= 0')
    )


def downgrade() -> None:
    op.drop_table('employee_rate_history')
    op.drop_table('employee_roles')
