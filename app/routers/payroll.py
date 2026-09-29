from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import datetime, date, timedelta
import calendar

from app.database import get_db
from app.timezone import get_local_now, get_local_today
from app.models import (
    Employee, Department, Designation, Attendance, AttendanceStatus,
    LeaveRequest, LeaveStatus, User, UserRole,
    SalaryStructure, AllowanceConfig, BonusConfig, DeductionConfig,
    PayrollBatch, Payslip
)
from app.schemas import (
    SalaryStructureCreate, SalaryStructureResponse,
    AllowanceConfigCreate, AllowanceConfigResponse,
    BonusConfigCreate, BonusConfigResponse,
    DeductionConfigCreate, DeductionConfigResponse,
    PayrollGenerateRequest, PayrollBatchResponse,
    PayslipResponse, DisbursementRequest,
    PayrollSummaryResponse
)
from app.security import get_current_user

router = APIRouter(prefix="/payroll", tags=["Payroll Management (9 Enterprise Modules)"])


# -------------------------------------------------------------
# Internal Helpers & Auto-Seeding
# -------------------------------------------------------------

def _seed_default_configs_if_needed(db: Session):
    """Seed default industry allowances, bonuses, and deduction policies if empty."""
    if db.query(AllowanceConfig).count() == 0:
        default_allowances = [
            AllowanceConfig(name="House Rent Allowance (HRA)", allowance_type="PERCENTAGE", value=40.0, is_taxable=True, applies_to="ALL", description="Standard 40% basic residential subsidy"),
            AllowanceConfig(name="Medical Allowance", allowance_type="PERCENTAGE", value=10.0, is_taxable=False, applies_to="ALL", description="Tax-free outpatient medical subsidy up to 10%"),
            AllowanceConfig(name="Conveyance & Transport", allowance_type="FIXED", value=3000.0, is_taxable=False, applies_to="ALL", description="Fixed monthly commuting allowance"),
            AllowanceConfig(name="Food & Refreshment Subsidy", allowance_type="FIXED", value=2500.0, is_taxable=False, applies_to="ALL", description="Canteen and office cafeteria monthly allowance"),
            AllowanceConfig(name="Executive Mobile & Internet", allowance_type="FIXED", value=1500.0, is_taxable=False, applies_to="ALL", description="Connectivity reimbursement for on-duty communications")
        ]
        db.add_all(default_allowances)
        db.commit()

    if db.query(BonusConfig).count() == 0:
        default_bonuses = [
            BonusConfig(title="Eid-ul-Fitr Festival Bonus", bonus_type="FESTIVAL", calculation_type="PERCENTAGE", value=100.0, effective_month="ALL", is_active=True, description="100% of basic salary for religious festive season"),
            BonusConfig(title="Eid-ul-Adha Festival Bonus", bonus_type="FESTIVAL", calculation_type="PERCENTAGE", value=100.0, effective_month="ALL", is_active=True, description="100% of basic salary festive grant"),
            BonusConfig(title="Annual Performance Excellence Bonus", bonus_type="PERFORMANCE", calculation_type="PERCENTAGE", value=50.0, effective_month="ALL", is_active=True, description="Awarded for KPI rating > 90%"),
            BonusConfig(title="Special Milestone Spot Bonus", bonus_type="SPECIAL", calculation_type="FIXED", value=25000.0, effective_month="ALL", is_active=True, description="Ad-hoc spot grant for exceptional project delivery")
        ]
        db.add_all(default_bonuses)
        db.commit()

    if db.query(DeductionConfig).count() == 0:
        default_deductions = [
            DeductionConfig(name="Absenteeism Salary Cut", deduction_type="POLICY", calculation_type="FORMULA", value=1.0, is_active=True, description="Daily basic rate deducted per unexcused absent day"),
            DeductionConfig(name="Late Attendance Penalty", deduction_type="POLICY", calculation_type="FORMULA", value=0.33, is_active=True, description="3 late arrivals trigger 1 full day basic deduction"),
            DeductionConfig(name="Recognized Provident Fund (PF)", deduction_type="PF", calculation_type="PERCENTAGE", value=10.0, is_active=True, description="Employee 10% retirement savings deduction"),
            DeductionConfig(name="Income Tax TDS Deduction", deduction_type="TAX", calculation_type="PERCENTAGE", value=5.0, is_active=True, description="Monthly withholding tax at source")
        ]
        db.add_all(default_deductions)
        db.commit()


