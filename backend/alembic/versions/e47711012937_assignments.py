"""assignments

Revision ID: e47711012937
Revises: 4f0d1ad85ff0
Create Date: 2026-08-14 12:42:58.390051

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'e47711012937'
down_revision: str | Sequence[str] | None = '4f0d1ad85ff0'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'employee_site_assignments',
        sa.Column('id', sa.UUID(as_uuid=True), primary_key=True),
        sa.Column('employee_id', sa.UUID(as_uuid=True), sa.ForeignKey('employees.id'), nullable=False),
        sa.Column('site_id', sa.UUID(as_uuid=True), sa.ForeignKey('sites.id'), nullable=False),
        sa.Column('assigned_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('unassigned_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.UniqueConstraint('employee_id', 'site_id')
    )


def downgrade() -> None:
    op.drop_table('employee_site_assignments')
