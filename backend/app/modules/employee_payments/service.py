from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal, ROUND_HALF_DOWN, ROUND_HALF_UP
from typing import Dict, List, Optional, Tuple

from fastapi import HTTPException, status
from sqlalchemy import and_, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.auth import User
from app.models.employee_payments import EmployeePayment, EmployeePaymentLine
from app.models.operations import AttendanceRecord, DailyWorkEntry
from app.models.payroll_settings import PayrollOvertimeSettings
from app.models.system import AuditLog
from app.models.workforce import Employee, EmployeeRateHistory
from app.modules.employee_payments.schemas import (
    CancelPaymentRequest,
    EmployeePaymentDetailResponse,
    EmployeePaymentLineResponse,
    EmployeePaymentPreviewItem,
    EmployeePaymentPreviewResponse,
    EmployeePaymentResponse,
    GeneratePaymentRequest,
    PayPaymentRequest,
    RateBandSummaryResponse,
)


class EmployeePaymentService:
    # Canonical approved attendance statuses eligible for payroll calculation:
    # 'verified' is the approved terminal status set by VerificationService.
    # 'approved' is retained for legacy and direct test fixture compatibility.
    ELIGIBLE_ATTENDANCE_STATUSES: tuple[str, ...] = ("verified", "approved")

    @staticmethod
    async def _generate_payment_number(session: AsyncSession) -> str:
        today_str = datetime.now(timezone.utc).strftime("%Y%m%d")
        prefix = f"PAY-{today_str}-"
        stmt = select(func.count(EmployeePayment.id)).where(EmployeePayment.payment_number.like(f"{prefix}%"))
        res = await session.execute(stmt)
        count = res.scalar() or 0
        return f"{prefix}{count + 1:04d}"

    @classmethod
    async def _fetch_eligible_records_for_employee(
        cls,
        session: AsyncSession,
        employee_id: uuid.UUID,
        period_start: date,
        period_end: date,
    ) -> Tuple[List[AttendanceRecord], List[DailyWorkEntry], List[EmployeeRateHistory]]:
        """
        Fetch approved/verified attendance records and daily work entries not yet locked by active payments,
        along with the employee's rate histories overlapping the period.
        """
        # 1. Unlocked approved/verified attendance records
        att_stmt = (
            select(AttendanceRecord)
            .where(
                AttendanceRecord.employee_id == employee_id,
                AttendanceRecord.status.in_(cls.ELIGIBLE_ATTENDANCE_STATUSES),
                AttendanceRecord.date >= period_start,
                AttendanceRecord.date <= period_end,
                ~AttendanceRecord.id.in_(
                    select(EmployeePaymentLine.source_attendance_id).where(
                        EmployeePaymentLine.is_active.is_(True),
                        EmployeePaymentLine.source_attendance_id.isnot(None),
                    )
                ),
            )
            .order_by(AttendanceRecord.date.asc())
        )
        att_records = (await session.execute(att_stmt)).scalars().all()

        # 2. Unlocked approved daily work entries
        dwe_stmt = (
            select(DailyWorkEntry)
            .where(
                DailyWorkEntry.employee_id == employee_id,
                DailyWorkEntry.status == "approved",
                DailyWorkEntry.work_date >= period_start,
                DailyWorkEntry.work_date <= period_end,
                ~DailyWorkEntry.id.in_(
                    select(EmployeePaymentLine.source_daily_work_entry_id).where(
                        EmployeePaymentLine.is_active.is_(True),
                        EmployeePaymentLine.source_daily_work_entry_id.isnot(None),
                    )
                ),
            )
            .order_by(DailyWorkEntry.work_date.asc())
        )
        dwe_records = (await session.execute(dwe_stmt)).scalars().all()

        # 3. Rate history
        rate_stmt = (
            select(EmployeeRateHistory)
            .where(
                EmployeeRateHistory.employee_id == employee_id,
                EmployeeRateHistory.effective_from <= period_end,
                or_(
                    EmployeeRateHistory.effective_to.is_(None),
                    EmployeeRateHistory.effective_to >= period_start,
                ),
            )
            .order_by(EmployeeRateHistory.effective_from.asc())
        )
        rate_histories = (await session.execute(rate_stmt)).scalars().all()

        return list(att_records), list(dwe_records), list(rate_histories)

    @classmethod
    def _find_effective_rate(
        cls,
        rate_histories: List[EmployeeRateHistory],
        record_date: date,
        employee_name: str,
    ) -> EmployeeRateHistory:
        for r in rate_histories:
            if r.effective_from <= record_date and (r.effective_to is None or r.effective_to >= record_date):
                return r
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"No effective rate configured for employee '{employee_name}' on date {record_date}",
        )

    @classmethod
    async def _fetch_overtime_settings_for_period(
        cls,
        session: AsyncSession,
        period_start: date,
        period_end: date,
    ) -> List[PayrollOvertimeSettings]:
        stmt = (
            select(PayrollOvertimeSettings)
            .where(
                PayrollOvertimeSettings.effective_from <= period_end,
                or_(
                    PayrollOvertimeSettings.effective_to.is_(None),
                    PayrollOvertimeSettings.effective_to >= period_start,
                ),
            )
            .order_by(PayrollOvertimeSettings.effective_from.desc())
        )
        res = await session.execute(stmt)
        return list(res.scalars().all())

    @classmethod
    def _find_effective_overtime_setting(
        cls,
        settings: List[PayrollOvertimeSettings],
        record_date: date,
    ) -> Optional[PayrollOvertimeSettings]:
        for s in settings:
            if s.effective_from <= record_date and (s.effective_to is None or s.effective_to >= record_date):
                return s
        return None

    @staticmethod
    def _calculate_attendance_hours(att: AttendanceRecord) -> Decimal:
        """
        Rounds session duration to the nearest whole minute, then returns hours as Decimal.
        Priority:
        1. If check_in_time and check_out_time are present:
           diff_seconds = max(0.0, (check_out_time - check_in_time).total_seconds())
           rounded_minutes = (Decimal(str(diff_seconds)) / Decimal("60")).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
           return rounded_minutes / Decimal("60")
        2. Else if working_hours is present:
           diff_seconds = max(0.0, float(att.working_hours) * 3600.0)
           rounded_minutes = (Decimal(str(diff_seconds)) / Decimal("60")).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
           return rounded_minutes / Decimal("60")
        3. Else:
           return Decimal("0.00")
        """
        if att.check_in_time and att.check_out_time:
            t_in = att.check_in_time
            t_out = att.check_out_time
            if t_in.tzinfo is None and t_out.tzinfo is not None:
                t_in = t_in.replace(tzinfo=timezone.utc)
            elif t_out.tzinfo is None and t_in.tzinfo is not None:
                t_out = t_out.replace(tzinfo=timezone.utc)
            diff_seconds = max(0.0, (t_out - t_in).total_seconds())
            rounded_minutes = (Decimal(str(diff_seconds)) / Decimal("60")).quantize(
                Decimal("1"), rounding=ROUND_HALF_UP
            )
            return rounded_minutes / Decimal("60")
        elif att.working_hours is not None:
            diff_seconds = max(0.0, float(att.working_hours) * 3600.0)
            rounded_minutes = (Decimal(str(diff_seconds)) / Decimal("60")).quantize(
                Decimal("1"), rounding=ROUND_HALF_UP
            )
            return rounded_minutes / Decimal("60")
        return Decimal("0.00")

    @classmethod
    def _calculate_employee_lines(
        cls,
        employee_name: str,
        att_records: List[AttendanceRecord],
        dwe_records: List[DailyWorkEntry],
        rate_histories: List[EmployeeRateHistory],
        overtime_settings: List[PayrollOvertimeSettings],
    ) -> Tuple[List[dict], List[RateBandSummaryResponse], Decimal, Decimal, Decimal, Decimal, Decimal, Decimal]:
        """
        Calculates itemized lines and rate band summaries for an employee.
        Respects:
          - Daily: base daily rate paid once per unique attendance date.
                   overtime = overtime_hours * (daily_rate / standard_day_hours) * overtime_multiplier.
          - Weekly: unique attendance dates pro-rated across 7 calendar days ((unique_days / 7) * weekly_rate).
                    overtime = overtime_hours * (weekly_rate / 7 / standard_day_hours) * overtime_multiplier.
          - Piece: quantity * piece_rate (per daily work entry, no overtime).
        Multiple sessions per date:
          - Sum minute-rounded session hours for the date.
          - Base pay allocated to the primary session line only; subsequent session lines have days=0, regular_amount=0.
          - Regular/overtime hours allocated chronologically across sessions up to standard workday hours.
          - Snapshot fields populated on all lines and reconciled with header totals.
        """
        lines_data: List[dict] = []
        band_groups: Dict[Tuple[str, Decimal, date, Optional[date]], dict] = {}

        # 1. Group attendance records by calendar date
        att_by_date: Dict[date, List[AttendanceRecord]] = {}
        for att in att_records:
            att_by_date.setdefault(att.date, []).append(att)

        for d in sorted(att_by_date.keys()):
            eff_rate = cls._find_effective_rate(rate_histories, d, employee_name)
            rate_amount = Decimal(str(eff_rate.rate_amount))
            band_key = (eff_rate.rate_type, rate_amount, eff_rate.effective_from, eff_rate.effective_to)

            if band_key not in band_groups:
                band_groups[band_key] = {
                    "rate_type": eff_rate.rate_type,
                    "rate_amount": rate_amount,
                    "rate_effective_from": eff_rate.effective_from,
                    "rate_effective_to": eff_rate.effective_to,
                    "dates": {},
                    "dwe_records": [],
                }
            sessions = sorted(
                att_by_date[d],
                key=lambda a: (a.session_number or 1, a.check_in_time or datetime.min, a.id),
            )
            band_groups[band_key]["dates"][d] = sessions

        # 2. Process daily work entries (for piece rate type)
        for dwe in dwe_records:
            eff_rate = cls._find_effective_rate(rate_histories, dwe.work_date, employee_name)
            rate_amount = Decimal(str(eff_rate.rate_amount))
            band_key = (eff_rate.rate_type, rate_amount, eff_rate.effective_from, eff_rate.effective_to)

            if band_key not in band_groups:
                band_groups[band_key] = {
                    "rate_type": eff_rate.rate_type,
                    "rate_amount": rate_amount,
                    "rate_effective_from": eff_rate.effective_from,
                    "rate_effective_to": eff_rate.effective_to,
                    "dates": {},
                    "dwe_records": [],
                }
            if eff_rate.rate_type == "piece":
                band_groups[band_key]["dwe_records"].append(dwe)

        rate_band_summaries: List[RateBandSummaryResponse] = []

        # 3. Calculate per rate band
        for band_key, data in sorted(band_groups.items(), key=lambda x: (x[0][2], x[0][0])):
            rtype = data["rate_type"]
            ramount = data["rate_amount"]
            eff_from = data["rate_effective_from"]
            eff_to = data["rate_effective_to"]
            dates_dict = data["dates"]
            dwes = data["dwe_records"]

            if rtype == "daily":
                sorted_dates = sorted(dates_dict.keys())
                band_days = Decimal(len(sorted_dates))
                band_regular_gross = (band_days * ramount).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                band_ot_amount = Decimal("0.00")

                for d in sorted_dates:
                    sessions = dates_dict[d]
                    session_durations = [cls._calculate_attendance_hours(s) for s in sessions]

                    ot_setting = cls._find_effective_overtime_setting(overtime_settings, d)
                    if ot_setting is not None:
                        std_day_hours = Decimal(str(ot_setting.standard_workday_hours))
                        ot_mult = Decimal(str(ot_setting.overtime_multiplier))
                        hourly_equiv_exact = ramount / std_day_hours
                        # hourly_equivalent_rate stores the 2-decimal rounded snapshot for
                        # display/audit purposes. The actual overtime amount is calculated from the
                        # exact unrounded hourly equivalent rate (hourly_equiv_exact) to avoid premature
                        # intermediate rounding errors before final ROUND_HALF_UP quantizing.
                        hourly_equiv_snapshot = hourly_equiv_exact.quantize(
                            Decimal("0.01"), rounding=ROUND_HALF_UP
                        )
                    else:
                        std_day_hours = None
                        ot_mult = None
                        hourly_equiv_exact = None
                        hourly_equiv_snapshot = None

                    # Waterfall hour allocation across sessions on date d
                    cum_prev = Decimal("0.00")
                    ot_session_indices = []
                    session_reg_hours = []
                    session_ot_hours = []

                    for idx, s_hours in enumerate(session_durations):
                        cum_curr = cum_prev + s_hours
                        if std_day_hours is not None and std_day_hours > Decimal("0.00"):
                            reg_h = max(Decimal("0.00"), min(cum_curr, std_day_hours) - min(cum_prev, std_day_hours))
                            ot_h = max(Decimal("0.00"), cum_curr - max(cum_prev, std_day_hours))
                        else:
                            reg_h = s_hours
                            ot_h = Decimal("0.00")

                        reg_h_q = reg_h.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                        ot_h_q = ot_h.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                        session_reg_hours.append(reg_h_q)
                        session_ot_hours.append(ot_h_q)
                        if ot_h_q > Decimal("0.00"):
                            ot_session_indices.append(idx)
                        cum_prev = cum_curr

                    date_ot_hours = sum(session_ot_hours, Decimal("0.00"))
                    if ot_setting is not None and date_ot_hours > Decimal("0.00") and hourly_equiv_exact is not None:
                        date_ot_amount = (date_ot_hours * hourly_equiv_exact * ot_mult).quantize(
                            Decimal("0.01"), rounding=ROUND_HALF_UP
                        )
                    else:
                        date_ot_amount = Decimal("0.00")

                    ot_amounts_allocated = Decimal("0.00")
                    for idx, att in enumerate(sessions):
                        is_primary = (idx == 0)
                        line_days = Decimal("1.00") if is_primary else Decimal("0.00")
                        line_reg_amt = ramount.quantize(Decimal("0.01")) if is_primary else Decimal("0.00")

                        ot_h_q = session_ot_hours[idx]
                        if ot_h_q > Decimal("0.00") and ot_mult is not None and hourly_equiv_exact is not None:
                            if idx == ot_session_indices[-1]:
                                line_ot_amt = date_ot_amount - ot_amounts_allocated
                            else:
                                line_ot_amt = (ot_h_q * hourly_equiv_exact * ot_mult).quantize(
                                    Decimal("0.01"), rounding=ROUND_HALF_UP
                                )
                                ot_amounts_allocated += line_ot_amt
                        else:
                            line_ot_amt = Decimal("0.00")

                        line_total_amt = line_reg_amt + line_ot_amt

                        lines_data.append({
                            "source_attendance_id": att.id,
                            "source_daily_work_entry_id": None,
                            "source_date": d,
                            "rate_type": rtype,
                            "rate_amount": ramount,
                            "rate_effective_from": eff_from,
                            "rate_effective_to": eff_to,
                            "days": line_days,
                            "quantity": Decimal("0.00"),
                            "regular_hours": session_reg_hours[idx],
                            "overtime_hours": ot_h_q,
                            "standard_day_hours": std_day_hours,
                            "hourly_equivalent_rate": hourly_equiv_snapshot,
                            "overtime_multiplier": ot_mult,
                            "regular_amount": line_reg_amt,
                            "overtime_amount": line_ot_amt,
                            "amount": line_total_amt,
                        })

                    band_ot_amount += date_ot_amount

                band_gross = band_regular_gross + band_ot_amount
                rate_band_summaries.append(
                    RateBandSummaryResponse(
                        rate_type=rtype,
                        rate_amount=ramount,
                        rate_effective_from=eff_from,
                        rate_effective_to=eff_to,
                        approved_days=band_days,
                        approved_quantity=Decimal("0.00"),
                        gross_amount=band_gross,
                    )
                )

            elif rtype == "weekly":
                sorted_dates = sorted(dates_dict.keys())
                band_days = Decimal(len(sorted_dates))
                band_regular_gross = ((band_days * ramount) / Decimal("7")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                band_ot_amount = Decimal("0.00")

                if band_days > 0:
                    per_day_base = (band_regular_gross / band_days).quantize(Decimal("0.01"), rounding=ROUND_HALF_DOWN)
                else:
                    per_day_base = Decimal("0.00")

                accumulated_base = Decimal("0.00")

                for d_idx, d in enumerate(sorted_dates):
                    is_last_date = (d_idx == len(sorted_dates) - 1)
                    if is_last_date:
                        date_reg_pay = band_regular_gross - accumulated_base
                    else:
                        date_reg_pay = per_day_base
                        accumulated_base += date_reg_pay

                    sessions = dates_dict[d]
                    session_durations = [cls._calculate_attendance_hours(s) for s in sessions]

                    ot_setting = cls._find_effective_overtime_setting(overtime_settings, d)
                    if ot_setting is not None:
                        std_day_hours = Decimal(str(ot_setting.standard_workday_hours))
                        ot_mult = Decimal(str(ot_setting.overtime_multiplier))
                        hourly_equiv_exact = (ramount / Decimal("7")) / std_day_hours
                        # hourly_equivalent_rate stores the 2-decimal rounded snapshot for
                        # display/audit purposes. The actual overtime amount is calculated from the
                        # exact unrounded hourly equivalent rate (hourly_equiv_exact) to avoid premature
                        # intermediate rounding errors before final ROUND_HALF_UP quantizing.
                        hourly_equiv_snapshot = hourly_equiv_exact.quantize(
                            Decimal("0.01"), rounding=ROUND_HALF_UP
                        )
                    else:
                        std_day_hours = None
                        ot_mult = None
                        hourly_equiv_exact = None
                        hourly_equiv_snapshot = None

                    cum_prev = Decimal("0.00")
                    ot_session_indices = []
                    session_reg_hours = []
                    session_ot_hours = []

                    for idx, s_hours in enumerate(session_durations):
                        cum_curr = cum_prev + s_hours
                        if std_day_hours is not None and std_day_hours > Decimal("0.00"):
                            reg_h = max(Decimal("0.00"), min(cum_curr, std_day_hours) - min(cum_prev, std_day_hours))
                            ot_h = max(Decimal("0.00"), cum_curr - max(cum_prev, std_day_hours))
                        else:
                            reg_h = s_hours
                            ot_h = Decimal("0.00")

                        reg_h_q = reg_h.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                        ot_h_q = ot_h.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                        session_reg_hours.append(reg_h_q)
                        session_ot_hours.append(ot_h_q)
                        if ot_h_q > Decimal("0.00"):
                            ot_session_indices.append(idx)
                        cum_prev = cum_curr

                    date_ot_hours = sum(session_ot_hours, Decimal("0.00"))
                    if ot_setting is not None and date_ot_hours > Decimal("0.00") and hourly_equiv_exact is not None:
                        date_ot_amount = (date_ot_hours * hourly_equiv_exact * ot_mult).quantize(
                            Decimal("0.01"), rounding=ROUND_HALF_UP
                        )
                    else:
                        date_ot_amount = Decimal("0.00")

                    ot_amounts_allocated = Decimal("0.00")
                    for idx, att in enumerate(sessions):
                        is_primary = (idx == 0)
                        line_days = Decimal("1.00") if is_primary else Decimal("0.00")
                        line_reg_amt = date_reg_pay if is_primary else Decimal("0.00")

                        ot_h_q = session_ot_hours[idx]
                        if ot_h_q > Decimal("0.00") and ot_mult is not None and hourly_equiv_exact is not None:
                            if idx == ot_session_indices[-1]:
                                line_ot_amt = date_ot_amount - ot_amounts_allocated
                            else:
                                line_ot_amt = (ot_h_q * hourly_equiv_exact * ot_mult).quantize(
                                    Decimal("0.01"), rounding=ROUND_HALF_UP
                                )
                                ot_amounts_allocated += line_ot_amt
                        else:
                            line_ot_amt = Decimal("0.00")

                        line_total_amt = line_reg_amt + line_ot_amt

                        lines_data.append({
                            "source_attendance_id": att.id,
                            "source_daily_work_entry_id": None,
                            "source_date": d,
                            "rate_type": rtype,
                            "rate_amount": ramount,
                            "rate_effective_from": eff_from,
                            "rate_effective_to": eff_to,
                            "days": line_days,
                            "quantity": Decimal("0.00"),
                            "regular_hours": session_reg_hours[idx],
                            "overtime_hours": ot_h_q,
                            "standard_day_hours": std_day_hours,
                            "hourly_equivalent_rate": hourly_equiv_snapshot,
                            "overtime_multiplier": ot_mult,
                            "regular_amount": line_reg_amt,
                            "overtime_amount": line_ot_amt,
                            "amount": line_total_amt,
                        })

                    band_ot_amount += date_ot_amount

                band_gross = band_regular_gross + band_ot_amount
                rate_band_summaries.append(
                    RateBandSummaryResponse(
                        rate_type=rtype,
                        rate_amount=ramount,
                        rate_effective_from=eff_from,
                        rate_effective_to=eff_to,
                        approved_days=band_days,
                        approved_quantity=Decimal("0.00"),
                        gross_amount=band_gross,
                    )
                )

            elif rtype == "monthly":
                sorted_dates = sorted(dates_dict.keys())
                band_days = Decimal(len(sorted_dates))
                # Standard monthly pay: 30-day basis pro-rated across attendance dates
                band_regular_gross = ((band_days * ramount) / Decimal("30")).quantize(
                    Decimal("0.01"), rounding=ROUND_HALF_UP
                )
                band_ot_amount = Decimal("0.00")

                if band_days > 0:
                    per_day_base = (band_regular_gross / band_days).quantize(
                        Decimal("0.01"), rounding=ROUND_HALF_DOWN
                    )
                else:
                    per_day_base = Decimal("0.00")

                accumulated_base = Decimal("0.00")

                for d_idx, d in enumerate(sorted_dates):
                    is_last_date = (d_idx == len(sorted_dates) - 1)
                    if is_last_date:
                        date_reg_pay = band_regular_gross - accumulated_base
                    else:
                        date_reg_pay = per_day_base
                        accumulated_base += date_reg_pay

                    sessions = dates_dict[d]
                    session_durations = [cls._calculate_attendance_hours(s) for s in sessions]

                    # Standard working time is 8 hours per day, 1x normal rate
                    std_day_hours = Decimal("8.00")
                    ot_mult = Decimal("1.00")

                    hourly_equiv_exact = (ramount / Decimal("30")) / std_day_hours
                    hourly_equiv_snapshot = hourly_equiv_exact.quantize(
                        Decimal("0.01"), rounding=ROUND_HALF_UP
                    )

                    # Waterfall hour allocation across sessions on date d
                    cum_prev = Decimal("0.00")
                    ot_session_indices = []
                    session_reg_hours = []
                    session_ot_hours = []

                    for idx, s_hours in enumerate(session_durations):
                        cum_curr = cum_prev + s_hours
                        if std_day_hours is not None and std_day_hours > Decimal("0.00"):
                            reg_h = max(
                                Decimal("0.00"),
                                min(cum_curr, std_day_hours) - min(cum_prev, std_day_hours),
                            )
                            ot_h = max(Decimal("0.00"), cum_curr - max(cum_prev, std_day_hours))
                        else:
                            reg_h = s_hours
                            ot_h = Decimal("0.00")

                        reg_h_q = reg_h.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                        ot_h_q = ot_h.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                        session_reg_hours.append(reg_h_q)
                        session_ot_hours.append(ot_h_q)
                        if ot_h_q > Decimal("0.00"):
                            ot_session_indices.append(idx)
                        cum_prev = cum_curr

                    date_ot_hours = sum(session_ot_hours, Decimal("0.00"))
                    if date_ot_hours > Decimal("0.00") and hourly_equiv_exact is not None:
                        date_ot_amount = (date_ot_hours * hourly_equiv_exact * ot_mult).quantize(
                            Decimal("0.01"), rounding=ROUND_HALF_UP
                        )
                    else:
                        date_ot_amount = Decimal("0.00")

                    ot_amounts_allocated = Decimal("0.00")
                    for idx, att in enumerate(sessions):
                        is_primary = (idx == 0)
                        line_days = Decimal("1.00") if is_primary else Decimal("0.00")
                        line_reg_amt = date_reg_pay if is_primary else Decimal("0.00")

                        ot_h_q = session_ot_hours[idx]
                        if ot_h_q > Decimal("0.00") and ot_mult is not None and hourly_equiv_exact is not None:
                            if idx == ot_session_indices[-1]:
                                line_ot_amt = date_ot_amount - ot_amounts_allocated
                            else:
                                line_ot_amt = (ot_h_q * hourly_equiv_exact * ot_mult).quantize(
                                    Decimal("0.01"), rounding=ROUND_HALF_UP
                                )
                                ot_amounts_allocated += line_ot_amt
                        else:
                            line_ot_amt = Decimal("0.00")

                        line_total_amt = line_reg_amt + line_ot_amt

                        lines_data.append({
                            "source_attendance_id": att.id,
                            "source_daily_work_entry_id": None,
                            "source_date": d,
                            "rate_type": rtype,
                            "rate_amount": ramount,
                            "rate_effective_from": eff_from,
                            "rate_effective_to": eff_to,
                            "days": line_days,
                            "quantity": Decimal("0.00"),
                            "regular_hours": session_reg_hours[idx],
                            "overtime_hours": ot_h_q,
                            "standard_day_hours": std_day_hours,
                            "hourly_equivalent_rate": hourly_equiv_snapshot,
                            "overtime_multiplier": ot_mult,
                            "regular_amount": line_reg_amt,
                            "overtime_amount": line_ot_amt,
                            "amount": line_total_amt,
                        })

                    band_ot_amount += date_ot_amount

                band_gross = band_regular_gross + band_ot_amount
                rate_band_summaries.append(
                    RateBandSummaryResponse(
                        rate_type=rtype,
                        rate_amount=ramount,
                        rate_effective_from=eff_from,
                        rate_effective_to=eff_to,
                        approved_days=band_days,
                        approved_quantity=Decimal("0.00"),
                        gross_amount=band_gross,
                    )
                )

            elif rtype == "piece":
                band_qty = Decimal(sum(d.quantity for d in dwes if d.quantity))
                band_gross = Decimal("0.00")
                for dwe in dwes:
                    dwe_qty = Decimal(str(dwe.quantity))
                    line_amt = (dwe_qty * ramount).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                    band_gross += line_amt
                    lines_data.append({
                        "source_attendance_id": None,
                        "source_daily_work_entry_id": dwe.id,
                        "source_date": dwe.work_date,
                        "rate_type": rtype,
                        "rate_amount": ramount,
                        "rate_effective_from": eff_from,
                        "rate_effective_to": eff_to,
                        "days": Decimal("0.00"),
                        "quantity": dwe_qty,
                        "regular_hours": None,
                        "overtime_hours": Decimal("0.00"),
                        "standard_day_hours": None,
                        "hourly_equivalent_rate": None,
                        "overtime_multiplier": None,
                        "regular_amount": line_amt,
                        "overtime_amount": Decimal("0.00"),
                        "amount": line_amt,
                    })
                rate_band_summaries.append(
                    RateBandSummaryResponse(
                        rate_type=rtype,
                        rate_amount=ramount,
                        rate_effective_from=eff_from,
                        rate_effective_to=eff_to,
                        approved_days=Decimal("0.00"),
                        approved_quantity=band_qty,
                        gross_amount=band_gross,
                    )
                )

        total_days = sum((l["days"] for l in lines_data), Decimal("0.00"))
        total_qty = sum((l["quantity"] for l in lines_data), Decimal("0.00"))
        total_regular_amount = sum((l["regular_amount"] for l in lines_data if l["regular_amount"] is not None), Decimal("0.00"))
        total_overtime_hours = sum((l["overtime_hours"] for l in lines_data if l["overtime_hours"] is not None), Decimal("0.00"))
        total_overtime_amount = sum((l["overtime_amount"] for l in lines_data if l["overtime_amount"] is not None), Decimal("0.00"))
        total_amount = sum((l["amount"] for l in lines_data), Decimal("0.00"))

        return (
            lines_data,
            rate_band_summaries,
            total_days,
            total_qty,
            total_regular_amount,
            total_overtime_hours,
            total_overtime_amount,
            total_amount,
        )

    @classmethod
    async def preview_payments(
        cls,
        session: AsyncSession,
        period_start: date,
        period_end: date,
        employee_id: Optional[uuid.UUID] = None,
    ) -> EmployeePaymentPreviewResponse:
        """
        Pre-calculates payments for the period without persisting any database records.
        """
        ot_settings = await cls._fetch_overtime_settings_for_period(session, period_start, period_end)

        emp_stmt = select(Employee).where(Employee.is_active.is_(True))
        if employee_id:
            emp_stmt = emp_stmt.where(Employee.id == employee_id)
        emp_stmt = emp_stmt.order_by(Employee.name.asc())
        employees = (await session.execute(emp_stmt)).scalars().all()

        items: List[EmployeePaymentPreviewItem] = []
        grand_total_regular = Decimal("0.00")
        grand_total_ot_hours = Decimal("0.00")
        grand_total_ot_amount = Decimal("0.00")
        grand_total = Decimal("0.00")

        for emp in employees:
            atts, dwes, rates = await cls._fetch_eligible_records_for_employee(
                session, emp.id, period_start, period_end
            )
            if not atts and not dwes:
                continue

            (
                lines,
                summaries,
                t_days,
                t_qty,
                t_reg_amt,
                t_ot_hrs,
                t_ot_amt,
                t_amt,
            ) = cls._calculate_employee_lines(
                emp.name, atts, dwes, rates, ot_settings
            )
            if lines:
                items.append(
                    EmployeePaymentPreviewItem(
                        employee_id=emp.id,
                        employee_name=emp.name,
                        period_start=period_start,
                        period_end=period_end,
                        rate_band_summaries=summaries,
                        total_days=t_days,
                        total_quantity=t_qty,
                        total_regular_amount=t_reg_amt,
                        total_overtime_hours=t_ot_hrs,
                        total_overtime_amount=t_ot_amt,
                        total_amount=t_amt,
                        eligible_attendance_count=len(atts),
                        eligible_work_entry_count=len(dwes),
                    )
                )
                grand_total_regular += t_reg_amt
                grand_total_ot_hours += t_ot_hrs
                grand_total_ot_amount += t_ot_amt
                grand_total += t_amt

        return EmployeePaymentPreviewResponse(
            period_start=period_start,
            period_end=period_end,
            total_employees=len(items),
            grand_total_regular_amount=grand_total_regular,
            grand_total_overtime_hours=grand_total_ot_hours,
            grand_total_overtime_amount=grand_total_ot_amount,
            grand_total_amount=grand_total,
            items=items,
        )

    @classmethod
    async def generate_payments(
        cls,
        session: AsyncSession,
        request: GeneratePaymentRequest,
        current_user: User,
    ) -> List[EmployeePaymentResponse]:
        """
        Generates draft employee payment records with source locks, snapshot metadata, and idempotency protection.
        """
        # Idempotency check:
        # Check if payment with exact idempotency key exists (or with batch prefix if multi-employee)
        if request.employee_id:
            idemp_stmt = select(EmployeePayment).where(EmployeePayment.idempotency_key == request.idempotency_key)
        else:
            idemp_stmt = select(EmployeePayment).where(
                or_(
                    EmployeePayment.idempotency_key == request.idempotency_key,
                    EmployeePayment.idempotency_key.like(f"{request.idempotency_key}:%"),
                )
            )
        existing = (await session.execute(idemp_stmt)).scalars().all()
        if existing:
            # Replay existing payment
            emp_ids = [p.employee_id for p in existing]
            emp_map = {e.id: e.name for e in (await session.execute(select(Employee).where(Employee.id.in_(emp_ids)))).scalars().all()}
            res = []
            for p in existing:
                resp = EmployeePaymentResponse.model_validate(p)
                resp.employee_name = emp_map.get(p.employee_id)
                res.append(resp)
            return res

        ot_settings = await cls._fetch_overtime_settings_for_period(session, request.period_start, request.period_end)

        # Fetch employees to process
        emp_stmt = select(Employee).where(Employee.is_active.is_(True))
        if request.employee_id:
            emp_stmt = emp_stmt.where(Employee.id == request.employee_id)
        emp_stmt = emp_stmt.order_by(Employee.name.asc())
        employees = (await session.execute(emp_stmt)).scalars().all()

        created_payments: List[EmployeePayment] = []

        try:
            for emp in employees:
                atts, dwes, rates = await cls._fetch_eligible_records_for_employee(
                    session, emp.id, request.period_start, request.period_end
                )
                if not atts and not dwes:
                    continue

                (
                    lines_data,
                    summaries,
                    t_days,
                    t_qty,
                    t_reg_amt,
                    t_ot_hrs,
                    t_ot_amt,
                    t_amt,
                ) = cls._calculate_employee_lines(
                    emp.name, atts, dwes, rates, ot_settings
                )
                if not lines_data:
                    continue

                # Generate payment number and unique per-employee idempotency key if batch
                pay_num = await cls._generate_payment_number(session)
                emp_idemp = (
                    request.idempotency_key
                    if request.employee_id
                    else f"{request.idempotency_key}:{emp.id}"
                )

                payment = EmployeePayment(
                    payment_number=pay_num,
                    idempotency_key=emp_idemp,
                    employee_id=emp.id,
                    period_start=request.period_start,
                    period_end=request.period_end,
                    status="draft",
                    total_amount=t_amt,
                    total_regular_amount=t_reg_amt,
                    total_overtime_hours=t_ot_hrs,
                    total_overtime_amount=t_ot_amt,
                    total_days=t_days,
                    total_quantity=t_qty,
                    created_by=current_user.id,
                )
                session.add(payment)
                await session.flush()

                for l in lines_data:
                    has_att = l["source_attendance_id"] is not None
                    has_dwe = l["source_daily_work_entry_id"] is not None
                    if (has_att and has_dwe) or (not has_att and not has_dwe):
                        raise HTTPException(
                            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                            detail="Each payment line must have exactly one source reference (attendance or work entry).",
                        )
                    line = EmployeePaymentLine(
                        payment_id=payment.id,
                        source_attendance_id=l["source_attendance_id"],
                        source_daily_work_entry_id=l["source_daily_work_entry_id"],
                        source_date=l["source_date"],
                        rate_type=l["rate_type"],
                        rate_amount=l["rate_amount"],
                        rate_effective_from=l["rate_effective_from"],
                        rate_effective_to=l["rate_effective_to"],
                        days=l["days"],
                        quantity=l["quantity"],
                        regular_hours=l["regular_hours"],
                        overtime_hours=l["overtime_hours"],
                        standard_day_hours=l["standard_day_hours"],
                        hourly_equivalent_rate=l["hourly_equivalent_rate"],
                        overtime_multiplier=l["overtime_multiplier"],
                        regular_amount=l["regular_amount"],
                        overtime_amount=l["overtime_amount"],
                        amount=l["amount"],
                        is_active=True,
                    )
                    session.add(line)

                created_payments.append(payment)

            if not created_payments:
                if request.employee_id:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="No eligible approved attendance or work records found for this employee in the specified period.",
                    )
                return []

            await session.commit()

        except IntegrityError as exc:
            await session.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="One or more selected records are already part of an active payment or duplicate idempotency key was submitted concurrently.",
            ) from exc

        # Assemble responses with employee names
        results: List[EmployeePaymentResponse] = []
        for p in created_payments:
            await session.refresh(p)
            resp = EmployeePaymentResponse.model_validate(p)
            emp_obj = next((e for e in employees if e.id == p.employee_id), None)
            resp.employee_name = emp_obj.name if emp_obj else None
            results.append(resp)

        return results

    @classmethod
    async def get_payment(
        cls,
        session: AsyncSession,
        payment_id: uuid.UUID,
    ) -> EmployeePaymentDetailResponse:
        """
        Get payment details by ID, including itemized lines and aggregated rate band summaries.
        """
        stmt = (
            select(EmployeePayment)
            .options(selectinload(EmployeePayment.lines), selectinload(EmployeePayment.employee))
            .where(EmployeePayment.id == payment_id)
        )
        payment = (await session.execute(stmt)).scalar_one_or_none()
        if not payment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Employee payment with ID '{payment_id}' not found.",
            )

        # Build rate band summaries from lines
        band_map: Dict[Tuple[str, Decimal, date, Optional[date]], dict] = {}
        line_responses: List[EmployeePaymentLineResponse] = []

        for line in payment.lines:
            line_responses.append(EmployeePaymentLineResponse.model_validate(line))
            key = (line.rate_type, line.rate_amount, line.rate_effective_from, line.rate_effective_to)
            if key not in band_map:
                band_map[key] = {
                    "rate_type": line.rate_type,
                    "rate_amount": line.rate_amount,
                    "rate_effective_from": line.rate_effective_from,
                    "rate_effective_to": line.rate_effective_to,
                    "approved_days": Decimal("0.00"),
                    "approved_quantity": Decimal("0.00"),
                    "gross_amount": Decimal("0.00"),
                }
            band_map[key]["approved_days"] += line.days
            band_map[key]["approved_quantity"] += line.quantity
            band_map[key]["gross_amount"] += line.amount

        summaries = [
            RateBandSummaryResponse(**v)
            for v in sorted(band_map.values(), key=lambda x: (x["rate_effective_from"], x["rate_type"]))
        ]

        resp = EmployeePaymentDetailResponse.model_validate(payment)
        resp.employee_name = payment.employee.name if payment.employee else None
        resp.lines = line_responses
        resp.rate_band_summaries = summaries
        return resp

    @classmethod
    async def list_payments(
        cls,
        session: AsyncSession,
        period_start: Optional[date] = None,
        period_end: Optional[date] = None,
        employee_id: Optional[uuid.UUID] = None,
        status_filter: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[EmployeePaymentResponse]:
        """
        List employee payments matching filters.
        """
        stmt = (
            select(EmployeePayment)
            .options(selectinload(EmployeePayment.employee))
            .order_by(EmployeePayment.created_at.desc())
        )
        if period_start:
            stmt = stmt.where(EmployeePayment.period_start >= period_start)
        if period_end:
            stmt = stmt.where(EmployeePayment.period_end <= period_end)
        if employee_id:
            stmt = stmt.where(EmployeePayment.employee_id == employee_id)
        if status_filter:
            stmt = stmt.where(EmployeePayment.status == status_filter)

        stmt = stmt.offset(offset).limit(limit)
        payments = (await session.execute(stmt)).scalars().all()

        results: List[EmployeePaymentResponse] = []
        for p in payments:
            resp = EmployeePaymentResponse.model_validate(p)
            resp.employee_name = p.employee.name if p.employee else None
            results.append(resp)
        return results

    @classmethod
    async def approve_payment(
        cls,
        session: AsyncSession,
        payment_id: uuid.UUID,
        current_user: User,
    ) -> EmployeePaymentDetailResponse:
        """
        Transitions draft -> approved.
        """
        stmt = (
            select(EmployeePayment)
            .options(selectinload(EmployeePayment.lines), selectinload(EmployeePayment.employee))
            .where(EmployeePayment.id == payment_id)
        )
        payment = (await session.execute(stmt)).scalar_one_or_none()
        if not payment:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")

        if payment.status != "draft":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot approve payment with status '{payment.status}'. Only draft payments can be approved.",
            )

        payment.status = "approved"
        payment.approved_by = current_user.id
        payment.approved_at = datetime.now(timezone.utc)
        await session.commit()
        await session.refresh(payment)

        return await cls.get_payment(session, payment.id)

    @classmethod
    async def mark_as_paid(
        cls,
        session: AsyncSession,
        payment_id: uuid.UUID,
        request: PayPaymentRequest,
        current_user: User,
    ) -> EmployeePaymentDetailResponse:
        """
        Transitions approved -> paid. Records payment method, date, reference, and remarks.
        """
        stmt = (
            select(EmployeePayment)
            .options(selectinload(EmployeePayment.lines), selectinload(EmployeePayment.employee))
            .where(EmployeePayment.id == payment_id)
        )
        payment = (await session.execute(stmt)).scalar_one_or_none()
        if not payment:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")

        if payment.status == "draft":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Payment must be approved before being marked as paid.",
            )
        if payment.status in ("paid", "cancelled"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot pay payment with status '{payment.status}'.",
            )

        payment.status = "paid"
        payment.paid_by = current_user.id
        payment.paid_at = datetime.now(timezone.utc)
        if request.payment_date:
            payment.payment_date = request.payment_date
        elif payment.period_end:
            # Monthly salary is paid on the 1st of every month
            y = payment.period_end.year
            m = payment.period_end.month + 1
            if m > 12:
                m = 1
                y += 1
            payment.payment_date = date(y, m, 1)
        else:
            today = date.today()
            payment.payment_date = date(today.year, today.month, 1)
        payment.payment_method = request.payment_method
        payment.reference_number = request.reference_number
        payment.remarks = request.remarks
        await session.commit()
        await session.refresh(payment)

        return await cls.get_payment(session, payment.id)

    @classmethod
    async def cancel_payment(
        cls,
        session: AsyncSession,
        payment_id: uuid.UUID,
        request: CancelPaymentRequest,
        current_user: User,
    ) -> EmployeePaymentDetailResponse:
        """
        Transitions draft or approved -> cancelled.
        Deactivates lines (is_active = False) so source records become eligible for billing again.
        """
        stmt = (
            select(EmployeePayment)
            .options(selectinload(EmployeePayment.lines), selectinload(EmployeePayment.employee))
            .where(EmployeePayment.id == payment_id)
        )
        payment = (await session.execute(stmt)).scalar_one_or_none()
        if not payment:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")

        if payment.status == "paid":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot cancel an already paid payment in V1.",
            )
        if payment.status == "cancelled":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Payment is already cancelled.",
            )

        old_status = payment.status
        payment.status = "cancelled"
        payment.cancelled_by = current_user.id
        payment.cancelled_at = datetime.now(timezone.utc)
        payment.cancellation_reason = request.cancellation_reason

        # Deactivate all line items to release locks on source records
        for line in payment.lines:
            line.is_active = False

        audit_entry = AuditLog(
            id=uuid.uuid4(),
            entity_type="employee_payment",
            entity_id=payment.id,
            action="employee_payment_cancelled",
            changed_by=current_user.id,
            created_at=payment.cancelled_at,
            previous_values={
                "status": old_status,
                "payment_number": payment.payment_number,
                "total_amount": str(payment.total_amount),
                "total_days": str(payment.total_days),
                "total_quantity": str(payment.total_quantity),
            },
            new_values={
                "status": "cancelled",
                "cancellation_reason": payment.cancellation_reason,
            },
        )
        session.add(audit_entry)

        await session.commit()
        await session.refresh(payment)

        return await cls.get_payment(session, payment.id)
