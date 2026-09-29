from typing import List, Optional, Dict
from datetime import datetime, date
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import (
    LeaveRequest, LeaveStatus, User, UserRole, Employee, Department, Designation,
    LeaveTypeConfig, DesignationChain
)
from app.schemas import (
    LeaveCreate, LeaveStatusUpdate, LeaveResponse,
    LeaveTypeConfigCreate, LeaveTypeConfigUpdate, LeaveTypeConfigResponse,
    DesignationChainCreate, DesignationChainResponse,
    MyLeaveQuotaItem, MyLeaveReportResponse,
    EmployeeLeaveReportItem, EmployeeLeaveReportSummary, EmployeeLeaveReportResponse
)
from app.security import get_current_user, RoleChecker

router = APIRouter(prefix="/leaves", tags=["Leave Management"])


def _seed_leave_defaults(db: Session):
    """Seed corporate leave types and designation chain defaults if tables are empty."""
    try:
        if db.query(LeaveTypeConfig).count() == 0:
            defaults = [
                LeaveTypeConfig(
                    name="Annual Leave",
                    code="ANNUAL",
                    days_allowed=15,
                    is_paid=True,
                    requires_attachment=False,
                    carry_forward=True,
                    is_active=True,
                    description="Standard yearly earned leave entitlement for all full-time employees."
                ),
                LeaveTypeConfig(
                    name="Casual Leave",
                    code="CASUAL",
                    days_allowed=10,
                    is_paid=True,
                    requires_attachment=False,
                    carry_forward=False,
                    is_active=True,
                    description="Short-notice personal leaves for emergencies or personal business."
                ),
                LeaveTypeConfig(
                    name="Medical & Sick Leave",
                    code="SICK",
                    days_allowed=14,
                    is_paid=True,
                    requires_attachment=True,
                    carry_forward=False,
                    is_active=True,
                    description="Health and illness absences; medical certificate required for > 2 days."
                ),
                LeaveTypeConfig(
                    name="Parental / Maternity",
                    code="PARENTAL",
                    days_allowed=90,
                    is_paid=True,
                    requires_attachment=True,
                    carry_forward=False,
                    is_active=True,
                    description="Maternity, paternity and adoption support leave policy."
                ),
                LeaveTypeConfig(
                    name="Unpaid / Sabbatical",
                    code="UNPAID",
                    days_allowed=30,
                    is_paid=False,
                    requires_attachment=False,
                    carry_forward=False,
                    is_active=True,
                    description="Extended leave without pay subject to executive board approval."
                ),
            ]
            for d in defaults:
                db.add(d)
            db.commit()

        if db.query(DesignationChain).count() == 0:
            designations = db.query(Designation).all()
            if len(designations) >= 2:
                # Create a sample hierarchy chain
                for i in range(len(designations) - 1):
                    chain = DesignationChain(
                        designation_id=designations[i].id,
                        approver_designation_id=designations[i + 1].id,
                        level=1,
                        auto_approve_days=3,
                        notes=f"{designations[i].name} submits to {designations[i + 1].name}"
                    )
                    db.add(chain)
                db.commit()
    except Exception as e:
        db.rollback()
        print(f"[Leave Seed Error] {e}")


def _calc_days(start_date: date, end_date: date) -> int:
    delta = (end_date - start_date).days + 1
    return max(1, delta)


def _format_leave(leave: LeaveRequest) -> LeaveResponse:
    emp_name = f"{leave.employee.first_name} {leave.employee.last_name}" if leave.employee else "Unknown"
    approver_name = f"{leave.approver.first_name} {leave.approver.last_name}" if leave.approver else None
    days = _calc_days(leave.start_date, leave.end_date)
    return LeaveResponse(
        id=leave.id,
        employee_id=leave.employee_id,
        employee_name=emp_name,
        leave_type=str(leave.leave_type.value if hasattr(leave.leave_type, 'value') else leave.leave_type),
        start_date=leave.start_date,
        end_date=leave.end_date,
        days_count=days,
        reason=leave.reason,
        status=leave.status,
        approved_by_id=leave.approved_by_id,
        approver_name=approver_name,
        created_at=leave.created_at
    )


# --- 1. Leave Types Endpoints ---
@router.get("/types", response_model=List[LeaveTypeConfigResponse])
def get_leave_types(db: Session = Depends(get_db)):
    _seed_leave_defaults(db)
    return db.query(LeaveTypeConfig).order_by(LeaveTypeConfig.id.asc()).all()


