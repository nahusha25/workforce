"""create_verification_records_table

Revision ID: dfc07bb0caa1
Revises: 36a54a7d2b06
Create Date: 2026-09-26 16:44:25.805491

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'dfc07bb0caa1'
down_revision: Union[str, Sequence[str], None] = '36a54a7d2b06'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema: create verification_records table."""
    op.create_table(
        'verification_records',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('idempotency_key', sa.String(length=100), nullable=False),
        sa.Column('attendance_record_id', sa.UUID(), nullable=True),
        sa.Column('daily_work_entry_id', sa.UUID(), nullable=True),
        sa.Column('material_transaction_id', sa.UUID(), nullable=True),
        sa.Column('verified_by', sa.UUID(), nullable=False),
        sa.Column('action', sa.String(length=30), nullable=False),
        sa.Column('remarks', sa.Text(), nullable=True),
        sa.Column('verified_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "action IN ('approved', 'rejected', 'correction_required')",
            name='check_verification_action'
        ),
        sa.CheckConstraint(
            "(CASE WHEN attendance_record_id IS NOT NULL THEN 1 ELSE 0 END + "
            "CASE WHEN daily_work_entry_id IS NOT NULL THEN 1 ELSE 0 END + "
            "CASE WHEN material_transaction_id IS NOT NULL THEN 1 ELSE 0 END) = 1",
            name='check_verification_single_target'
        ),
        sa.CheckConstraint(
            "action = 'approved' OR (remarks IS NOT NULL AND length(trim(remarks)) >= 10)",
            name='check_verification_mandatory_remarks'
        ),
        sa.ForeignKeyConstraint(['attendance_record_id'], ['attendance_records.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['daily_work_entry_id'], ['daily_work_entries.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['material_transaction_id'], ['material_transactions.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['verified_by'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('idempotency_key', name='uq_verification_records_idempotency_key')
    )
    op.create_index(op.f('ix_verification_records_attendance_record_id'), 'verification_records', ['attendance_record_id'], unique=False)
    op.create_index(op.f('ix_verification_records_daily_work_entry_id'), 'verification_records', ['daily_work_entry_id'], unique=False)
    op.create_index(op.f('ix_verification_records_material_transaction_id'), 'verification_records', ['material_transaction_id'], unique=False)
    op.create_index(op.f('ix_verification_records_verified_by'), 'verification_records', ['verified_by'], unique=False)
    op.create_index(op.f('ix_verification_records_idempotency_key'), 'verification_records', ['idempotency_key'], unique=True)
    op.create_index(op.f('ix_verification_records_verified_at'), 'verification_records', ['verified_at'], unique=False)


def downgrade() -> None:
    """Downgrade schema: drop verification_records table."""
    op.drop_index(op.f('ix_verification_records_verified_at'), table_name='verification_records')
    op.drop_index(op.f('ix_verification_records_idempotency_key'), table_name='verification_records')
    op.drop_index(op.f('ix_verification_records_verified_by'), table_name='verification_records')
    op.drop_index(op.f('ix_verification_records_material_transaction_id'), table_name='verification_records')
    op.drop_index(op.f('ix_verification_records_daily_work_entry_id'), table_name='verification_records')
    op.drop_index(op.f('ix_verification_records_attendance_record_id'), table_name='verification_records')
    op.drop_table('verification_records')
