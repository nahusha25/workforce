"""employees

Revision ID: 47573e73e776
Revises: 8b1b5ab2858f
Create Date: 2026-08-14 12:42:52.682082

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '47573e73e776'
down_revision: str | Sequence[str] | None = '8b1b5ab2858f'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'employees',
        sa.Column('id', sa.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', sa.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('employee_code', sa.String(), nullable=False),
        sa.Column('mobile_id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('supervisor_id', sa.UUID(as_uuid=True), sa.ForeignKey('employees.id'), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.UniqueConstraint('user_id'),
        sa.UniqueConstraint('employee_code'),
        sa.UniqueConstraint('mobile_id')
    )


def downgrade() -> None:
    op.drop_table('employees')
