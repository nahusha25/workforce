import uuid
from datetime import date, datetime, timezone
from sqlalchemy import select, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
from app.models.operations import AttendanceRecord, DailyWorkEntry, EmployeeSiteAssignment, ExceptionFlag, Site
from app.models.workforce import Employee
from app.models.system import AuditLog
from app.modules.attendance.schemas import CheckInRequest, CheckOutRequest, OverrideRequest
from app.shared.geo import calculate_distance_metres, is_within_geofence

class AttendanceService:
    @staticmethod
    async def get_active_assignment(session: AsyncSession, employee_id: uuid.UUID) -> EmployeeSiteAssignment:
        stmt = select(EmployeeSiteAssignment).where(
            and_(
                EmployeeSiteAssignment.employee_id == employee_id,
                EmployeeSiteAssignment.is_active == True
            )
        )
        result = await session.execute(stmt)
        assignment = result.scalars().first()
        if not assignment:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Employee does not have an active site assignment"
            )
        return assignment

    @staticmethod
    async def get_site(session: AsyncSession, site_id: uuid.UUID) -> Site:
        stmt = select(Site).where(Site.id == site_id)
        result = await session.execute(stmt)
        site = result.scalars().first()
        if not site:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Site not found")
        return site

    @staticmethod
    async def is_supervisor_authorized(session: AsyncSession, supervisor_emp_id: uuid.UUID, target_emp_id: uuid.UUID) -> bool:
        stmt = select(Employee).where(Employee.id == target_emp_id)
        result = await session.execute(stmt)
        emp = result.scalars().first()
        if emp and emp.supervisor_id == supervisor_emp_id:
            return True
            
        assignment = await AttendanceService.get_active_assignment(session, target_emp_id)
        if assignment:
            site = await AttendanceService.get_site(session, assignment.site_id)
            if site and site.supervisor_id == supervisor_emp_id:
                return True
                
        return False
        
    @staticmethod
    def extract_lat_lng_from_wkt(location_str: str) -> tuple[float, float]:
        if not location_str or not location_str.startswith("POINT"):
            return 0.0, 0.0
        try:
            coords = location_str.replace("POINT", "").replace("(", "").replace(")", "").strip().split(" ")
            lng, lat = float(coords[0]), float(coords[1])
            return lat, lng
        except Exception:
            return 0.0, 0.0

    @staticmethod
    async def check_in(session: AsyncSession, employee_id: uuid.UUID, user_id: uuid.UUID, data: CheckInRequest):
        assignment = await AttendanceService.get_active_assignment(session, employee_id)
        site = await AttendanceService.get_site(session, assignment.site_id)
        
        today = datetime.now(timezone.utc).date()
        
        stmt = select(AttendanceRecord).where(
            and_(
                AttendanceRecord.employee_id == employee_id,
                AttendanceRecord.date == today
            )
        ).order_by(AttendanceRecord.session_number.desc())
        result = await session.execute(stmt)
        existing_records = result.scalars().all()
        
        open_session = next((r for r in existing_records if r.check_out_time is None), None)
        if open_session:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Active check-in session already in progress"
            )

        session_number = (max((r.session_number or 0) for r in existing_records) + 1) if existing_records else 1

        if not site.location:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Site has no GPS location configured"
            )
            
        site_lat, site_lng = AttendanceService.extract_lat_lng_from_wkt(str(site.location))
        
        distance = calculate_distance_metres(data.latitude, data.longitude, site_lat, site_lng)
        
        is_within = is_within_geofence(
            data.latitude, data.longitude, 
            site_lat, site_lng, 
            float(site.permitted_radius_m or 100.0)
        )

        record_status = "draft" if is_within else "flagged"
        wkt_point = f"POINT({data.longitude} {data.latitude})"

        record = AttendanceRecord(
            employee_id=employee_id,
            site_id=site.id,
            date=today,
            session_number=session_number,
            check_in_time=datetime.now(timezone.utc),
            check_in_location=wkt_point,
            check_in_distance_m=distance,
            is_within_geofence=is_within,
            status=record_status
        )
        session.add(record)
        await session.flush()
        
        if not is_within:
            flag = ExceptionFlag(
                entity_type="attendance_record",
                entity_id=record.id,
                flag_type="out_of_location",
                is_resolved=False
            )
            session.add(flag)

        audit = AuditLog(
            entity_type="attendance_record",
            entity_id=record.id,
            action="create",
            changed_by=user_id,
            previous_values=None,
            new_values={
                "status": record_status,
                "is_within_geofence": is_within
            }
        )
        session.add(audit)
        
        await session.commit()
        await session.refresh(record)
        return record

    @staticmethod
    async def check_out(session: AsyncSession, employee_id: uuid.UUID, user_id: uuid.UUID, data: CheckOutRequest):
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
        record = result.scalars().first()
        if not record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No active check-in session found"
            )
            
        site = await AttendanceService.get_site(session, record.site_id)
        if site.location:
            site_lat, site_lng = AttendanceService.extract_lat_lng_from_wkt(str(site.location))
            distance = calculate_distance_metres(data.latitude, data.longitude, site_lat, site_lng)
        else:
            distance = 0.0

        wkt_point = f"POINT({data.longitude} {data.latitude})"

        record.check_out_time = datetime.now(timezone.utc)
        record.check_out_location = wkt_point
        record.check_out_distance_m = distance
        
        if record.check_in_time:
            delta = record.check_out_time - record.check_in_time
            record.working_hours = delta.total_seconds() / 3600.0
            
            if record.working_hours > 8.0:
                record.overtime_hours = record.working_hours - 8.0
            else:
                record.overtime_hours = 0.0

        # REQ-BR-003: Pre-checkout soft check for daily work submission
        dwe_stmt = select(DailyWorkEntry).where(
            DailyWorkEntry.attendance_record_id == record.id
        )
        dwe_result = await session.execute(dwe_stmt)
        work_entries = dwe_result.scalars().all()

        requires_confirmation = False
        warning = None

        if not work_entries:
            requires_confirmation = True
            warning = "No daily work entries submitted for this session. Please confirm check-out."
        elif any(entry.status == "draft" for entry in work_entries):
            requires_confirmation = True
            warning = "You have unsubmitted draft work entries. Please confirm check-out."

        audit = AuditLog(
            entity_type="attendance_record",
            entity_id=record.id,
            action="check_out",
            changed_by=user_id,
            previous_values={"working_hours": None},
            new_values={"working_hours": float(record.working_hours) if record.working_hours else None}
        )
        session.add(audit)
        
        await session.commit()
        await session.refresh(record)

        record.requires_confirmation = requires_confirmation
        record.warning = warning
        return record
        
    @staticmethod
    async def override_geofence(session: AsyncSession, attendance_id: uuid.UUID, supervisor_user_id: uuid.UUID, supervisor_emp_id: uuid.UUID, data: OverrideRequest, is_admin: bool = False):
        stmt = select(AttendanceRecord).where(AttendanceRecord.id == attendance_id)
        result = await session.execute(stmt)
        record = result.scalars().first()
        if not record:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attendance record not found")
            
        if not is_admin:
            is_auth = await AttendanceService.is_supervisor_authorized(session, supervisor_emp_id, record.employee_id)
            if not is_auth:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorized to override attendance for this employee")
            
        record.override_by = supervisor_user_id
        
        audit = AuditLog(
            entity_type="attendance_record",
            entity_id=record.id,
            action="override",
            changed_by=supervisor_user_id,
            previous_values={"override_by": None},
            new_values={"override_reason": data.override_reason}
        )
        session.add(audit)
        
        await session.commit()
        await session.refresh(record)
        return record

    @staticmethod
    async def list_attendance(session: AsyncSession, employee_id: uuid.UUID = None, supervisor_emp_id: uuid.UUID = None, is_admin: bool = False, skip: int = 0, limit: int = 20):
        stmt = (
            select(
                AttendanceRecord,
                Employee.name.label("employee_name"),
                Site.name.label("site_name"),
            )
            .outerjoin(Employee, AttendanceRecord.employee_id == Employee.id)
            .outerjoin(Site, AttendanceRecord.site_id == Site.id)
        )
        
        if not is_admin and supervisor_emp_id:
            if employee_id:
                is_auth = await AttendanceService.is_supervisor_authorized(session, supervisor_emp_id, employee_id)
                if not is_auth:
                    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot access other employee records")
                stmt = stmt.where(AttendanceRecord.employee_id == employee_id)
            else:
                stmt = (
                    stmt.outerjoin(
                        EmployeeSiteAssignment, AttendanceRecord.employee_id == EmployeeSiteAssignment.employee_id
                    )
                    .where(
                        or_(
                            Employee.supervisor_id == supervisor_emp_id,
                            Site.supervisor_id == supervisor_emp_id
                        )
                    )
                    .group_by(AttendanceRecord.id, Employee.name, Site.name)
                )
        elif employee_id:
            stmt = stmt.where(AttendanceRecord.employee_id == employee_id)
            
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total_res = await session.execute(count_stmt)
        total = total_res.scalar_one()
        
        stmt = stmt.offset(skip).limit(limit)
        result = await session.execute(stmt)
        rows = result.all()
        items = []
        for row in rows:
            rec = row[0]
            rec.employee_name = row[1]
            rec.site_name = row[2]
            items.append(rec)
        
        return items, total
