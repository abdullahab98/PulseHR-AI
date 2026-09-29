from typing import List, Optional
from datetime import datetime, date, timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.timezone import get_local_now, get_local_today
from app.models import (
    Attendance, AttendanceStatus, Employee, User,
    TimeSlot, AttendanceApplication, TimeSlotApplication, WeekendSetup
)
from app.schemas import (
    AttendanceResponse, CheckInRequest, CheckOutRequest,
    TimeSlotCreate, TimeSlotResponse,
    AttendanceApplicationCreate, AttendanceApplicationStatusUpdate, AttendanceApplicationResponse,
    TimeSlotApplicationCreate, TimeSlotApplicationStatusUpdate, TimeSlotApplicationResponse,
    WeekendSetupCreate, WeekendSetupResponse,
    AttendanceReportItem, AttendanceReportSummary, AttendanceReportResponse
)
from app.security import get_current_user

router = APIRouter(prefix="/attendance", tags=["Attendance Management"])

def _format_attendance(att: Attendance) -> AttendanceResponse:
    emp_name = f"{att.employee.first_name} {att.employee.last_name}" if att.employee else "Unknown"
    return AttendanceResponse(
        id=att.id,
        employee_id=att.employee_id,
        employee_name=emp_name,
        date=att.date,
        check_in=att.check_in,
        check_out=att.check_out,
        work_hours=att.work_hours,
        overtime_hours=att.overtime_hours,
        status=att.status
    )

def _get_target_employee_id(requested_emp_id: Optional[int], current_user: User, db: Session) -> int:
    if requested_emp_id:
        return requested_emp_id
    emp = db.query(Employee).filter(Employee.user_id == current_user.id).first()
    if not emp:
        raise HTTPException(status_code=400, detail="Current user has no associated employee profile")
    return emp.id

