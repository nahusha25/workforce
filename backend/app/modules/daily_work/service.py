import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any, Optional, Tuple, Union

from fastapi import HTTPException, status, status as http_status
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.operations import (
    Activity,
    AttendanceRecord,
    DailyWorkEntry,
    EmployeeSiteAssignment,
    Site,
    WorkOrder,
)
from app.models.system import AuditLog
from app.models.workforce import Employee
from app.modules.attendance.service import AttendanceService
from app.modules.daily_work.schemas import DailyWorkEntryCreate, DailyWorkEntryUpdate

EDITABLE_STATUSES: Tuple[str, ...] = ("draft", "correction_required")


def _get_data_dict(data: Any) -> dict:
    if isinstance(data, dict):
        return data
    if hasattr(data, "model_dump"):
        return data.model_dump(exclude_unset=True)
    if hasattr(data, "dict"):
        return data.dict(exclude_unset=True)
    return vars(data)


class DailyWorkService:
    @staticmethod
    async def is_supervisor_authorized(
        session: AsyncSession,
        supervisor_emp_id: uuid.UUID,
        target_emp_id: uuid.UUID,
        site_id: Optional[uuid.UUID] = None,
    ) -> bool:
        """Check if supervisor is authorized for target employee.

        Delegates directly to AttendanceService.is_supervisor_authorized for
        standard organizational hierarchy and active assignment checks:
          1. Direct supervisor (Employee.supervisor_id == supervisor_emp_id)
          2. Active site assignment (Site.supervisor_id == supervisor_emp_id)

        In addition, Daily Work entries support site-specific authorization:
          3. Specific entry site supervisor (Site.supervisor_id == supervisor_emp_id for entry.site_id)

        Why this site-specific check is needed in Daily Work and not Attendance:
        Attendance operations (check-in, check-out, geofence override) are real-time,
        session-scoped actions evaluated against an employee's current active site
        assignment. Daily work entries, however, are persistent records of work
        completed at a specific physical site (recorded in entry.site_id). A resident
        site supervisor must have authorization to inspect all work executed on their
        site, even if the worker's active assignment subsequently shifts or their
        reporting line sits under a different department.
        """
        # 1 & 2: Delegate to AttendanceService's established authorization logic
        try:
            if await AttendanceService.is_supervisor_authorized(
                session, supervisor_emp_id, target_emp_id
            ):
                return True
        except HTTPException:
            # get_active_assignment inside AttendanceService raises 403 if target has no active assignment
            pass

        # 3. Additional site-specific check for work entry's site
        if site_id:
            stmt_site = select(Site).where(Site.id == site_id)
            res_site = await session.execute(stmt_site)
            site = res_site.scalars().first()
            if site and site.supervisor_id == supervisor_emp_id:
                return True

        return False

    @staticmethod
    async def create_work_entry(
        session: AsyncSession,
        employee_id: uuid.UUID,
        data: Union[DailyWorkEntryCreate, dict],
        user_id: Optional[uuid.UUID] = None,
    ) -> DailyWorkEntry:
        """Create a new daily_work_entries record.

        Validates that the employee has an active (checked-in, not checked-out)
        attendance_records entry for today, and links the new entry via attendance_record_id.
        Rejects if no active check-in exists.
        """
        today = datetime.now(timezone.utc).date()

        # Validate active attendance session: any unclosed check-in session (check_out_time IS NULL)
        # ordered by check_in_time descending.
        stmt = (
            select(AttendanceRecord)
            .where(
                and_(
                    AttendanceRecord.employee_id == employee_id,
                    AttendanceRecord.check_out_time.is_(None),
                )
            )
            .order_by(AttendanceRecord.check_in_time.desc())
        )
        result = await session.execute(stmt)
        active_record = result.scalars().first()

        if not active_record:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No active check-in session found. An active attendance check-in is required to create a daily work entry.",
            )

        data_dict = _get_data_dict(data)

        # Validate idempotency_key
        idempotency_key = data_dict.get("idempotency_key")
        if not idempotency_key or not str(idempotency_key).strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="idempotency_key is required",
            )
        idempotency_key_str = str(idempotency_key).strip()

        # Check uniqueness of idempotency_key
        stmt_idemp = select(DailyWorkEntry).where(DailyWorkEntry.idempotency_key == idempotency_key_str)
        res_idemp = await session.execute(stmt_idemp)
        if res_idemp.scalars().first():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Daily work entry with idempotency_key '{idempotency_key_str}' already exists",
            )

        # Validate activity
        activity_id = data_dict.get("activity_id")
        if not activity_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="activity_id is required",
            )
        if isinstance(activity_id, str):
            activity_id = uuid.UUID(activity_id)

        stmt_act = select(Activity).where(Activity.id == activity_id)
        res_act = await session.execute(stmt_act)
        activity = res_act.scalars().first()
        if not activity:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Activity not found",
            )

        # Auto-derive uom from selected activity
        uom = activity.unit_of_measure or "nos"

        # Validate work_order_id if provided
        work_order_id = data_dict.get("work_order_id")
        if work_order_id:
            if isinstance(work_order_id, str):
                work_order_id = uuid.UUID(work_order_id)
            stmt_wo = select(WorkOrder).where(WorkOrder.id == work_order_id)
            res_wo = await session.execute(stmt_wo)
            wo = res_wo.scalars().first()
            if not wo:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Work order not found",
                )

        # Validate quantity non-negative
        quantity_raw = data_dict.get("quantity", 0)
        try:
            quantity = Decimal(str(quantity_raw if quantity_raw is not None else 0))
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="quantity must be a valid number",
            )
        if quantity < 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="quantity must be non-negative",
            )

        work_date = data_dict.get("work_date") or data_dict.get("date") or active_record.date or today
        remarks = data_dict.get("remarks")

        entry = DailyWorkEntry(
            idempotency_key=idempotency_key_str,
            attendance_record_id=active_record.id,
            employee_id=employee_id,
            site_id=active_record.site_id,
            activity_id=activity_id,
            work_order_id=work_order_id,
            work_date=work_date,
            quantity=quantity,
            uom=uom,
            status="draft",
            remarks=remarks,
        )
        session.add(entry)
        await session.flush()

        if user_id:
            audit = AuditLog(
                entity_type="daily_work_entry",
                entity_id=entry.id,
                action="create",
                changed_by=user_id,
                previous_values=None,
                new_values={
                    "status": "draft",
                    "activity_id": str(activity_id),
                    "attendance_record_id": str(active_record.id),
                },
            )
            session.add(audit)

        await session.commit()
        await session.refresh(entry)
        return entry

    @staticmethod
    async def update_work_entry(
        session: AsyncSession,
        entry_id: uuid.UUID,
        data: Union[DailyWorkEntryUpdate, dict],
        employee_id: Optional[uuid.UUID] = None,
        user_id: Optional[uuid.UUID] = None,
        is_admin: bool = False,
    ) -> DailyWorkEntry:
        """Update a draft or correction_required entry's fields.

        Rejects edits to entries in any other status (submitted, approved, rejected).
        """
        stmt = select(DailyWorkEntry).where(DailyWorkEntry.id == entry_id)
        result = await session.execute(stmt)
        entry = result.scalars().first()
        if not entry:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Daily work entry not found",
            )

        # Authorization: employee can only update their own entries
        if not is_admin and employee_id is not None:
            if entry.employee_id != employee_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Cannot edit another employee's work entry",
                )

        # Status constraint: only draft or correction_required can be updated
        if entry.status not in EDITABLE_STATUSES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot update work entry with status '{entry.status}'. Only draft and correction_required entries can be edited.",
            )

        data_dict = _get_data_dict(data)

        # Update activity_id if present
        if "activity_id" in data_dict and data_dict["activity_id"] is not None:
            act_id = data_dict["activity_id"]
            if isinstance(act_id, str):
                act_id = uuid.UUID(act_id)
            stmt_act = select(Activity).where(Activity.id == act_id)
            res_act = await session.execute(stmt_act)
            act_obj = res_act.scalars().first()
            if not act_obj:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Activity not found",
                )
            entry.activity_id = act_id
            if act_obj.unit_of_measure:
                entry.uom = act_obj.unit_of_measure

        # Update work_order_id if present
        if "work_order_id" in data_dict:
            wo_id = data_dict["work_order_id"]
            if wo_id is not None:
                if isinstance(wo_id, str):
                    wo_id = uuid.UUID(wo_id)
                stmt_wo = select(WorkOrder).where(WorkOrder.id == wo_id)
                res_wo = await session.execute(stmt_wo)
                if not res_wo.scalars().first():
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Work order not found",
                    )
            entry.work_order_id = wo_id

        # Update quantity
        if "quantity" in data_dict and data_dict["quantity"] is not None:
            try:
                val = Decimal(str(data_dict["quantity"]))
            except Exception:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="quantity must be a valid number",
                )
            if val < 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="quantity must be non-negative",
                )
            entry.quantity = val

        # Update remarks
        if "remarks" in data_dict:
            entry.remarks = data_dict["remarks"]

        entry.updated_at = datetime.now(timezone.utc)

        if user_id:
            audit = AuditLog(
                entity_type="daily_work_entry",
                entity_id=entry.id,
                action="update",
                changed_by=user_id,
                previous_values=None,
                new_values={"status": entry.status},
            )
            session.add(audit)

        await session.commit()
        await session.refresh(entry)
        return entry

    @staticmethod
    async def submit_work_entry(
        session: AsyncSession,
        entry_id: uuid.UUID,
        employee_id: Optional[uuid.UUID] = None,
        user_id: Optional[uuid.UUID] = None,
        is_admin: bool = False,
    ) -> DailyWorkEntry:
        """Transition an entry from draft/correction_required to submitted.

        Validates quantity is greater than zero.
        """
        stmt = select(DailyWorkEntry).where(DailyWorkEntry.id == entry_id)
        result = await session.execute(stmt)
        entry = result.scalars().first()
        if not entry:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Daily work entry not found",
            )

        # Authorization: employee can only submit their own entries
        if not is_admin and employee_id is not None:
            if entry.employee_id != employee_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Cannot submit another employee's work entry",
                )

        # Status constraint: only draft or correction_required can be submitted
        if entry.status not in EDITABLE_STATUSES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot submit work entry with status '{entry.status}'. Only draft or correction_required entries can be submitted.",
            )

        # Validate quantity is greater than zero
        if entry.quantity is None or float(entry.quantity) <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Work quantity must be greater than zero to submit",
            )

        old_status = entry.status
        entry.status = "submitted"
        entry.updated_at = datetime.now(timezone.utc)

        if user_id:
            audit = AuditLog(
                entity_type="daily_work_entry",
                entity_id=entry.id,
                action="submit",
                changed_by=user_id,
                previous_values={"status": old_status},
                new_values={"status": "submitted"},
            )
            session.add(audit)

        await session.commit()
        await session.refresh(entry)
        return entry

    @staticmethod
    async def list_work_entries(
        session: AsyncSession,
        employee_id: Optional[uuid.UUID] = None,
        supervisor_emp_id: Optional[uuid.UUID] = None,
        date: Optional[date] = None,
        date_filter: Optional[date] = None,
        entry_date: Optional[date] = None,
        is_admin: bool = False,
        status: Optional[str] = None,
        site_id: Optional[uuid.UUID] = None,
        activity_id: Optional[uuid.UUID] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        skip: int = 0,
        limit: int = 20,
    ) -> Tuple[list[DailyWorkEntry], int]:
        """List daily work entries for an employee (self) or for a supervisor's assigned team.

        Filterable by date, date range, status, site_id, activity_id.
        """
        target_date = date or date_filter or entry_date

        stmt = (
            select(
                DailyWorkEntry,
                Employee.name.label("employee_name"),
                Site.name.label("site_name"),
                Activity.name.label("activity_name"),
            )
            .outerjoin(Employee, DailyWorkEntry.employee_id == Employee.id)
            .outerjoin(Site, DailyWorkEntry.site_id == Site.id)
            .outerjoin(Activity, DailyWorkEntry.activity_id == Activity.id)
        )

        if not is_admin and supervisor_emp_id:
            if employee_id:
                is_auth = await DailyWorkService.is_supervisor_authorized(
                    session, supervisor_emp_id, employee_id
                )
                if not is_auth:
                    raise HTTPException(
                        status_code=http_status.HTTP_403_FORBIDDEN,
                        detail="Cannot access other employee records",
                    )
                stmt = stmt.where(DailyWorkEntry.employee_id == employee_id)
            else:
                stmt = (
                    stmt.outerjoin(
                        EmployeeSiteAssignment,
                        DailyWorkEntry.employee_id == EmployeeSiteAssignment.employee_id,
                    )
                    .where(
                        or_(
                            Employee.supervisor_id == supervisor_emp_id,
                            Site.supervisor_id == supervisor_emp_id,
                        )
                    )
                    .group_by(DailyWorkEntry.id, Employee.name, Site.name, Activity.name)
                )
        elif employee_id:
            stmt = stmt.where(DailyWorkEntry.employee_id == employee_id)

        if target_date:
            stmt = stmt.where(DailyWorkEntry.work_date == target_date)
        if date_from:
            stmt = stmt.where(DailyWorkEntry.work_date >= date_from)
        if date_to:
            stmt = stmt.where(DailyWorkEntry.work_date <= date_to)
        if status:
            stmt = stmt.where(DailyWorkEntry.status == status)
        if site_id:
            stmt = stmt.where(DailyWorkEntry.site_id == site_id)
        if activity_id:
            stmt = stmt.where(DailyWorkEntry.activity_id == activity_id)

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total_res = await session.execute(count_stmt)
        total = total_res.scalar_one()

        stmt = stmt.order_by(DailyWorkEntry.work_date.desc(), DailyWorkEntry.created_at.desc()).offset(skip).limit(limit)
        result = await session.execute(stmt)
        rows = result.all()

        items = []
        for row in rows:
            rec = row[0]
            rec.employee_name = row[1]
            rec.site_name = row[2]
            rec.activity_name = row[3]
            items.append(rec)

        return items, total

    @staticmethod
    async def get_work_entry(
        session: AsyncSession,
        entry_id: uuid.UUID,
        employee_id: Optional[uuid.UUID] = None,
        supervisor_emp_id: Optional[uuid.UUID] = None,
        user_role: Optional[str] = None,
        requester_employee_id: Optional[uuid.UUID] = None,
        is_admin: bool = False,
    ) -> DailyWorkEntry:
        """Get a single entry by id, respecting self/supervisor authorization rules."""
        stmt = (
            select(
                DailyWorkEntry,
                Employee.name.label("employee_name"),
                Site.name.label("site_name"),
                Activity.name.label("activity_name"),
            )
            .outerjoin(Employee, DailyWorkEntry.employee_id == Employee.id)
            .outerjoin(Site, DailyWorkEntry.site_id == Site.id)
            .outerjoin(Activity, DailyWorkEntry.activity_id == Activity.id)
            .where(DailyWorkEntry.id == entry_id)
        )
        result = await session.execute(stmt)
        row = result.first()
        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Daily work entry not found",
            )

        entry = row[0]
        entry.employee_name = row[1]
        entry.site_name = row[2]
        entry.activity_name = row[3]

        # Authorization checks
        if is_admin or user_role in ("administrator", "director"):
            return entry

        req_emp_id = requester_employee_id or employee_id

        if user_role == "employee":
            if not req_emp_id or entry.employee_id != req_emp_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Cannot access other employee records",
                )
        elif user_role == "supervisor" or supervisor_emp_id:
            sup_id = supervisor_emp_id or req_emp_id
            if not sup_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Supervisor profile required",
                )
            is_auth = await DailyWorkService.is_supervisor_authorized(
                session, sup_id, entry.employee_id, site_id=entry.site_id
            )
            if not is_auth:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Cannot access other employee records",
                )
        elif req_emp_id:
            if entry.employee_id != req_emp_id:
                is_auth = await DailyWorkService.is_supervisor_authorized(
                    session, req_emp_id, entry.employee_id, site_id=entry.site_id
                )
                if not is_auth:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Cannot access other employee records",
                    )

        return entry

    # Aliases for flexible calling conventions
    create = create_work_entry
    update = update_work_entry
    submit = submit_work_entry
    list = list_work_entries
    list_entries = list_work_entries
    get = get_work_entry