@router.post("/types", response_model=LeaveTypeConfigResponse)
def create_leave_type(req: LeaveTypeConfigCreate, db: Session = Depends(get_db)):
    existing = db.query(LeaveTypeConfig).filter(
        (LeaveTypeConfig.name == req.name) | (LeaveTypeConfig.code == req.code.upper())
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Leave type name or code already exists.")

    lt = LeaveTypeConfig(
        name=req.name,
        code=req.code.upper(),
        days_allowed=req.days_allowed,
        is_paid=req.is_paid,
        requires_attachment=req.requires_attachment,
        carry_forward=req.carry_forward,
        is_active=req.is_active,
        description=req.description
    )
    db.add(lt)
    db.commit()
    db.refresh(lt)
    return lt


@router.put("/types/{type_id}", response_model=LeaveTypeConfigResponse)
def update_leave_type(type_id: int, req: LeaveTypeConfigUpdate, db: Session = Depends(get_db)):
    lt = db.query(LeaveTypeConfig).filter(LeaveTypeConfig.id == type_id).first()
    if not lt:
        raise HTTPException(status_code=404, detail="Leave type not found")

    if req.name is not None:
        lt.name = req.name
    if req.code is not None:
        lt.code = req.code.upper()
    if req.days_allowed is not None:
        lt.days_allowed = req.days_allowed
    if req.is_paid is not None:
        lt.is_paid = req.is_paid
    if req.requires_attachment is not None:
        lt.requires_attachment = req.requires_attachment
    if req.carry_forward is not None:
        lt.carry_forward = req.carry_forward
    if req.is_active is not None:
        lt.is_active = req.is_active
    if req.description is not None:
        lt.description = req.description

    db.commit()
    db.refresh(lt)
    return lt


# --- 2. Designation Chain Endpoints ---
@router.get("/designation-chains", response_model=List[DesignationChainResponse])
def get_designation_chains(db: Session = Depends(get_db)):
    _seed_leave_defaults(db)
    chains = db.query(DesignationChain).order_by(DesignationChain.level.asc()).all()
    results = []
    for c in chains:
        des_name = c.designation.name if c.designation else "Unknown"
        app_name = c.approver_designation.name if c.approver_designation else "Unknown"
        results.append(DesignationChainResponse(
            id=c.id,
            designation_id=c.designation_id,
            designation_name=des_name,
            approver_designation_id=c.approver_designation_id,
            approver_designation_name=app_name,
            level=c.level,
            auto_approve_days=c.auto_approve_days,
            notes=c.notes,
            created_at=c.created_at
        ))
    return results


@router.post("/designation-chains", response_model=DesignationChainResponse)
def create_designation_chain(req: DesignationChainCreate, db: Session = Depends(get_db)):
    chain = DesignationChain(
        designation_id=req.designation_id,
        approver_designation_id=req.approver_designation_id,
        level=req.level,
        auto_approve_days=req.auto_approve_days,
        notes=req.notes
    )
    db.add(chain)
    db.commit()
    db.refresh(chain)

    des_name = chain.designation.name if chain.designation else "Unknown"
    app_name = chain.approver_designation.name if chain.approver_designation else "Unknown"
    return DesignationChainResponse(
        id=chain.id,
        designation_id=chain.designation_id,
        designation_name=des_name,
        approver_designation_id=chain.approver_designation_id,
        approver_designation_name=app_name,
        level=chain.level,
        auto_approve_days=chain.auto_approve_days,
        notes=chain.notes,
        created_at=chain.created_at
    )


@router.delete("/designation-chains/{chain_id}")
def delete_designation_chain(chain_id: int, db: Session = Depends(get_db)):
    chain = db.query(DesignationChain).filter(DesignationChain.id == chain_id).first()
    if not chain:
        raise HTTPException(status_code=404, detail="Chain rule not found")
    db.delete(chain)
    db.commit()
    return {"message": "Chain rule removed successfully"}


# --- 3. My Leave Report Endpoint ---
@router.get("/reports/my", response_model=MyLeaveReportResponse)
def get_my_leave_report(
    employee_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    _seed_leave_defaults(db)

    target_emp_id = employee_id or 1
    employee = db.query(Employee).filter(Employee.id == target_emp_id).first()
    if not employee:
        employee = db.query(Employee).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")

    emp_name = f"{employee.first_name} {employee.last_name}"
    dept_name = employee.department.name if employee.department else "General"

    # Fetch leave types
    leave_types = db.query(LeaveTypeConfig).filter(LeaveTypeConfig.is_active == True).all()

    # Fetch employee's leaves
    leaves = db.query(LeaveRequest).filter(LeaveRequest.employee_id == target_emp_id).order_by(LeaveRequest.created_at.desc()).all()

    # Calculate quotas
    quotas = []
    total_alloc = 0
    total_used = 0
    total_pending = 0

    for lt in leave_types:
        # Match leaves of this type
        matched_leaves = [
            l for l in leaves
            if (l.leave_type.value if hasattr(l.leave_type, 'value') else str(l.leave_type)).upper() == lt.code.upper()
        ]
        used_days = sum(_calc_days(l.start_date, l.end_date) for l in matched_leaves if l.status == LeaveStatus.APPROVED)
        pending_days = sum(_calc_days(l.start_date, l.end_date) for l in matched_leaves if l.status == LeaveStatus.PENDING)
        remaining = max(0, lt.days_allowed - used_days)

        total_alloc += lt.days_allowed
        total_used += used_days
        total_pending += pending_days

        quotas.append(MyLeaveQuotaItem(
            leave_type=lt.code,
            name=lt.name,
            allocated=lt.days_allowed,
            used=used_days,
            pending=pending_days,
            remaining=remaining,
            is_paid=lt.is_paid
        ))

    total_remaining = max(0, total_alloc - total_used)

    return MyLeaveReportResponse(
        employee_id=employee.id,
        employee_name=emp_name,
        department_name=dept_name,
        total_allocated=total_alloc,
        total_used=total_used,
        total_remaining=total_remaining,
        total_pending=total_pending,
        quotas=quotas,
        history=[_format_leave(l) for l in leaves]
    )


# --- 4. Employee Leave Report Endpoint (Company-Wide) ---
@router.get("/reports/employee-summary", response_model=EmployeeLeaveReportResponse)
def get_employee_leave_report(db: Session = Depends(get_db)):
    _seed_leave_defaults(db)

    employees = db.query(Employee).all()
    all_leaves = db.query(LeaveRequest).all()

    dept_counts: Dict[str, int] = {}
    emp_items: List[EmployeeLeaveReportItem] = []
    total_days_all = 0
    total_pending_all = 0
    type_counts: Dict[str, int] = {}

    for emp in employees:
        emp_name = f"{emp.first_name} {emp.last_name}"
        dept_name = emp.department.name if emp.department else "General"
        desig_name = emp.designation_rel.name if emp.designation_rel else emp.designation

        emp_leaves = [l for l in all_leaves if l.employee_id == emp.id]

        annual_used = 0
        casual_used = 0
        sick_used = 0
        other_used = 0
        pending_cnt = 0

        for l in emp_leaves:
            code = (l.leave_type.value if hasattr(l.leave_type, 'value') else str(l.leave_type)).upper()
            days = _calc_days(l.start_date, l.end_date)
            if l.status == LeaveStatus.APPROVED:
                if "ANNUAL" in code:
                    annual_used += days
                elif "CASUAL" in code:
                    casual_used += days
                elif "SICK" in code:
                    sick_used += days
                else:
                    other_used += days
                total_days_all += days
                type_counts[code] = type_counts.get(code, 0) + days
                dept_counts[dept_name] = dept_counts.get(dept_name, 0) + days
            elif l.status == LeaveStatus.PENDING:
                pending_cnt += 1
                total_pending_all += 1

        tot_used = annual_used + casual_used + sick_used + other_used
        allocated = 30
        rem_balance = max(0, allocated - tot_used)

        emp_items.append(EmployeeLeaveReportItem(
            employee_id=emp.id,
            employee_name=emp_name,
            employee_code=emp.employee_code,
            department_name=dept_name,
            designation_name=desig_name,
            annual_allocated=15,
            annual_used=annual_used,
            casual_used=casual_used,
            sick_used=sick_used,
            other_used=other_used,
            total_used=tot_used,
            remaining_balance=rem_balance,
            pending_applications=pending_cnt
        ))

    most_used = max(type_counts, key=type_counts.get) if type_counts else "ANNUAL"
    avg_leave = round(total_days_all / len(employees), 1) if employees else 0.0

    summary = EmployeeLeaveReportSummary(
        total_employees=len(employees),
        total_days_taken=total_days_all,
        avg_leave_per_emp=avg_leave,
        total_pending_requests=total_pending_all,
        most_used_leave_type=most_used
    )

    return EmployeeLeaveReportResponse(
        summary=summary,
        department_breakdown=dept_counts,
        employees=emp_items
    )


# --- 5. Standard Applications & Approvals Endpoints ---
@router.get("/", response_model=List[LeaveResponse])
def list_leaves(
    status_filter: Optional[LeaveStatus] = None,
    employee_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(LeaveRequest)
    if status_filter:
        query = query.filter(LeaveRequest.status == status_filter)
    if employee_id:
        query = query.filter(LeaveRequest.employee_id == employee_id)
    leaves = query.order_by(LeaveRequest.created_at.desc()).all()
    return [_format_leave(l) for l in leaves]


@router.post("/", response_model=LeaveResponse)
def apply_leave(req: LeaveCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    leave = LeaveRequest(
        employee_id=req.employee_id,
        leave_type=req.leave_type,
        start_date=req.start_date,
        end_date=req.end_date,
        reason=req.reason,
        status=LeaveStatus.PENDING
    )
    db.add(leave)
    db.commit()
    db.refresh(leave)
    return _format_leave(leave)


@router.put("/{leave_id}/status", response_model=LeaveResponse)
def update_leave_status(
    leave_id: int,
    status_update: LeaveStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(RoleChecker([UserRole.SUPER_ADMIN, UserRole.DEPARTMENT_HEAD, UserRole.MANAGER, UserRole.TEAM_LEADER]))
):
    leave = db.query(LeaveRequest).filter(LeaveRequest.id == leave_id).first()
    if not leave:
        raise HTTPException(status_code=404, detail="Leave request not found")

    approver_emp = db.query(Employee).filter(Employee.user_id == current_user.id).first()
    leave.status = status_update.status
    if approver_emp:
        leave.approved_by_id = approver_emp.id

    db.commit()
    db.refresh(leave)
    return _format_leave(leave)