@router.get("/me/today", response_model=Optional[AttendanceResponse])
def get_my_today_attendance(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    emp = db.query(Employee).filter(Employee.user_id == current_user.id).first()
    if not emp:
        return None
    today = get_local_today()
    att = db.query(Attendance).filter(
        Attendance.employee_id == emp.id,
        Attendance.date == today
    ).first()
    if not att:
        return None
    return _format_attendance(att)

@router.post("/check-in", response_model=AttendanceResponse)
def check_in(req: CheckInRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    target_emp_id = _get_target_employee_id(req.employee_id, current_user, db)
    today = get_local_today()
    att = db.query(Attendance).filter(
        Attendance.employee_id == target_emp_id,
        Attendance.date == today
    ).first()

    now = get_local_now()
    # Check if late (after 09:30 AM local Bangladesh time)
    is_late = now.hour > 9 or (now.hour == 9 and now.minute > 30)

    if not att:
        att = Attendance(
            employee_id=target_emp_id,
            date=today,
            check_in=now,
            status=AttendanceStatus.LATE if is_late else AttendanceStatus.PRESENT
        )
        db.add(att)
    else:
        if att.check_in:
            raise HTTPException(status_code=400, detail="Employee already checked in today")
        att.check_in = now
        att.status = AttendanceStatus.LATE if is_late else AttendanceStatus.PRESENT

    db.commit()
    db.refresh(att)
    return _format_attendance(att)

@router.post("/check-out", response_model=AttendanceResponse)
def check_out(req: CheckOutRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    target_emp_id = _get_target_employee_id(req.employee_id, current_user, db)
    today = get_local_today()
    att = db.query(Attendance).filter(
        Attendance.employee_id == target_emp_id,
        Attendance.date == today
    ).first()

    if not att or not att.check_in:
        raise HTTPException(status_code=400, detail="No check-in record found for today")

    now = get_local_now()
    att.check_out = now
    
    # Calculate duration
    duration = (now - att.check_in).total_seconds() / 3600.0
    att.work_hours = round(duration, 2)
    att.overtime_hours = round(max(0.0, duration - 8.0), 2)

    db.commit()
    db.refresh(att)
    return _format_attendance(att)

@router.get("/daily", response_model=List[AttendanceResponse])
def get_daily_attendance(
    target_date: Optional[date] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query_date = target_date or get_local_today()
    records = db.query(Attendance).filter(Attendance.date == query_date).all()
    return [_format_attendance(r) for r in records]

@router.get("/employee/{employee_id}", response_model=List[AttendanceResponse])
def get_employee_attendance(
    employee_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    records = db.query(Attendance).filter(
        Attendance.employee_id == employee_id
    ).order_by(Attendance.date.desc()).limit(30).all()
    return [_format_attendance(r) for r in records]


# ==========================================
# 1. Attendance Report Endpoint
# ==========================================
@router.get("/report", response_model=AttendanceReportResponse)
def get_attendance_report(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    employee_id: Optional[int] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(Attendance)
    if start_date:
        query = query.filter(Attendance.date >= start_date)
    if end_date:
        query = query.filter(Attendance.date <= end_date)
    if employee_id:
        query = query.filter(Attendance.employee_id == employee_id)
    if status and status != "ALL":
        query = query.filter(Attendance.status == status)

    records = query.order_by(Attendance.date.desc()).all()

    # Calculate summary metrics
    total_records = len(records)
    total_present = sum(1 for r in records if r.status == AttendanceStatus.PRESENT)
    total_late = sum(1 for r in records if r.status == AttendanceStatus.LATE)
    total_absent = sum(1 for r in records if r.status == AttendanceStatus.ABSENT)
    total_overtime = sum(r.overtime_hours or 0.0 for r in records)
    total_work_hours = sum(r.work_hours or 0.0 for r in records)
    avg_work_hours = round(total_work_hours / total_records, 2) if total_records > 0 else 0.0

    items = []
    for r in records:
        emp_name = f"{r.employee.first_name} {r.employee.last_name}" if r.employee else f"Employee #{r.employee_id}"
        dept_name = r.employee.department.name if r.employee and r.employee.department else "General"
        items.append(AttendanceReportItem(
            id=r.id,
            date=r.date,
            employee_id=r.employee_id,
            employee_name=emp_name,
            department_name=dept_name,
            check_in=r.check_in,
            check_out=r.check_out,
            work_hours=r.work_hours or 0.0,
            overtime_hours=r.overtime_hours or 0.0,
            status=r.status
        ))

    return AttendanceReportResponse(
        summary=AttendanceReportSummary(
            total_records=total_records,
            total_present=total_present,
            total_late=total_late,
            total_absent=total_absent,
            total_overtime_hours=round(total_overtime, 2),
            avg_work_hours=avg_work_hours
        ),
        records=items
    )


# ==========================================
# 2. Attendance Application List Endpoints
# ==========================================
@router.get("/applications", response_model=List[AttendanceApplicationResponse])
def get_attendance_applications(
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(AttendanceApplication)
    if status and status != "ALL":
        query = query.filter(AttendanceApplication.status == status)
    apps = query.order_by(AttendanceApplication.created_at.desc()).all()

    # Seed demo applications if empty
    if not apps and not status:
        emp = db.query(Employee).first()
        if emp:
            demo_apps = [
                AttendanceApplication(
                    employee_id=emp.id,
                    date=date.today() - timedelta(days=1),
                    requested_check_in="09:05 AM",
                    requested_check_out="05:15 PM",
                    application_type="Forgot Check-in",
                    reason="Fingerprint biometric device was restarting in the morning.",
                    status="PENDING"
                ),
                AttendanceApplication(
                    employee_id=emp.id,
                    date=date.today() - timedelta(days=3),
                    requested_check_in="09:00 AM",
                    requested_check_out="06:30 PM",
                    application_type="On-Duty Visit",
                    reason="Client on-site meeting at North Campus branch.",
                    status="APPROVED"
                )
            ]
            db.add_all(demo_apps)
            db.commit()
            apps = query.order_by(AttendanceApplication.created_at.desc()).all()

    result = []
    for a in apps:
        emp_name = f"{a.employee.first_name} {a.employee.last_name}" if a.employee else f"Employee #{a.employee_id}"
        result.append(AttendanceApplicationResponse(
            id=a.id,
            employee_id=a.employee_id,
            employee_name=emp_name,
            date=a.date,
            requested_check_in=a.requested_check_in,
            requested_check_out=a.requested_check_out,
            application_type=a.application_type,
            reason=a.reason,
            status=a.status,
            created_at=a.created_at
        ))
    return result


@router.post("/applications", response_model=AttendanceApplicationResponse)
def create_attendance_application(
    req: AttendanceApplicationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    emp_id = _get_target_employee_id(req.employee_id, current_user, db)
    new_app = AttendanceApplication(
        employee_id=emp_id,
        date=req.date,
        requested_check_in=req.requested_check_in,
        requested_check_out=req.requested_check_out,
        application_type=req.application_type,
        reason=req.reason,
        status="PENDING"
    )
    db.add(new_app)
    db.commit()
    db.refresh(new_app)

    emp = db.query(Employee).filter(Employee.id == emp_id).first()
    emp_name = f"{emp.first_name} {emp.last_name}" if emp else f"Employee #{emp_id}"
    return AttendanceApplicationResponse(
        id=new_app.id,
        employee_id=new_app.employee_id,
        employee_name=emp_name,
        date=new_app.date,
        requested_check_in=new_app.requested_check_in,
        requested_check_out=new_app.requested_check_out,
        application_type=new_app.application_type,
        reason=new_app.reason,
        status=new_app.status,
        created_at=new_app.created_at
    )


@router.patch("/applications/{app_id}/status", response_model=AttendanceApplicationResponse)
def update_application_status(
    app_id: int,
    req: AttendanceApplicationStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    app = db.query(AttendanceApplication).filter(AttendanceApplication.id == app_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Attendance application not found")
    app.status = req.status.upper()
    db.commit()
    db.refresh(app)

    emp = app.employee
    emp_name = f"{emp.first_name} {emp.last_name}" if emp else f"Employee #{app.employee_id}"
    return AttendanceApplicationResponse(
        id=app.id,
        employee_id=app.employee_id,
        employee_name=emp_name,
        date=app.date,
        requested_check_in=app.requested_check_in,
        requested_check_out=app.requested_check_out,
        application_type=app.application_type,
        reason=app.reason,
        status=app.status,
        created_at=app.created_at
    )


# ==========================================
# 3. Attendance Time Slot Endpoints
# ==========================================
@router.get("/time-slots", response_model=List[TimeSlotResponse])
def get_time_slots(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    slots = db.query(TimeSlot).order_by(TimeSlot.id.asc()).all()
    if not slots:
        # Seed default industry standard time slots
        defaults = [
            TimeSlot(name="General Office Shift", start_time="09:00 AM", end_time="05:00 PM", late_grace_minutes=15, is_active=True, description="Standard corporate 8-hour schedule with 15m grace period"),
            TimeSlot(name="Early Morning Shift", start_time="07:00 AM", end_time="03:00 PM", late_grace_minutes=10, is_active=True, description="Operations and early engineering support shift"),
            TimeSlot(name="Mid-Day / Evening Shift", start_time="02:00 PM", end_time="10:00 PM", late_grace_minutes=15, is_active=True, description="Customer success and extended technical coverage"),
            TimeSlot(name="Night Shift", start_time="10:00 PM", end_time="06:00 AM", late_grace_minutes=20, is_active=True, description="24/7 Infrastructure and critical systems monitoring"),
            TimeSlot(name="Executive Flexible Band", start_time="10:00 AM", end_time="06:00 PM", late_grace_minutes=30, is_active=True, description="Flexible arrival time band for senior leaders and research staff")
        ]
        db.add_all(defaults)
        db.commit()
        slots = db.query(TimeSlot).order_by(TimeSlot.id.asc()).all()
    return slots


@router.post("/time-slots", response_model=TimeSlotResponse)
def create_time_slot(
    req: TimeSlotCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    slot = TimeSlot(
        name=req.name,
        start_time=req.start_time,
        end_time=req.end_time,
        late_grace_minutes=req.late_grace_minutes,
        is_active=req.is_active,
        description=req.description
    )
    db.add(slot)
    db.commit()
    db.refresh(slot)
    return slot


# ==========================================
# 4. Apply for New Time Slot Endpoints
# ==========================================
@router.get("/slot-applications", response_model=List[TimeSlotApplicationResponse])
def get_slot_applications(
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(TimeSlotApplication)
    if status and status != "ALL":
        query = query.filter(TimeSlotApplication.status == status)
    apps = query.order_by(TimeSlotApplication.created_at.desc()).all()

    # Seed demo slot applications if empty
    if not apps and not status:
        emp = db.query(Employee).first()
        slot = db.query(TimeSlot).first()
        if emp and slot:
            demo_slot_app = TimeSlotApplication(
                employee_id=emp.id,
                time_slot_id=slot.id,
                effective_from=date.today() + timedelta(days=7),
                reason="Relocation closer to office branch; preferred morning timing.",
                status="PENDING"
            )
            db.add(demo_slot_app)
            db.commit()
            apps = query.order_by(TimeSlotApplication.created_at.desc()).all()

    result = []
    for a in apps:
        emp_name = f"{a.employee.first_name} {a.employee.last_name}" if a.employee else f"Employee #{a.employee_id}"
        slot_name = a.time_slot.name if a.time_slot else f"Time Slot #{a.time_slot_id}"
        result.append(TimeSlotApplicationResponse(
            id=a.id,
            employee_id=a.employee_id,
            employee_name=emp_name,
            time_slot_id=a.time_slot_id,
            time_slot_name=slot_name,
            effective_from=a.effective_from,
            reason=a.reason,
            status=a.status,
            created_at=a.created_at
        ))
    return result


@router.post("/slot-applications", response_model=TimeSlotApplicationResponse)
def create_slot_application(
    req: TimeSlotApplicationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    emp_id = _get_target_employee_id(req.employee_id, current_user, db)
    slot = db.query(TimeSlot).filter(TimeSlot.id == req.time_slot_id).first()
    if not slot:
        raise HTTPException(status_code=404, detail="Selected time slot not found")

    new_app = TimeSlotApplication(
        employee_id=emp_id,
        time_slot_id=req.time_slot_id,
        effective_from=req.effective_from,
        reason=req.reason,
        status="PENDING"
    )
    db.add(new_app)
    db.commit()
    db.refresh(new_app)

    emp = db.query(Employee).filter(Employee.id == emp_id).first()
    emp_name = f"{emp.first_name} {emp.last_name}" if emp else f"Employee #{emp_id}"
    return TimeSlotApplicationResponse(
        id=new_app.id,
        employee_id=new_app.employee_id,
        employee_name=emp_name,
        time_slot_id=slot.id,
        time_slot_name=slot.name,
        effective_from=new_app.effective_from,
        reason=new_app.reason,
        status=new_app.status,
        created_at=new_app.created_at
    )


@router.patch("/slot-applications/{app_id}/status", response_model=TimeSlotApplicationResponse)
def update_slot_application_status(
    app_id: int,
    req: TimeSlotApplicationStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    app = db.query(TimeSlotApplication).filter(TimeSlotApplication.id == app_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Slot application not found")
    app.status = req.status.upper()
    db.commit()
    db.refresh(app)

    emp = app.employee
    emp_name = f"{emp.first_name} {emp.last_name}" if emp else f"Employee #{app.employee_id}"
    slot_name = app.time_slot.name if app.time_slot else f"Time Slot #{app.time_slot_id}"
    return TimeSlotApplicationResponse(
        id=app.id,
        employee_id=app.employee_id,
        employee_name=emp_name,
        time_slot_id=app.time_slot_id,
        time_slot_name=slot_name,
        effective_from=app.effective_from,
        reason=app.reason,
        status=app.status,
        created_at=app.created_at
    )


# ==========================================
# 5. Weekend Setup Endpoints
# ==========================================
@router.get("/weekend-setup", response_model=WeekendSetupResponse)
def get_weekend_setup(
    department_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(WeekendSetup)
    if department_id:
        setup = query.filter(WeekendSetup.department_id == department_id).first()
    else:
        setup = query.filter(WeekendSetup.department_id.is_(None)).first()

    if not setup:
        # Create default weekend setup
        setup = WeekendSetup(
            days=["Friday", "Saturday"],
            department_id=department_id,
            note="Official standard corporate weekend configuration"
        )
        db.add(setup)
        db.commit()
        db.refresh(setup)

    return WeekendSetupResponse(
        id=setup.id,
        days=setup.days or ["Friday", "Saturday"],
        department_id=setup.department_id,
        note=setup.note,
        updated_at=setup.updated_at
    )


@router.post("/weekend-setup", response_model=WeekendSetupResponse)
def save_weekend_setup(
    req: WeekendSetupCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(WeekendSetup)
    if req.department_id:
        setup = query.filter(WeekendSetup.department_id == req.department_id).first()
    else:
        setup = query.filter(WeekendSetup.department_id.is_(None)).first()

    if not setup:
        setup = WeekendSetup(
            days=req.days,
            department_id=req.department_id,
            note=req.note or "Updated corporate weekend setup",
            updated_at=get_local_now()
        )
        db.add(setup)
    else:
        setup.days = req.days
        setup.note = req.note or setup.note
        setup.updated_at = get_local_now()

    db.commit()
    db.refresh(setup)
    return WeekendSetupResponse(
        id=setup.id,
        days=setup.days,
        department_id=setup.department_id,
        note=setup.note,
        updated_at=setup.updated_at
    )

