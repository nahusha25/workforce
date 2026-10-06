"""add_phase5_dashboard_composite_indexes

Revision ID: 2115387ba7d2
Revises: dfc07bb0caa1
Create Date: 2026-09-30 11:52:30.987549

Phase 5 — Batch 1 (DB-027-IDX)
Adds three composite indexes to support live dashboard metric aggregation queries.
All three tables already have single-column status indexes from earlier phases;
these composites allow PostgreSQL to satisfy (status, date/created_at, site_id, ...)
filter combinations from the index alone, avoiding sequential scans on large date ranges.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2115387ba7d2'
down_revision: Union[str, Sequence[str], None] = 'dfc07bb0caa1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add composite indexes for Phase 5 dashboard metrics queries."""

    # attendance_records: manpower count + working hours queries
    # Dashboard filters: status='approved', date range, optional site_id, optional employee_id
    op.create_index(
        'ix_attendance_records_status_date_site_employee',
        'attendance_records',
        ['status', 'date', 'site_id', 'employee_id'],
        unique=False,
    )

    # daily_work_entries: work quantity / productivity / cable / device metrics
    # Dashboard filters: status='approved', work_date range, optional site_id,
    # activity_id joined to activities.category for cable/device breakdown
    op.create_index(
        'ix_daily_work_entries_status_work_date_site_activity',
        'daily_work_entries',
        ['status', 'work_date', 'site_id', 'activity_id'],
        unique=False,
    )

    # material_transactions: material cost metric + materials report
    # Dashboard filters: status='approved', created_at date range, optional site_id
    op.create_index(
        'ix_material_transactions_status_created_at_site',
        'material_transactions',
        ['status', 'created_at', 'site_id'],
        unique=False,
    )


def downgrade() -> None:
    """Remove composite indexes added for Phase 5 dashboard metrics."""
    op.drop_index('ix_material_transactions_status_created_at_site', table_name='material_transactions')
    op.drop_index('ix_daily_work_entries_status_work_date_site_activity', table_name='daily_work_entries')
    op.drop_index('ix_attendance_records_status_date_site_employee', table_name='attendance_records')
