"""add_photo_type_to_work_photos

Revision ID: d4e5f6a7b8c9
Revises: c3f8e1a7b9d2
Create Date: 2026-10-26 18:30:00.000000

Changes:
1. Add `photo_type` column to `work_photos` table:
   - VARCHAR(50), nullable=True
   - Check constraint `check_work_photos_photo_type`: photo_type IS NULL OR photo_type IN ('start_point', 'end_point', 'progress')
   - Index on `photo_type`
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'd4e5f6a7b8c9'
down_revision: Union[str, Sequence[str], None] = 'c3f8e1a7b9d2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('work_photos', sa.Column('photo_type', sa.String(length=50), nullable=True))
    op.create_index(op.f('ix_work_photos_photo_type'), 'work_photos', ['photo_type'], unique=False)
    op.create_check_constraint(
        'check_work_photos_photo_type',
        'work_photos',
        "photo_type IS NULL OR photo_type IN ('start_point', 'end_point', 'progress')"
    )


def downgrade() -> None:
    op.drop_constraint('check_work_photos_photo_type', 'work_photos', type_='check')
    op.drop_index(op.f('ix_work_photos_photo_type'), table_name='work_photos')
    op.drop_column('work_photos', 'photo_type')
