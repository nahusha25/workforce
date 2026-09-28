"""roles

Revision ID: 8b1b5ab2858f
Revises: 3d272fbae20d
Create Date: 2026-08-14 12:42:51.370165

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '8b1b5ab2858f'
down_revision: str | Sequence[str] | None = '3d272fbae20d'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'roles',
        sa.Column('id', sa.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.UniqueConstraint('name')
    )


def downgrade() -> None:
    op.drop_table('roles')
