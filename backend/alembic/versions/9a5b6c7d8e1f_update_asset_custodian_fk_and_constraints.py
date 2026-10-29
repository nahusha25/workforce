"""update_asset_custodian_fk_and_constraints

Revision ID: 9a5b6c7d8e1f
Revises: 8d4a9f12b67c
Create Date: 2026-10-13 12:25:00.000000

Asset Management Batch 1 - Corrective Batch
- Enforce check_assets_custody_status_consistency constraint:
    (status = 'issued_employee' AND current_custodian_id IS NOT NULL)
    OR (status != 'issued_employee' AND current_custodian_id IS NULL)
- Update current_custodian_id foreign key ondelete to RESTRICT
- Remove unused in_transit status from check_assets_status constraint
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '9a5b6c7d8e1f'
down_revision: Union[str, Sequence[str], None] = '8d4a9f12b67c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Update check_assets_status constraint to remove 'in_transit'
    op.drop_constraint('check_assets_status', 'assets', type_='check')
    op.create_check_constraint(
        'check_assets_status',
        'assets',
        "status IN ('available', 'under_maintenance', 'damaged', 'lost', 'retired', 'issued_employee')",
    )

    # 2. Add check_assets_custody_status_consistency constraint
    op.create_check_constraint(
        'check_assets_custody_status_consistency',
        'assets',
        "(status = 'issued_employee' AND current_custodian_id IS NOT NULL) "
        "OR (status != 'issued_employee' AND current_custodian_id IS NULL)",
    )

    # 3. Update current_custodian_id foreign key delete rule to RESTRICT
    op.drop_constraint('assets_current_custodian_id_fkey', 'assets', type_='foreignkey')
    op.create_foreign_key(
        'assets_current_custodian_id_fkey',
        'assets',
        'employees',
        ['current_custodian_id'],
        ['id'],
        ondelete='RESTRICT',
    )


def downgrade() -> None:
    # 1. Revert current_custodian_id foreign key delete rule to SET NULL
    op.drop_constraint('assets_current_custodian_id_fkey', 'assets', type_='foreignkey')
    op.create_foreign_key(
        'assets_current_custodian_id_fkey',
        'assets',
        'employees',
        ['current_custodian_id'],
        ['id'],
        ondelete='SET NULL',
    )

    # 2. Drop custody status consistency constraint
    op.drop_constraint('check_assets_custody_status_consistency', 'assets', type_='check')

    # 3. Revert check_assets_status constraint to include 'in_transit'
    op.drop_constraint('check_assets_status', 'assets', type_='check')
    op.create_check_constraint(
        'check_assets_status',
        'assets',
        "status IN ('available', 'under_maintenance', 'damaged', 'lost', 'retired', 'issued_employee', 'in_transit')",
    )