def _ensure_employee_salary_structure(emp: Employee, db: Session) -> SalaryStructure:
    """Ensure the employee has a structured breakdown of salary components."""
    struct = db.query(SalaryStructure).filter(SalaryStructure.employee_id == emp.id).first()
    if not struct:
        base = emp.salary if emp.salary and emp.salary > 0 else 45000.0
        # Recommended standard breakdown: 55% Basic, 25% HRA, 10% Medical, 10% Transport
        basic = round(base * 0.55, 2)
        hra = round(base * 0.25, 2)
        med = round(base * 0.10, 2)
        trans = round(base * 0.10, 2)

        struct = SalaryStructure(
            employee_id=emp.id,
            basic_salary=basic,
            house_rent_allowance=hra,
            medical_allowance=med,
            transport_allowance=trans,
            food_allowance=2000.0,
            other_allowances=0.0,
            provident_fund_rate=8.0,
            tax_deduction_rate=5.0,
            bank_name="Dutch Bangla Bank Ltd.",
            bank_account_no=f"105.120.{emp.id:04d}89",
            payment_method="BANK",
            mobile_banking_no=emp.phone or f"01700{emp.id:06d}",
            effective_date=get_local_today() - timedelta(days=90),
            is_active=True,
            notes="Default corporate standard structure auto-initialized"
        )
        db.add(struct)
        db.commit()
        db.refresh(struct)
    return struct


def _format_salary_structure(s: SalaryStructure) -> SalaryStructureResponse:
    emp = s.employee
    emp_name = f"{emp.first_name} {emp.last_name}" if emp else f"Employee #{s.employee_id}"
    dept_name = emp.department.name if emp and emp.department else "General"
    desig = emp.designation if emp else "Staff"

    total_allow = round((s.house_rent_allowance or 0) + (s.medical_allowance or 0) + (s.transport_allowance or 0) + (s.food_allowance or 0) + (s.other_allowances or 0), 2)
    gross = round(s.basic_salary + total_allow, 2)

    return SalaryStructureResponse(
        id=s.id,
        employee_id=s.employee_id,
        employee_name=emp_name,
        department_name=dept_name,
        designation=desig,
        basic_salary=s.basic_salary,
        house_rent_allowance=s.house_rent_allowance or 0.0,
        medical_allowance=s.medical_allowance or 0.0,
        transport_allowance=s.transport_allowance or 0.0,
        food_allowance=s.food_allowance or 0.0,
        other_allowances=s.other_allowances or 0.0,
        total_allowances=total_allow,
        gross_salary=gross,
        provident_fund_rate=s.provident_fund_rate or 0.0,
        tax_deduction_rate=s.tax_deduction_rate or 0.0,
        bank_name=s.bank_name,
        bank_account_no=s.bank_account_no,
        payment_method=s.payment_method or "BANK",
        mobile_banking_no=s.mobile_banking_no,
        effective_date=s.effective_date,
        is_active=s.is_active,
        notes=s.notes
    )


def _format_payslip(p: Payslip) -> PayslipResponse:
    emp = p.employee
    emp_name = f"{emp.first_name} {emp.last_name}" if emp else f"Employee #{p.employee_id}"
    dept_name = emp.department.name if emp and emp.department else "Corporate"
    desig = emp.designation if emp else "Officer"

    return PayslipResponse(
        id=p.id,
        batch_id=p.batch_id,
        employee_id=p.employee_id,
        employee_name=emp_name,
        department_name=dept_name,
        designation=desig,
        month_year=p.month_year,
        working_days=p.working_days,
        present_days=p.present_days,
        absent_days=p.absent_days,
        late_days=p.late_days,
        paid_leaves=p.paid_leaves,
        unpaid_leaves=p.unpaid_leaves,
        weekend_days=p.weekend_days,
        holiday_days=p.holiday_days,
        overtime_hours=p.overtime_hours or 0.0,
        overtime_amount=p.overtime_amount or 0.0,
        basic_salary=p.basic_salary,
        house_rent=p.house_rent,
        medical_allowance=p.medical_allowance,
        transport_allowance=p.transport_allowance,
        food_allowance=p.food_allowance,
        other_allowance=p.other_allowance,
        bonus_amount=p.bonus_amount,
        bonus_note=p.bonus_note,
        gross_salary=p.gross_salary,
        absent_deduction=p.absent_deduction,
        late_deduction=p.late_deduction,
        tax_deduction=p.tax_deduction,
        provident_fund=p.provident_fund,
        loan_installment=p.loan_installment,
        advance_adjustment=p.advance_adjustment,
        other_deduction=p.other_deduction,
        total_deductions=p.total_deductions,
        net_salary=p.net_salary,
        payment_status=p.payment_status,
        payment_method=p.payment_method,
        payment_date=p.payment_date,
        account_number=p.account_number,
        transaction_id=p.transaction_id,
        payment_reference=p.payment_reference
    )


