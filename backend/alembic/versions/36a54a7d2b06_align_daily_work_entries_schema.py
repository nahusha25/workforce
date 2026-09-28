"""align_daily_work_entries_schema

Revision ID: 36a54a7d2b06
Revises: 7043ed85afd1
Create Date: 2026-09-25 17:48:19.564375

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '36a54a7d2b06'
down_revision: Union[str, Sequence[str], None] = '7043ed85afd1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema: drop 7 quantity columns and constraints, add idempotency_key, quantity, uom, and rename date to work_date."""
    # 1. Add idempotency_key
    op.add_column(
        'daily_work_entries',
        sa.Column('idempotency_key', sa.String(length=100), nullable=False, server_default=sa.text("gen_random_uuid()::text"))
    )
    op.create_index(op.f('ix_daily_work_entries_idempotency_key'), 'daily_work_entries', ['idempotency_key'], unique=True)
    op.alter_column('daily_work_entries', 'idempotency_key', server_default=None)

    # 2. Rename date column to work_date and update index
    op.drop_index('ix_daily_work_entries_employee_id_date', table_name='daily_work_entries')
    op.alter_column('daily_work_entries', 'date', new_column_name='work_date')
    op.create_index('ix_daily_work_entries_employee_id_work_date', 'daily_work_entries', ['employee_id', 'work_date'], unique=False)

    # 3. Add quantity and uom
    op.add_column('daily_work_entries', sa.Column('quantity', sa.Numeric(precision=10, scale=2), nullable=False, server_default='0.00'))
    op.create_check_constraint('check_dwe_quantity', 'daily_work_entries', 'quantity >= 0')
    op.alter_column('daily_work_entries', 'quantity', server_default=None)

    op.add_column('daily_work_entries', sa.Column('uom', sa.String(length=50), nullable=False, server_default='nos'))
    op.alter_column('daily_work_entries', 'uom', server_default=None)

    # 4. Drop the 7 check constraints
    op.drop_constraint('check_dwe_cable_length_metres', 'daily_work_entries', type_='check')
    op.drop_constraint('check_dwe_cable_runs', 'daily_work_entries', type_='check')
    op.drop_constraint('check_dwe_commissioning_qty', 'daily_work_entries', type_='check')
    op.drop_constraint('check_dwe_devices_installed', 'daily_work_entries', type_='check')
    op.drop_constraint('check_dwe_drilling_qty', 'daily_work_entries', type_='check')
    op.drop_constraint('check_dwe_mounting_qty', 'daily_work_entries', type_='check')
    op.drop_constraint('check_dwe_testing_qty', 'daily_work_entries', type_='check')

    # 5. Drop the 7 quantity columns
    op.drop_column('daily_work_entries', 'cable_runs')
    op.drop_column('daily_work_entries', 'cable_length_metres')
    op.drop_column('daily_work_entries', 'devices_installed')
    op.drop_column('daily_work_entries', 'drilling_qty')
    op.drop_column('daily_work_entries', 'mounting_qty')
    op.drop_column('daily_work_entries', 'testing_qty')
    op.drop_column('daily_work_entries', 'commissioning_qty')


def downgrade() -> None:
    """Downgrade schema."""
    # 1. Re-add the 7 quantity columns
    op.add_column('daily_work_entries', sa.Column('commissioning_qty', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('daily_work_entries', sa.Column('testing_qty', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('daily_work_entries', sa.Column('mounting_qty', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('daily_work_entries', sa.Column('drilling_qty', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('daily_work_entries', sa.Column('devices_installed', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('daily_work_entries', sa.Column('cable_length_metres', sa.Numeric(precision=10, scale=2), nullable=False, server_default='0.00'))
    op.add_column('daily_work_entries', sa.Column('cable_runs', sa.Integer(), nullable=False, server_default='0'))

    # 2. Re-create the 7 check constraints
    op.create_check_constraint('check_dwe_testing_qty', 'daily_work_entries', 'testing_qty >= 0')
    op.create_check_constraint('check_dwe_mounting_qty', 'daily_work_entries', 'mounting_qty >= 0')
    op.create_check_constraint('check_dwe_drilling_qty', 'daily_work_entries', 'drilling_qty >= 0')
    op.create_check_constraint('check_dwe_devices_installed', 'daily_work_entries', 'devices_installed >= 0')
    op.create_check_constraint('check_dwe_commissioning_qty', 'daily_work_entries', 'commissioning_qty >= 0')
    op.create_check_constraint('check_dwe_cable_runs', 'daily_work_entries', 'cable_runs >= 0')
    op.create_check_constraint('check_dwe_cable_length_metres', 'daily_work_entries', 'cable_length_metres >= 0')

    # 3. Drop quantity check constraint and column
    op.drop_constraint('check_dwe_quantity', 'daily_work_entries', type_='check')
    op.drop_column('daily_work_entries', 'quantity')

    # 4. Drop uom column
    op.drop_column('daily_work_entries', 'uom')

    # 5. Drop idempotency_key index and column
    op.drop_index(op.f('ix_daily_work_entries_idempotency_key'), table_name='daily_work_entries')
    op.drop_column('daily_work_entries', 'idempotency_key')

    # 6. Revert work_date to date and update index
    op.drop_index('ix_daily_work_entries_employee_id_work_date', table_name='daily_work_entries')
    op.alter_column('daily_work_entries', 'work_date', new_column_name='date')
    op.create_index('ix_daily_work_entries_employee_id_date', 'daily_work_entries', ['employee_id', 'date'], unique=False)
