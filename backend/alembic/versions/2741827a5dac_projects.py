"""projects

Revision ID: 2741827a5dac
Revises: 3ef7de2f2bad
Create Date: 2026-08-14 12:42:56.052358

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '2741827a5dac'
down_revision: str | Sequence[str] | None = '3ef7de2f2bad'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'projects',
        sa.Column('id', sa.UUID(as_uuid=True), primary_key=True),
        sa.Column('client_id', sa.UUID(as_uuid=True), sa.ForeignKey('clients.id'), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('start_date', sa.Date(), nullable=True),
        sa.Column('end_date', sa.Date(), nullable=True)
    )


def downgrade() -> None:
    op.drop_table('projects')
