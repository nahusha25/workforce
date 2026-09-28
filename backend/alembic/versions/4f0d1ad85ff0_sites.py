"""sites

Revision ID: 4f0d1ad85ff0
Revises: 2741827a5dac
Create Date: 2026-08-14 12:42:57.228802

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '4f0d1ad85ff0'
down_revision: str | Sequence[str] | None = '2741827a5dac'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'sites',
        sa.Column('id', sa.UUID(as_uuid=True), primary_key=True),
        sa.Column('project_id', sa.UUID(as_uuid=True), sa.ForeignKey('projects.id'), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('address', sa.Text(), nullable=True),
        sa.Column('location', sa.String(), nullable=True),
        sa.Column('permitted_radius_m', sa.Numeric(), nullable=True),
        sa.Column('supervisor_id', sa.UUID(as_uuid=True), sa.ForeignKey('employees.id'), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true'))
    )


def downgrade() -> None:
    op.drop_table('sites')
