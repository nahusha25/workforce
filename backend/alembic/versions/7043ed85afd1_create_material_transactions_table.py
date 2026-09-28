"""create material_transactions table

Revision ID: 7043ed85afd1
Revises: 4a2fb3cd2cce
Create Date: 2026-09-22 17:25:56.763883

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7043ed85afd1'
down_revision: Union[str, Sequence[str], None] = '4a2fb3cd2cce'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('material_transactions',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('daily_work_entry_id', sa.UUID(), nullable=False),
    sa.Column('material_id', sa.UUID(), nullable=True),
    sa.Column('site_id', sa.UUID(), nullable=False),
    sa.Column('transaction_type', sa.String(), nullable=False),
    sa.Column('item_name', sa.String(length=200), nullable=False),
    sa.Column('quantity', sa.Numeric(precision=10, scale=2), nullable=False),
    sa.Column('amount', sa.Numeric(precision=12, scale=2), nullable=False),
    sa.Column('bill_image_url', sa.Text(), nullable=True),
    sa.Column('is_high_value', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.Column('status', sa.String(), server_default='draft', nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.CheckConstraint("transaction_type IN ('consumed', 'purchased')", name='check_material_transactions_type'),
    sa.CheckConstraint('quantity > 0', name='check_material_transactions_quantity'),
    sa.CheckConstraint('amount >= 0', name='check_material_transactions_amount'),
    sa.CheckConstraint("status IN ('draft', 'submitted', 'approved', 'rejected', 'correction_required')", name='check_material_transactions_status'),
    sa.ForeignKeyConstraint(['daily_work_entry_id'], ['daily_work_entries.id'], ),
    sa.ForeignKeyConstraint(['material_id'], ['materials.id'], ),
    sa.ForeignKeyConstraint(['site_id'], ['sites.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_material_transactions_daily_work_entry_id'), 'material_transactions', ['daily_work_entry_id'], unique=False)
    op.create_index(op.f('ix_material_transactions_status'), 'material_transactions', ['status'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_material_transactions_status'), table_name='material_transactions')
    op.drop_index(op.f('ix_material_transactions_daily_work_entry_id'), table_name='material_transactions')
    op.drop_table('material_transactions')
