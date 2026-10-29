"""add_measurements_to_daily_work_entries

Revision ID: f2b3c4d5e6a7
Revises: d4e5f6a7b8c9
Create Date: 2026-10-27 16:30:00.000000

Changes:
1. Add `measurements` JSONB column to `daily_work_entries` table:
   - JSONB, nullable=True, server_default='[]'
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'f2b3c4d5e6a7'
down_revision: Union[str, Sequence[str], None] = 'd4e5f6a7b8c9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'daily_work_entries',
        sa.Column('measurements', postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default='[]')
    )


def downgrade() -> None:
    op.drop_column('daily_work_entries', 'measurements')