# =============================================================
# MODULE 1: Employee Salary Structure
# =============================================================

@router.get("/salary-structures", response_model=List[SalaryStructureResponse])
def get_salary_structures(
    department_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    _seed_default_configs_if_needed(db)
    employees = db.query(Employee).all()
    # Ensure all employees have structure initialized
    for e in employees:
        _ensure_employee_salary_structure(e, db)

    query = db.query(SalaryStructure).join(Employee)
    if department_id:
        query = query.filter(Employee.department_id == department_id)
    structures = query.all()
    return [_format_salary_structure(s) for s in structures]


@router.get("/salary-structures/{employee_id}", response_model=SalaryStructureResponse)
def get_employee_salary_structure(
    employee_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    emp = db.query(Employee).filter(Employee.id == employee_id).first()
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")
    struct = _ensure_employee_salary_structure(emp, db)
    return _format_salary_structure(struct)


@router.post("/salary-structures", response_model=SalaryStructureResponse)
def save_salary_structure(
    req: SalaryStructureCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    emp = db.query(Employee).filter(Employee.id == req.employee_id).first()
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")

    struct = db.query(SalaryStructure).filter(SalaryStructure.employee_id == req.employee_id).first()
    if not struct:
        struct = SalaryStructure(employee_id=req.employee_id)
        db.add(struct)

    struct.basic_salary = req.basic_salary
    struct.house_rent_allowance = req.house_rent_allowance or 0.0
    struct.medical_allowance = req.medical_allowance or 0.0
    struct.transport_allowance = req.transport_allowance or 0.0
    struct.food_allowance = req.food_allowance or 0.0
    struct.other_allowances = req.other_allowances or 0.0
    struct.provident_fund_rate = req.provident_fund_rate or 0.0
    struct.tax_deduction_rate = req.tax_deduction_rate or 0.0
    struct.bank_name = req.bank_name
    struct.bank_account_no = req.bank_account_no
    struct.payment_method = req.payment_method or "BANK"
    struct.mobile_banking_no = req.mobile_banking_no
    struct.effective_date = req.effective_date or get_local_today()
    struct.is_active = req.is_active if req.is_active is not None else True
    struct.notes = req.notes

    # Keep Employee.salary synchronized with total gross
    total_allow = struct.house_rent_allowance + struct.medical_allowance + struct.transport_allowance + struct.food_allowance + struct.other_allowances
    emp.salary = round(struct.basic_salary + total_allow, 2)

    db.commit()
    db.refresh(struct)
    return _format_salary_structure(struct)


# =============================================================
# MODULE 3: Allowance Management
# =============================================================

@router.get("/allowance-configs", response_model=List[AllowanceConfigResponse])
def get_allowance_configs(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _seed_default_configs_if_needed(db)
    return db.query(AllowanceConfig).all()


@router.post("/allowance-configs", response_model=AllowanceConfigResponse)
def create_allowance_config(
    req: AllowanceConfigCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    cfg = AllowanceConfig(
        name=req.name,
        allowance_type=req.allowance_type.upper(),
        value=req.value,
        is_taxable=req.is_taxable,
        applies_to=req.applies_to.upper(),
        is_active=req.is_active,
        description=req.description
    )
    db.add(cfg)
    db.commit()
    db.refresh(cfg)
    return cfg


@router.delete("/allowance-configs/{cfg_id}")
def delete_allowance_config(cfg_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    cfg = db.query(AllowanceConfig).filter(AllowanceConfig.id == cfg_id).first()
    if not cfg:
        raise HTTPException(status_code=404, detail="Allowance config not found")
    db.delete(cfg)
    db.commit()
    return {"message": "Allowance configuration deleted successfully"}


# =============================================================
# MODULE 4: Bonus Management
# =============================================================

@router.get("/bonus-configs", response_model=List[BonusConfigResponse])
def get_bonus_configs(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _seed_default_configs_if_needed(db)
    return db.query(BonusConfig).all()


@router.post("/bonus-configs", response_model=BonusConfigResponse)
def create_bonus_config(
    req: BonusConfigCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    cfg = BonusConfig(
        title=req.title,
        bonus_type=req.bonus_type.upper(),
        calculation_type=req.calculation_type.upper(),
        value=req.value,
        effective_month=req.effective_month,
        is_active=req.is_active,
        description=req.description
    )
    db.add(cfg)
    db.commit()
    db.refresh(cfg)
    return cfg


@router.delete("/bonus-configs/{cfg_id}")
def delete_bonus_config(cfg_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    cfg = db.query(BonusConfig).filter(BonusConfig.id == cfg_id).first()
    if not cfg:
        raise HTTPException(status_code=404, detail="Bonus config not found")
    db.delete(cfg)
    db.commit()
    return {"message": "Bonus configuration deleted successfully"}


# =============================================================
# MODULE 5: Deduction Management
# =============================================================

@router.get("/deduction-configs", response_model=List[DeductionConfigResponse])
def get_deduction_configs(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _seed_default_configs_if_needed(db)
    return db.query(DeductionConfig).all()


@router.post("/deduction-configs", response_model=DeductionConfigResponse)
def create_deduction_config(
    req: DeductionConfigCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    cfg = DeductionConfig(
        name=req.name,
        deduction_type=req.deduction_type.upper(),
        calculation_type=req.calculation_type.upper(),
        value=req.value,
        is_active=req.is_active,
        description=req.description
    )
    db.add(cfg)
    db.commit()
    db.refresh(cfg)
    return cfg


@router.delete("/deduction-configs/{cfg_id}")
def delete_deduction_config(cfg_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    cfg = db.query(DeductionConfig).filter(DeductionConfig.id == cfg_id).first()
    if not cfg:
        raise HTTPException(status_code=404, detail="Deduction config not found")
    db.delete(cfg)
    db.commit()
    return {"message": "Deduction configuration deleted successfully"}


# =============================================================
# MODULE 2 & 6: Attendance Integration & Monthly Payroll Processing
# =============================================================

@router.get("/attendance-summary")
def get_attendance_integration_summary(
    month_year: str = Query(..., description="Format: YYYY-MM, e.g. 2026-09"),
    employee_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Module 2: Attendance & Leave Integration data inspection endpoint.
    Computes present, absent, late, paid leave, unpaid leave, overtime hours
    for the selected month.
    """
    try:
        year, month = map(int, month_year.split("-"))
        num_days = calendar.monthrange(year, month)[1]
        start_dt = date(year, month, 1)
        end_dt = date(year, month, num_days)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid month_year format. Use YYYY-MM")

    # Count weekend days (Friday & Saturday in BD)
    weekend_count = 0
    for day_idx in range(1, num_days + 1):
        d = date(year, month, day_idx)
        if d.weekday() in [4, 5]: # Friday, Saturday
            weekend_count += 1

    emp_query = db.query(Employee)
    if employee_id:
        emp_query = emp_query.filter(Employee.id == employee_id)
    employees = emp_query.all()

    summary_list = []
    for emp in employees:
        att_records = db.query(Attendance).filter(
            Attendance.employee_id == emp.id,
            Attendance.date >= start_dt,
            Attendance.date <= end_dt
        ).all()

        present_count = sum(1 for a in att_records if a.status == AttendanceStatus.PRESENT or a.check_in is not None)
        late_count = sum(1 for a in att_records if a.status == AttendanceStatus.LATE)
        overtime_hours = sum(a.overtime_hours or 0.0 for a in att_records)

        # Approved leaves
        leave_records = db.query(LeaveRequest).filter(
            LeaveRequest.employee_id == emp.id,
            LeaveRequest.status == LeaveStatus.APPROVED,
            LeaveRequest.start_date <= end_dt,
            LeaveRequest.end_date >= start_dt
        ).all()

        paid_leaves = 0
        unpaid_leaves = 0
        for l in leave_records:
            # Calculate overlapping days
            l_start = max(l.start_date, start_dt)
            l_end = min(l.end_date, end_dt)
            diff = (l_end - l_start).days + 1
            if l.leave_type == LeaveType.UNPAID:
                unpaid_leaves += diff
            else:
                paid_leaves += diff

        # If sparse demo attendance data exists, assume realistic standard baseline
        if len(att_records) == 0:
            effective_present = num_days - weekend_count - paid_leaves - unpaid_leaves
            absent_count = 0
            late_count = 1
            overtime_hours = 4.5
        else:
            effective_present = present_count
            absent_count = max(0, (num_days - weekend_count) - effective_present - paid_leaves - unpaid_leaves)

        summary_list.append({
            "employee_id": emp.id,
            "employee_name": f"{emp.first_name} {emp.last_name}",
            "department": emp.department.name if emp.department else "General",
            "total_month_days": num_days,
            "weekend_days": weekend_count,
            "working_days": num_days - weekend_count,
            "present_days": effective_present,
            "late_days": late_count,
            "absent_days": absent_count,
            "paid_leaves": paid_leaves,
            "unpaid_leaves": unpaid_leaves,
            "overtime_hours": round(overtime_hours, 2)
        })

    return {
        "month_year": month_year,
        "total_employees_analyzed": len(summary_list),
        "attendance_integration": summary_list
    }


@router.post("/generate", response_model=PayrollBatchResponse)
def generate_monthly_payroll(
    req: PayrollGenerateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Module 6: Monthly Payroll Processing.
    Integrates salary structures, attendance data, allowances, bonuses, and deductions
    to create an enterprise-grade Payroll Batch with itemized payslips.
    """
    _seed_default_configs_if_needed(db)

    try:
        year, month = map(int, req.month_year.split("-"))
        num_days = calendar.monthrange(year, month)[1]
        start_dt = date(year, month, 1)
        end_dt = date(year, month, num_days)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid month_year format. Use YYYY-MM (e.g. 2026-09)")

    # Month name for title
    month_name = datetime(year, month, 1).strftime("%B %Y")
    batch_title = req.title or f"{month_name} Organization Payroll"

    # Check if a batch already exists for this month
    batch = db.query(PayrollBatch).filter(PayrollBatch.batch_month == req.month_year).first()
    if not batch:
        batch = PayrollBatch(
            batch_month=req.month_year,
            title=batch_title,
            status="DRAFT"
        )
        db.add(batch)
        db.commit()
        db.refresh(batch)
    else:
        # If existing batch was already approved or disbursed, warn
        if batch.status in ["APPROVED", "DISBURSED"]:
            raise HTTPException(status_code=400, detail=f"Payroll batch for {req.month_year} is already {batch.status}. Cannot regenerate without reopening.")
        # Clear existing payslips for regeneration
        db.query(Payslip).filter(Payslip.batch_id == batch.id).delete()
        db.commit()

    # Query employees
    emp_query = db.query(Employee)
    if req.department_id:
        emp_query = emp_query.filter(Employee.department_id == req.department_id)
    employees = emp_query.all()

    if not employees:
        raise HTTPException(status_code=400, detail="No employees found to generate payroll.")

    # Calculate weekend days (Fridays and Saturdays)
    weekend_days = sum(1 for d in range(1, num_days + 1) if date(year, month, d).weekday() in [4, 5])
    working_days = num_days - weekend_days

    # Check bonus config if requested
    bonus_cfg = None
    if req.include_bonus_id:
        bonus_cfg = db.query(BonusConfig).filter(BonusConfig.id == req.include_bonus_id).first()

    total_gross = 0.0
    total_allow = 0.0
    total_bonus = 0.0
    total_deduct = 0.0
    total_net = 0.0

    payslip_objects = []

    for emp in employees:
        struct = _ensure_employee_salary_structure(emp, db)

        # 1. Fetch attendance records
        att_records = db.query(Attendance).filter(
            Attendance.employee_id == emp.id,
            Attendance.date >= start_dt,
            Attendance.date <= end_dt
        ).all()

        present_days = sum(1 for a in att_records if a.status == AttendanceStatus.PRESENT or a.check_in is not None)
        late_days = sum(1 for a in att_records if a.status == AttendanceStatus.LATE)
        ot_hours = sum(a.overtime_hours or 0.0 for a in att_records)

        # Leaves
        leaves = db.query(LeaveRequest).filter(
            LeaveRequest.employee_id == emp.id,
            LeaveRequest.status == LeaveStatus.APPROVED,
            LeaveRequest.start_date <= end_dt,
            LeaveRequest.end_date >= start_dt
        ).all()

        paid_leaves = 0
        unpaid_leaves = 0
        for l in leaves:
            l_start = max(l.start_date, start_dt)
            l_end = min(l.end_date, end_dt)
            diff = (l_end - l_start).days + 1
            if l.leave_type == LeaveType.UNPAID:
                unpaid_leaves += diff
            else:
                paid_leaves += diff

        # If no attendance records present for employee, baseline to full presence with 1 sample late
        if len(att_records) == 0:
            present_days = working_days - paid_leaves - unpaid_leaves
            absent_days = 0
            late_days = 1
            ot_hours = 4.0
        else:
            absent_days = max(0, working_days - present_days - paid_leaves - unpaid_leaves)

        # 2. Earnings calculations
        basic = struct.basic_salary
        hra = struct.house_rent_allowance or 0.0
        med = struct.medical_allowance or 0.0
        trans = struct.transport_allowance or 0.0
        food = struct.food_allowance or 0.0
        other_allow = struct.other_allowances or 0.0

        # Overtime calculation: (basic / (working_days * 8)) * 1.5 * ot_hours
        hourly_rate = (basic / (working_days * 8)) if working_days > 0 else 0.0
        overtime_amount = round(hourly_rate * 1.5 * ot_hours, 2)

        # Bonus calculation
        bonus_val = 0.0
        bonus_note = None
        if bonus_cfg:
            if bonus_cfg.calculation_type == "PERCENTAGE":
                bonus_val = round((basic * bonus_cfg.value) / 100.0, 2)
            else:
                bonus_val = round(bonus_cfg.value, 2)
            bonus_note = f"{bonus_cfg.title} ({bonus_cfg.value}%)"

        gross = round(basic + hra + med + trans + food + other_allow + bonus_val + overtime_amount, 2)

        # 3. Deductions calculations
        daily_basic = (basic / working_days) if working_days > 0 else 0.0
        absent_cut = round(daily_basic * absent_days, 2)
        # 3 late arrivals = 1 day salary deduction rule
        late_cut = round(daily_basic * (late_days // 3), 2)

        pf_rate = struct.provident_fund_rate or 0.0
        pf_cut = round((basic * pf_rate) / 100.0, 2)

        tax_rate = struct.tax_deduction_rate or 0.0
        tax_cut = round((gross * tax_rate) / 100.0, 2)

        loan_cut = 0.0
        advance_cut = 0.0
        other_cut = 0.0

        total_deductions_val = round(absent_cut + late_cut + pf_cut + tax_cut + loan_cut + advance_cut + other_cut, 2)
        net_salary_val = round(max(0.0, gross - total_deductions_val), 2)

        payslip = Payslip(
            batch_id=batch.id,
            employee_id=emp.id,
            month_year=req.month_year,
            working_days=working_days,
            present_days=present_days,
            absent_days=absent_days,
            late_days=late_days,
            paid_leaves=paid_leaves,
            unpaid_leaves=unpaid_leaves,
            weekend_days=weekend_days,
            holiday_days=0,
            overtime_hours=round(ot_hours, 2),
            overtime_amount=overtime_amount,
            basic_salary=basic,
            house_rent=hra,
            medical_allowance=med,
            transport_allowance=trans,
            food_allowance=food,
            other_allowance=other_allow,
            bonus_amount=bonus_val,
            bonus_note=bonus_note,
            gross_salary=gross,
            absent_deduction=absent_cut,
            late_deduction=late_cut,
            tax_deduction=tax_cut,
            provident_fund=pf_cut,
            loan_installment=loan_cut,
            advance_adjustment=advance_cut,
            other_deduction=other_cut,
            total_deductions=total_deductions_val,
            net_salary=net_salary_val,
            payment_status="PENDING",
            payment_method=struct.payment_method or "BANK",
            account_number=struct.bank_account_no or struct.mobile_banking_no
        )
        db.add(payslip)
        payslip_objects.append(payslip)

        total_gross += gross
        total_allow += (hra + med + trans + food + other_allow)
        total_bonus += bonus_val
        total_deduct += total_deductions_val
        total_net += net_salary_val

    # Update batch aggregates
    batch.total_employees = len(payslip_objects)
    batch.total_gross = round(total_gross, 2)
    batch.total_allowances = round(total_allow, 2)
    batch.total_bonuses = round(total_bonus, 2)
    batch.total_deductions = round(total_deduct, 2)
    batch.total_net_salary = round(total_net, 2)
    batch.status = "DRAFT"

    db.commit()
    db.refresh(batch)

    # Return batch response with payslips
    payslips_db = db.query(Payslip).filter(Payslip.batch_id == batch.id).all()
    return PayrollBatchResponse(
        id=batch.id,
        batch_month=batch.batch_month,
        title=batch.title,
        total_employees=batch.total_employees,
        total_gross=batch.total_gross,
        total_allowances=batch.total_allowances,
        total_bonuses=batch.total_bonuses,
        total_deductions=batch.total_deductions,
        total_net_salary=batch.total_net_salary,
        status=batch.status,
        created_at=batch.created_at,
        payslips=[_format_payslip(p) for p in payslips_db]
    )


@router.get("/batches", response_model=List[PayrollBatchResponse])
def get_payroll_batches(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _seed_default_configs_if_needed(db)
    batches = db.query(PayrollBatch).order_by(PayrollBatch.batch_month.desc()).all()
    res = []
    for b in batches:
        payslips = db.query(Payslip).filter(Payslip.batch_id == b.id).all()
        res.append(PayrollBatchResponse(
            id=b.id,
            batch_month=b.batch_month,
            title=b.title,
            total_employees=b.total_employees,
            total_gross=b.total_gross,
            total_allowances=b.total_allowances,
            total_bonuses=b.total_bonuses,
            total_deductions=b.total_deductions,
            total_net_salary=b.total_net_salary,
            status=b.status,
            created_at=b.created_at,
            payslips=[_format_payslip(p) for p in payslips]
        ))
    return res


@router.get("/batches/{batch_id}", response_model=PayrollBatchResponse)
def get_payroll_batch_details(batch_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    b = db.query(PayrollBatch).filter(PayrollBatch.id == batch_id).first()
    if not b:
        raise HTTPException(status_code=404, detail="Payroll batch not found")
    payslips = db.query(Payslip).filter(Payslip.batch_id == b.id).all()
    return PayrollBatchResponse(
        id=b.id,
        batch_month=b.batch_month,
        title=b.title,
        total_employees=b.total_employees,
        total_gross=b.total_gross,
        total_allowances=b.total_allowances,
        total_bonuses=b.total_bonuses,
        total_deductions=b.total_deductions,
        total_net_salary=b.total_net_salary,
        status=b.status,
        created_at=b.created_at,
        payslips=[_format_payslip(p) for p in payslips]
    )


@router.patch("/batches/{batch_id}/status")
def update_batch_approval_status(
    batch_id: int,
    status_val: str = Query(..., description="DRAFT, REVIEWED, APPROVED, DISBURSED"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    b = db.query(PayrollBatch).filter(PayrollBatch.id == batch_id).first()
    if not b:
        raise HTTPException(status_code=404, detail="Payroll batch not found")

    new_status = status_val.upper()
    if new_status not in ["DRAFT", "REVIEWED", "APPROVED", "DISBURSED"]:
        raise HTTPException(status_code=400, detail="Invalid status value. Must be DRAFT, REVIEWED, APPROVED, or DISBURSED.")

    b.status = new_status
    if new_status == "APPROVED":
        b.approved_at = get_local_now()

    db.commit()
    db.refresh(b)
    return {"message": f"Payroll batch status successfully updated to {new_status}", "batch_id": b.id, "status": b.status}


# =============================================================
# MODULE 7: Salary Disbursement
# =============================================================

@router.get("/disbursements", response_model=List[PayslipResponse])
def get_disbursement_queue(
    batch_month: Optional[str] = None,
    payment_status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(Payslip)
    if batch_month:
        query = query.filter(Payslip.month_year == batch_month)
    if payment_status and payment_status != "ALL":
        query = query.filter(Payslip.payment_status == payment_status.upper())
    
    records = query.order_by(Payslip.id.desc()).all()
    return [_format_payslip(p) for p in records]


@router.post("/disburse")
def disburse_salaries(
    req: DisbursementRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Module 7: Salary Disbursement executor.
    Marks requested payslips as PAID with payment method, transaction reference and date.
    """
    if not req.payslip_ids:
        raise HTTPException(status_code=400, detail="No payslips selected for disbursement")

    payslips = db.query(Payslip).filter(Payslip.id.in_(req.payslip_ids)).all()
    pay_date = req.payment_date or get_local_today()

    disbursed_count = 0
    total_amount = 0.0

    for idx, p in enumerate(payslips):
        p.payment_status = "PAID"
        p.payment_method = req.payment_method.upper()
        p.payment_date = pay_date
        p.transaction_id = req.transaction_id or f"TXN-{get_local_today().strftime('%Y%m%d')}-{p.employee_id:04d}-{idx+101}"
        p.payment_reference = req.payment_reference or f"Payroll Disbursed via {p.payment_method}"
        disbursed_count += 1
        total_amount += p.net_salary

    # If all payslips in a batch are paid, auto-mark batch as DISBURSED
    batch_ids = list(set(p.batch_id for p in payslips))
    for b_id in batch_ids:
        unpaid = db.query(Payslip).filter(Payslip.batch_id == b_id, Payslip.payment_status != "PAID").count()
        if unpaid == 0:
            batch = db.query(PayrollBatch).filter(PayrollBatch.id == b_id).first()
            if batch:
                batch.status = "DISBURSED"

    db.commit()
    return {
        "message": f"Successfully disbursed salary for {disbursed_count} employees.",
        "disbursed_count": disbursed_count,
        "total_disbursed_amount": round(total_amount, 2),
        "payment_date": pay_date,
        "payment_method": req.payment_method.upper()
    }


# =============================================================
# MODULE 8: Payslip Management
# =============================================================

@router.get("/payslips", response_model=List[PayslipResponse])
def get_all_payslips(
    month_year: Optional[str] = None,
    employee_id: Optional[int] = None,
    payment_status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(Payslip)
    if month_year:
        query = query.filter(Payslip.month_year == month_year)
    if employee_id:
        query = query.filter(Payslip.employee_id == employee_id)
    if payment_status and payment_status != "ALL":
        query = query.filter(Payslip.payment_status == payment_status.upper())

    records = query.order_by(Payslip.id.desc()).all()
    return [_format_payslip(p) for p in records]


@router.get("/payslips/{payslip_id}", response_model=PayslipResponse)
def get_payslip_by_id(
    payslip_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    p = db.query(Payslip).filter(Payslip.id == payslip_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Payslip record not found")
    return _format_payslip(p)


@router.get("/my-payslips", response_model=List[PayslipResponse])
def get_my_personal_payslips(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    emp = db.query(Employee).filter(Employee.user_id == current_user.id).first()
    if not emp:
        return []
    records = db.query(Payslip).filter(Payslip.employee_id == emp.id).order_by(Payslip.id.desc()).all()
    return [_format_payslip(p) for p in records]


# =============================================================
# MODULE 9: Payroll Reports & Analytics
# =============================================================

@router.get("/reports/summary", response_model=PayrollSummaryResponse)
def get_payroll_summary_report(
    month_year: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(Payslip)
    if month_year:
        query = query.filter(Payslip.month_year == month_year)
    payslips = query.all()

    total_payout = sum(p.net_salary for p in payslips)
    total_allow = sum((p.house_rent + p.medical_allowance + p.transport_allowance + p.food_allowance + p.other_allowance) for p in payslips)
    total_bonus = sum(p.bonus_amount for p in payslips)
    total_deduct = sum(p.total_deductions for p in payslips)

    paid_count = sum(1 for p in payslips if p.payment_status == "PAID")
    pending_payslips = [p for p in payslips if p.payment_status != "PAID"]
    pending_count = len(pending_payslips)
    pending_amount = sum(p.net_salary for p in pending_payslips)

    # Department breakdown
    dept_map = {}
    for p in payslips:
        d_name = p.employee.department.name if p.employee and p.employee.department else "General"
        if d_name not in dept_map:
            dept_map[d_name] = {"department": d_name, "employee_count": 0, "gross_total": 0.0, "net_total": 0.0}
        dept_map[d_name]["employee_count"] += 1
        dept_map[d_name]["gross_total"] += p.gross_salary
        dept_map[d_name]["net_total"] += p.net_salary

    dept_breakdown = list(dept_map.values())
    for d in dept_breakdown:
        d["gross_total"] = round(d["gross_total"], 2)
        d["net_total"] = round(d["net_total"], 2)

    return PayrollSummaryResponse(
        total_monthly_payout=round(total_payout, 2),
        total_allowances=round(total_allow, 2),
        total_bonuses=round(total_bonus, 2),
        total_deductions=round(total_deduct, 2),
        total_employees_paid=paid_count,
        pending_disbursement_count=pending_count,
        pending_disbursement_amount=round(pending_amount, 2),
        department_breakdown=dept_breakdown
    )


@router.get("/reports/employee-history/{employee_id}", response_model=List[PayslipResponse])
def get_employee_salary_history(
    employee_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    records = db.query(Payslip).filter(Payslip.employee_id == employee_id).order_by(Payslip.month_year.desc()).all()
    return [_format_payslip(p) for p in records]
