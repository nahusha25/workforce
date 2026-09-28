from datetime import date, datetime, timezone
from decimal import Decimal
from typing import List, Optional, Tuple, Union
import uuid

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.auth import User
from app.models.operations import (
    Activity,
    AttendanceRecord,
    Client,
    DailyWorkEntry,
    EmployeeSiteAssignment,
    ExceptionFlag,
    Material,
    MaterialTransaction,
    Project,
    Site,
    VerificationRecord,
    WorkOrder,
    WorkPhoto,
)
from app.models.system import AuditLog
from app.models.workforce import Employee
from app.modules.verification.exceptions import (
    InvalidVerificationStateError,
    MandatoryRemarksRequiredError,
    TargetNotFoundError,
    UnauthorizedSupervisorError,
)
from app.modules.verification.schemas import (
    EmployeeDayAttendanceDetail,
    EmployeeDayDetailResponse,
    EmployeeDayMaterialDetail,
    EmployeeDayPhotoDetail,
    EmployeeDayWorkEntryDetail,
    VerificationHistoryEvent,
    VerificationSummaryItem,
    VerificationSummaryResponse,
)


class VerificationService:
    @staticmethod
    async def is_supervisor_authorized(
        session: AsyncSession,
        supervisor_emp_id: Optional[uuid.UUID],
        target_emp_id: uuid.UUID,
        site_id: Optional[uuid.UUID] = None,
        is_admin: bool = False,
    ) -> bool:
        """Verify whether a supervisor is assigned to the target employee or site."""
        if is_admin:
            return True

        if not supervisor_emp_id:
            return False

        # 1. Direct supervisor assignment on Employee
        stmt_emp = select(Employee).where(Employee.id == target_emp_id)
        res_emp = await session.execute(stmt_emp)
        emp = res_emp.scalars().first()
        if emp and emp.supervisor_id == supervisor_emp_id:
            return True

        # 2. Check site supervisor via provided site_id
        if site_id:
            stmt_site = select(Site).where(Site.id == site_id)
            res_site = await session.execute(stmt_site)
            site = res_site.scalars().first()
            if site and site.supervisor_id == supervisor_emp_id:
                return True

        # 3. Check active assignment's site supervisor
        stmt_assign = (
            select(Site)
            .join(EmployeeSiteAssignment, EmployeeSiteAssignment.site_id == Site.id)
            .where(
                and_(
                    EmployeeSiteAssignment.employee_id == target_emp_id,
                    EmployeeSiteAssignment.is_active == True,
                    Site.supervisor_id == supervisor_emp_id,
                )
            )
        )
        res_assign = await session.execute(stmt_assign)
        if res_assign.scalars().first():
            return True

        return False

    @staticmethod
    async def compute_exception_flags(
        session: AsyncSession,
        employee_id: uuid.UUID,
        work_date: date,
        attendance_record: Optional[AttendanceRecord],
        work_entries: List[DailyWorkEntry],
        material_transactions: List[MaterialTransaction],
    ) -> List[str]:
        """Compute exception flags for a single employee on a given date."""
        flags: set[str] = set()

        # 1. Out of geofence check
        if attendance_record:
            if attendance_record.is_within_geofence is False and not attendance_record.override_by:
                flags.add("out_of_location")

            # 2. Missing checkout check
            if (
                attendance_record.check_in_time is not None
                and attendance_record.check_out_time is None
                and work_date <= date.today()
            ):
                flags.add("missing_checkout")

            # 3. Attendance without work check
            if len(work_entries) == 0:
                flags.add("attendance_without_work")

        # 4. Work without attendance check
        if len(work_entries) > 0 and not attendance_record:
            flags.add("work_without_attendance")

        # 5. Missing photo on positive-quantity work entries
        for entry in work_entries:
            if entry.quantity and float(entry.quantity) > 0:
                stmt_photo = select(func.count(WorkPhoto.id)).where(WorkPhoto.daily_work_entry_id == entry.id)
                res_photo = await session.execute(stmt_photo)
                photo_count = res_photo.scalar() or 0
                if photo_count == 0:
                    flags.add("no_photograph")
                    break

        # 6. High-value material purchase
        for mat in material_transactions:
            if mat.is_high_value:
                flags.add("high_value_material")
                break

        # 7. Check persisted unresolved ExceptionFlag records
        entity_ids = []
        if attendance_record:
            entity_ids.append(attendance_record.id)
        for e in work_entries:
            entity_ids.append(e.id)
        for m in material_transactions:
            entity_ids.append(m.id)

        if entity_ids:
            stmt_ef = select(ExceptionFlag).where(
                and_(
                    ExceptionFlag.entity_id.in_(entity_ids),
                    ExceptionFlag.is_resolved == False,
                )
            )
            res_ef = await session.execute(stmt_ef)
            for ef in res_ef.scalars().all():
                if ef.flag_type:
                    flags.add(ef.flag_type)

        return sorted(list(flags))

    @staticmethod
    async def get_eod_summary(
        session: AsyncSession,
        supervisor_emp_id: Optional[uuid.UUID],
        review_date: date,
        site_id: Optional[uuid.UUID] = None,
        is_admin: bool = False,
    ) -> VerificationSummaryResponse:
        """Aggregate EOD summary across all assigned employees for supervisor review."""
        # 1. Fetch eligible employees
        stmt_emps = (
            select(
                Employee,
                Site.id.label("active_site_id"),
                Site.name.label("active_site_name"),
            )
            .outerjoin(
                EmployeeSiteAssignment,
                and_(
                    EmployeeSiteAssignment.employee_id == Employee.id,
                    EmployeeSiteAssignment.is_active == True,
                ),
            )
            .outerjoin(Site, EmployeeSiteAssignment.site_id == Site.id)
            .where(Employee.is_active == True)
        )

        if not is_admin and supervisor_emp_id:
            stmt_emps = stmt_emps.where(
                or_(
                    Employee.supervisor_id == supervisor_emp_id,
                    Site.supervisor_id == supervisor_emp_id,
                )
            )

        if site_id:
            stmt_emps = stmt_emps.where(
                or_(
                    EmployeeSiteAssignment.site_id == site_id,
                    Site.id == site_id,
                )
            )

        res_emps = await session.execute(stmt_emps)
        emp_rows = res_emps.all()

        summary_items: List[VerificationSummaryItem] = []
        pending_count = 0

        # Unique employees
        seen_emp_ids = set()

        for emp, active_site_id, active_site_name in emp_rows:
            if emp.id in seen_emp_ids:
                continue
            seen_emp_ids.add(emp.id)

            # Query attendance for date
            stmt_att = (
                select(AttendanceRecord, Site.name.label("att_site_name"))
                .outerjoin(Site, AttendanceRecord.site_id == Site.id)
                .where(
                    and_(
                        AttendanceRecord.employee_id == emp.id,
                        AttendanceRecord.date == review_date,
                    )
                )
            )
            res_att = await session.execute(stmt_att)
            att_row = res_att.first()
            att = att_row[0] if att_row else None
            att_site_name = att_row[1] if att_row else None

            # Query daily work entries for date
            stmt_dwe = select(DailyWorkEntry).where(
                and_(
                    DailyWorkEntry.employee_id == emp.id,
                    DailyWorkEntry.work_date == review_date,
                )
            )
            res_dwe = await session.execute(stmt_dwe)
            dwe_list = res_dwe.scalars().all()
            dwe_ids = [e.id for e in dwe_list]

            # Query photos and materials if any entries exist
            photos_count = 0
            materials_list: List[MaterialTransaction] = []
            if dwe_ids:
                stmt_photo = select(func.count(WorkPhoto.id)).where(WorkPhoto.daily_work_entry_id.in_(dwe_ids))
                res_photo = await session.execute(stmt_photo)
                photos_count = res_photo.scalar() or 0

                stmt_mat = select(MaterialTransaction).where(MaterialTransaction.daily_work_entry_id.in_(dwe_ids))
                res_mat = await session.execute(stmt_mat)
                materials_list = res_mat.scalars().all()

            # Skip employees who have zero attendance and zero work on this date
            if not att and len(dwe_list) == 0:
                continue

            total_mat_cost = sum(
                (Decimal(str(m.amount)) for m in materials_list if m.amount is not None),
                Decimal("0.00"),
            )

            # Compute exception flags
            flags = await VerificationService.compute_exception_flags(
                session=session,
                employee_id=emp.id,
                work_date=review_date,
                attendance_record=att,
                work_entries=dwe_list,
                material_transactions=materials_list,
            )

            # Determine pending verification
            has_pending = False
            if att and att.status not in ("verified", "rejected"):
                has_pending = True
            elif any(e.status == "submitted" for e in dwe_list):
                has_pending = True
            elif any(m.status == "submitted" for m in materials_list):
                has_pending = True

            if has_pending:
                pending_count += 1

            summary_items.append(
                VerificationSummaryItem(
                    employee_id=emp.id,
                    employee_name=emp.name,
                    employee_code=emp.employee_code,
                    site_id=att.site_id if att else active_site_id,
                    site_name=att_site_name if att else active_site_name,
                    attendance_record_id=att.id if att else None,
                    attendance_status=att.status if att else None,
                    check_in_time=att.check_in_time if att else None,
                    check_out_time=att.check_out_time if att else None,
                    working_hours=float(att.working_hours) if att and att.working_hours else None,
                    work_entry_count=len(dwe_list),
                    photo_count=photos_count,
                    material_count=len(materials_list),
                    total_material_cost=total_mat_cost,
                    exception_flags=flags,
                    has_pending_verification=has_pending,
                )
            )

        return VerificationSummaryResponse(
            date=review_date,
            site_id=site_id,
            items=summary_items,
            total_employees=len(summary_items),
            pending_verification_count=pending_count,
        )

    @staticmethod
    async def get_employee_detail(
        session: AsyncSession,
        supervisor_emp_id: Optional[uuid.UUID],
        employee_id: uuid.UUID,
        review_date: date,
        is_admin: bool = False,
    ) -> EmployeeDayDetailResponse:
        """Fetch consolidated employee detail view for supervisor verification.

        Verification history is batch-loaded with 3 IN queries (one per entity
        type) plus a single employee-name resolution query, matching the
        list_work_entries batch-photo pattern.
        """
        stmt_emp = select(Employee).where(Employee.id == employee_id)
        res_emp = await session.execute(stmt_emp)
        emp = res_emp.scalars().first()
        if not emp:
            raise TargetNotFoundError("employee", str(employee_id))

        # Authorization check
        is_auth = await VerificationService.is_supervisor_authorized(
            session=session,
            supervisor_emp_id=supervisor_emp_id,
            target_emp_id=employee_id,
            is_admin=is_admin,
        )
        if not is_auth:
            raise UnauthorizedSupervisorError()

        # ── 1. Fetch attendance ──────────────────────────────────────────────
        stmt_att = (
            select(AttendanceRecord, Site.name.label("att_site_name"))
            .outerjoin(Site, AttendanceRecord.site_id == Site.id)
            .where(
                and_(
                    AttendanceRecord.employee_id == employee_id,
                    AttendanceRecord.date == review_date,
                )
            )
        )
        res_att = await session.execute(stmt_att)
        att_row = res_att.first()
        att = att_row[0] if att_row else None
        att_site_name = att_row[1] if att_row else None

        # ── 2. Fetch work entries ─────────────────────────────────────────────
        stmt_dwe = (
            select(
                DailyWorkEntry,
                Activity.name.label("activity_name"),
                Activity.category.label("activity_category"),
                WorkOrder.order_number.label("work_order_number"),
            )
            .join(Activity, DailyWorkEntry.activity_id == Activity.id)
            .outerjoin(WorkOrder, DailyWorkEntry.work_order_id == WorkOrder.id)
            .where(
                and_(
                    DailyWorkEntry.employee_id == employee_id,
                    DailyWorkEntry.work_date == review_date,
                )
            )
            .order_by(DailyWorkEntry.created_at.asc())
        )
        res_dwe = await session.execute(stmt_dwe)
        dwe_rows = res_dwe.all()

        dwe_objs: List[DailyWorkEntry] = [r[0] for r in dwe_rows]
        dwe_ids = [d.id for d in dwe_objs]

        # ── 3. Batch-load photos ──────────────────────────────────────────────
        photos_by_dwe: dict[uuid.UUID, list] = {d.id: [] for d in dwe_objs}
        if dwe_ids:
            stmt_photos = (
                select(WorkPhoto)
                .where(WorkPhoto.daily_work_entry_id.in_(dwe_ids))
                .order_by(WorkPhoto.uploaded_at.asc())
            )
            res_photos = await session.execute(stmt_photos)
            for p in res_photos.scalars().all():
                photos_by_dwe[p.daily_work_entry_id].append(
                    EmployeeDayPhotoDetail.model_validate(p)
                )

        # ── 4. Batch-load material transactions ───────────────────────────────
        all_mats: List[MaterialTransaction] = []
        mats_by_dwe: dict[uuid.UUID, list] = {d.id: [] for d in dwe_objs}
        mat_ids: List[uuid.UUID] = []
        if dwe_ids:
            stmt_mats = (
                select(MaterialTransaction)
                .where(MaterialTransaction.daily_work_entry_id.in_(dwe_ids))
                .order_by(MaterialTransaction.created_at.asc())
            )
            res_mats = await session.execute(stmt_mats)
            for m in res_mats.scalars().all():
                all_mats.append(m)
                mat_ids.append(m.id)
                mats_by_dwe[m.daily_work_entry_id].append(m)

        # ── 5. Batch-load verification records (3 IN queries) ─────────────────
        # attendance
        att_vr_list: List[VerificationRecord] = []
        if att:
            stmt_vr_att = (
                select(VerificationRecord)
                .where(VerificationRecord.attendance_record_id == att.id)
                .order_by(VerificationRecord.verified_at.asc())
            )
            res_vr_att = await session.execute(stmt_vr_att)
            att_vr_list = list(res_vr_att.scalars().all())

        # work entries
        dwe_vr_by_id: dict[uuid.UUID, List[VerificationRecord]] = {d.id: [] for d in dwe_objs}
        if dwe_ids:
            stmt_vr_dwe = (
                select(VerificationRecord)
                .where(VerificationRecord.daily_work_entry_id.in_(dwe_ids))
                .order_by(VerificationRecord.verified_at.asc())
            )
            res_vr_dwe = await session.execute(stmt_vr_dwe)
            for vr in res_vr_dwe.scalars().all():
                dwe_vr_by_id[vr.daily_work_entry_id].append(vr)

        # materials
        mat_vr_by_id: dict[uuid.UUID, List[VerificationRecord]] = {m.id: [] for m in all_mats}
        if mat_ids:
            stmt_vr_mat = (
                select(VerificationRecord)
                .where(VerificationRecord.material_transaction_id.in_(mat_ids))
                .order_by(VerificationRecord.verified_at.asc())
            )
            res_vr_mat = await session.execute(stmt_vr_mat)
            for vr in res_vr_mat.scalars().all():
                mat_vr_by_id[vr.material_transaction_id].append(vr)

        # ── 6. Resolve verifier names (1 employee IN query + 1 user IN query) ─
        all_vrs = att_vr_list + [
            vr for vrs in dwe_vr_by_id.values() for vr in vrs
        ] + [
            vr for vrs in mat_vr_by_id.values() for vr in vrs
        ]
        verifier_user_ids = list({vr.verified_by for vr in all_vrs})

        # Map user_id → employee name
        verifier_name_by_user_id: dict[uuid.UUID, str] = {}
        if verifier_user_ids:
            stmt_verifier_emps = select(Employee).where(
                Employee.user_id.in_(verifier_user_ids)
            )
            res_verifier_emps = await session.execute(stmt_verifier_emps)
            for e in res_verifier_emps.scalars().all():
                verifier_name_by_user_id[e.user_id] = e.name

            # Fall back to role label for any user_id without an employee row
            missing_user_ids = [
                uid for uid in verifier_user_ids if uid not in verifier_name_by_user_id
            ]
            if missing_user_ids:
                stmt_users = select(User).where(User.id.in_(missing_user_ids))
                res_users = await session.execute(stmt_users)
                for u in res_users.scalars().all():
                    role_label = u.role.replace("_", " ").title()
                    verifier_name_by_user_id[u.id] = role_label

        def build_history(vr_list: List[VerificationRecord]) -> List[VerificationHistoryEvent]:
            """Convert a list of VerificationRecord objects to VerificationHistoryEvent."""
            return [
                VerificationHistoryEvent(
                    id=vr.id,
                    action=vr.action,
                    remarks=vr.remarks,
                    verified_by=vr.verified_by,
                    verified_by_name=verifier_name_by_user_id.get(vr.verified_by, "Unknown"),
                    verified_at=vr.verified_at,
                )
                for vr in vr_list
            ]

        # ── 7. Assemble attendance detail ────────────────────────────────────
        att_detail: Optional[EmployeeDayAttendanceDetail] = None
        if att:
            # latest VR for the legacy single-action fields (preserved unchanged)
            latest_att_vr = att_vr_list[-1] if att_vr_list else None
            att_detail = EmployeeDayAttendanceDetail(
                id=att.id,
                date=att.date,
                session_number=att.session_number,
                check_in_time=att.check_in_time,
                check_in_distance_m=float(att.check_in_distance_m) if att.check_in_distance_m else None,
                check_out_time=att.check_out_time,
                check_out_distance_m=float(att.check_out_distance_m) if att.check_out_distance_m else None,
                is_within_geofence=att.is_within_geofence,
                working_hours=float(att.working_hours) if att.working_hours else None,
                overtime_hours=float(att.overtime_hours) if att.overtime_hours else None,
                status=att.status,
                override_by=att.override_by,
                verification_record_id=latest_att_vr.id if latest_att_vr else None,
                verification_action=latest_att_vr.action if latest_att_vr else None,
                verification_remarks=latest_att_vr.remarks if latest_att_vr else None,
                history=build_history(att_vr_list),
            )

        # ── 8. Assemble work entries with history ────────────────────────────
        work_entries: List[EmployeeDayWorkEntryDetail] = []
        for dwe, act_name, act_cat, wo_num in dwe_rows:
            dwe_vrs = dwe_vr_by_id.get(dwe.id, [])
            latest_dwe_vr = dwe_vrs[-1] if dwe_vrs else None

            mat_objs = mats_by_dwe.get(dwe.id, [])
            materials_detail: List[EmployeeDayMaterialDetail] = []
            for m in mat_objs:
                m_vrs = mat_vr_by_id.get(m.id, [])
                latest_m_vr = m_vrs[-1] if m_vrs else None
                materials_detail.append(
                    EmployeeDayMaterialDetail(
                        id=m.id,
                        daily_work_entry_id=m.daily_work_entry_id,
                        material_id=m.material_id,
                        site_id=m.site_id,
                        transaction_type=m.transaction_type,
                        item_name=m.item_name,
                        quantity=m.quantity,
                        amount=m.amount,
                        bill_image_url=m.bill_image_url,
                        is_high_value=m.is_high_value,
                        status=m.status,
                        verification_record_id=latest_m_vr.id if latest_m_vr else None,
                        verification_action=latest_m_vr.action if latest_m_vr else None,
                        verification_remarks=latest_m_vr.remarks if latest_m_vr else None,
                        history=build_history(m_vrs),
                    )
                )

            work_entries.append(
                EmployeeDayWorkEntryDetail(
                    id=dwe.id,
                    idempotency_key=dwe.idempotency_key,
                    activity_id=dwe.activity_id,
                    activity_name=act_name,
                    activity_category=act_cat,
                    work_order_id=dwe.work_order_id,
                    work_order_number=wo_num,
                    work_date=dwe.work_date,
                    quantity=dwe.quantity,
                    uom=dwe.uom,
                    status=dwe.status,
                    remarks=dwe.remarks,
                    verification_record_id=latest_dwe_vr.id if latest_dwe_vr else None,
                    verification_action=latest_dwe_vr.action if latest_dwe_vr else None,
                    verification_remarks=latest_dwe_vr.remarks if latest_dwe_vr else None,
                    history=build_history(dwe_vrs),
                    photos=photos_by_dwe.get(dwe.id, []),
                    materials=materials_detail,
                )
            )

        # ── 9. Exception flags ───────────────────────────────────────────────
        flags = await VerificationService.compute_exception_flags(
            session=session,
            employee_id=employee_id,
            work_date=review_date,
            attendance_record=att,
            work_entries=dwe_objs,
            material_transactions=all_mats,
        )

        # ── 10. All-verified check ───────────────────────────────────────────
        all_verified = True
        if att and att.status not in ("verified", "rejected"):
            all_verified = False
        if any(e.status not in ("approved", "rejected") for e in dwe_objs):
            all_verified = False
        if any(m.status not in ("approved", "rejected") for m in all_mats):
            all_verified = False

        return EmployeeDayDetailResponse(
            employee_id=emp.id,
            employee_name=emp.name,
            employee_code=emp.employee_code,
            date=review_date,
            site_id=att.site_id if att else None,
            site_name=att_site_name,
            attendance=att_detail,
            work_entries=work_entries,
            exception_flags=flags,
            all_verified=all_verified,
        )


    @staticmethod
    async def verify_entity(
        session: AsyncSession,
        entity_type: str,
        entity_id: uuid.UUID,
        action: str,
        idempotency_key: str,
        supervisor_user_id: uuid.UUID,
        supervisor_emp_id: Optional[uuid.UUID] = None,
        remarks: Optional[str] = None,
        is_admin: bool = False,
    ) -> Tuple[VerificationRecord, str, bool]:
        """Verify an attendance, daily work entry, or material transaction with idempotency and audit trail.

        Returns: (VerificationRecord, target_status, is_replay)
        """
        norm_entity = entity_type.lower().strip()
        if norm_entity in ("material", "material_transaction"):
            norm_entity = "material"
        elif norm_entity in ("daily_work", "daily_work_entry"):
            norm_entity = "daily_work"
        elif norm_entity in ("attendance", "attendance_record"):
            norm_entity = "attendance"
        else:
            raise InvalidVerificationStateError(f"Unsupported entity type: '{entity_type}'")

        if action not in ("approved", "rejected", "correction_required"):
            raise InvalidVerificationStateError(f"Unsupported verification action: '{action}'")

        # 1. Idempotency Key Replay Check
        stmt_idemp = select(VerificationRecord).where(VerificationRecord.idempotency_key == idempotency_key)
        res_idemp = await session.execute(stmt_idemp)
        existing_vr = res_idemp.scalars().first()
        if existing_vr:
            target_status = await VerificationService._get_target_status(session, norm_entity, entity_id)
            return existing_vr, target_status, True

        # 2. Fetch and Authorize Target Entity
        target_obj, emp_id, site_id = await VerificationService._fetch_target_entity(session, norm_entity, entity_id)

        is_auth = await VerificationService.is_supervisor_authorized(
            session=session,
            supervisor_emp_id=supervisor_emp_id,
            target_emp_id=emp_id,
            site_id=site_id,
            is_admin=is_admin,
        )
        if not is_auth:
            raise UnauthorizedSupervisorError()

        # 3. State-Machine Guard & Replay Check
        current_status = target_obj.status
        target_success_status = "verified" if norm_entity == "attendance" else "approved"

        # If already in requested status, return existing verification record if one exists
        action_matches_current = (
            (action == "approved" and current_status == target_success_status)
            or (action == current_status)
        )
        if action_matches_current:
            stmt_last = (
                select(VerificationRecord)
                .where(
                    and_(
                        VerificationRecord.verified_by == supervisor_user_id,
                        VerificationRecord.action == action,
                        VerificationRecord.attendance_record_id == entity_id
                        if norm_entity == "attendance"
                        else VerificationRecord.daily_work_entry_id == entity_id
                        if norm_entity == "daily_work"
                        else VerificationRecord.material_transaction_id == entity_id,
                    )
                )
                .order_by(VerificationRecord.verified_at.desc())
            )
            res_last = await session.execute(stmt_last)
            last_vr = res_last.scalars().first()
            if last_vr:
                return last_vr, current_status, True

        # Reopen validation (admin/director only)
        if action == "correction_required" and current_status == target_success_status:
            if not is_admin:
                raise UnauthorizedSupervisorError("Only administrators or directors can reopen an approved record")
        elif current_status not in ("submitted", "draft", "flagged"):
            raise InvalidVerificationStateError(
                f"Cannot {action} record with status '{current_status}'. Target must be submitted."
            )

        # 4. Mandatory Remarks Check
        cleaned_remarks = remarks.strip() if remarks else None
        if action in ("rejected", "correction_required"):
            if not cleaned_remarks or len(cleaned_remarks) < 10:
                raise MandatoryRemarksRequiredError(action)

        # 5. Apply Status Transition
        old_status = current_status
        new_status = ""
        if action == "approved":
            new_status = target_success_status
        elif action == "rejected":
            new_status = "rejected"
        elif action == "correction_required":
            new_status = "correction_required"

        target_obj.status = new_status

        # 6. Insert VerificationRecord
        vr = VerificationRecord(
            idempotency_key=idempotency_key,
            attendance_record_id=entity_id if norm_entity == "attendance" else None,
            daily_work_entry_id=entity_id if norm_entity == "daily_work" else None,
            material_transaction_id=entity_id if norm_entity == "material" else None,
            verified_by=supervisor_user_id,
            action=action,
            remarks=cleaned_remarks,
            verified_at=datetime.now(timezone.utc),
        )
        session.add(vr)

        # 7. Insert System AuditLog
        audit_entity = (
            "attendance_record"
            if norm_entity == "attendance"
            else "daily_work_entry"
            if norm_entity == "daily_work"
            else "material_transaction"
        )
        audit = AuditLog(
            entity_type=audit_entity,
            entity_id=entity_id,
            action=f"verify_{action}",
            changed_by=supervisor_user_id,
            previous_values={"status": old_status},
            new_values={
                "status": new_status,
                "verification_record_id": str(vr.id),
                "remarks": cleaned_remarks,
            },
        )
        session.add(audit)

        await session.commit()
        await session.refresh(vr)
        await session.refresh(target_obj)

        return vr, new_status, False

    @staticmethod
    async def _fetch_target_entity(
        session: AsyncSession, entity_type: str, entity_id: uuid.UUID
    ) -> Tuple[Union[AttendanceRecord, DailyWorkEntry, MaterialTransaction], uuid.UUID, uuid.UUID]:
        """Fetch target entity, returning (entity_obj, employee_id, site_id)."""
        if entity_type == "attendance":
            stmt = select(AttendanceRecord).where(AttendanceRecord.id == entity_id)
            res = await session.execute(stmt)
            obj = res.scalars().first()
            if not obj:
                raise TargetNotFoundError("attendance", str(entity_id))
            return obj, obj.employee_id, obj.site_id

        if entity_type == "daily_work":
            stmt = select(DailyWorkEntry).where(DailyWorkEntry.id == entity_id)
            res = await session.execute(stmt)
            obj = res.scalars().first()
            if not obj:
                raise TargetNotFoundError("daily_work", str(entity_id))
            return obj, obj.employee_id, obj.site_id

        if entity_type == "material":
            stmt = select(MaterialTransaction).where(MaterialTransaction.id == entity_id)
            res = await session.execute(stmt)
            obj = res.scalars().first()
            if not obj:
                raise TargetNotFoundError("material", str(entity_id))
            # Parent daily work entry for employee ownership
            stmt_parent = select(DailyWorkEntry).where(DailyWorkEntry.id == obj.daily_work_entry_id)
            res_parent = await session.execute(stmt_parent)
            parent = res_parent.scalars().first()
            emp_id = parent.employee_id if parent else uuid.uuid4()
            return obj, emp_id, obj.site_id

        raise InvalidVerificationStateError(f"Unsupported entity type: '{entity_type}'")

    @staticmethod
    async def _get_target_status(session: AsyncSession, entity_type: str, entity_id: uuid.UUID) -> str:
        """Fetch status of target entity for idempotency response."""
        if entity_type == "attendance":
            stmt = select(AttendanceRecord.status).where(AttendanceRecord.id == entity_id)
        elif entity_type == "daily_work":
            stmt = select(DailyWorkEntry.status).where(DailyWorkEntry.id == entity_id)
        else:
            stmt = select(MaterialTransaction.status).where(MaterialTransaction.id == entity_id)

        res = await session.execute(stmt)
        status_val = res.scalar()
        return status_val or "unknown"
