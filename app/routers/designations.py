from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Designation, Office, Rank, User, UserRole, Employee
from app.schemas import DesignationCreate, DesignationUpdate, DesignationResponse
from app.security import get_current_user, RoleChecker

router = APIRouter(prefix="/designations", tags=["Designation & RBAC Management"])

ALLOWED_ROLES = [UserRole.SUPER_ADMIN, UserRole.DEPARTMENT_HEAD, UserRole.MANAGER]

SYSTEM_PANELS = [
    # 1. Executive & Strategy
    {"id": "dashboard", "name": "Dashboard", "category": "Executive & Strategy", "icon": "🏠"},
    {"id": "reports", "name": "AI Analytics & Reports", "category": "Executive & Strategy", "icon": "📊"},

    # 2. HR Management
    {"id": "offices", "name": "Office", "category": "HR Management", "icon": "🏢"},
    {"id": "ranks", "name": "Rank", "category": "HR Management", "icon": "⭐"},
    {"id": "designations", "name": "Designation", "category": "HR Management", "icon": "🎖️"},
    {"id": "employees", "name": "Employees", "category": "HR Management", "icon": "👥"},
    {"id": "create_employee", "name": "Create Employee", "category": "HR Management", "icon": "➕"},
    {"id": "employee_organogram", "name": "Employee Organogram", "category": "HR Management", "icon": "🌳"},

    # 3. Attendance Management
    {"id": "attendance", "name": "Attendance Application List", "category": "Attendance Management", "icon": "📋"},
    {"id": "attendance_report", "name": "Attendance Report", "category": "Attendance Management", "icon": "📊"},
    {"id": "attendance_time_slots", "name": "Attendance Time Slot", "category": "Attendance Management", "icon": "🕒"},
    {"id": "attendance_apply_slot", "name": "Apply for New Time Slot", "category": "Attendance Management", "icon": "📝"},
    {"id": "attendance_weekend_setup", "name": "Weekend Setup", "category": "Attendance Management", "icon": "🗓️"},

    # 4. Leave Management
    {"id": "leaves", "name": "Leave", "category": "Leave Management", "icon": "🏖️"},
    {"id": "leave_applications", "name": "Leave Application", "category": "Leave Management", "icon": "⚖️"},
    {"id": "leave_employee_report", "name": "Employee Leave Report", "category": "Leave Management", "icon": "📑"},
    {"id": "leave_designation_chain", "name": "Designation Chain", "category": "Leave Management", "icon": "🔗"},
    {"id": "leave_types", "name": "Leave Type", "category": "Leave Management", "icon": "🏷️"},

    # 5. Engineering & QA
    {"id": "projects", "name": "Projects & Milestones", "category": "Engineering & QA", "icon": "📋"},
    {"id": "tasks", "name": "Tasks & Sprint Board", "category": "Engineering & QA", "icon": "💻"},
    {"id": "qa", "name": "QA & Bug Tracking", "category": "Engineering & QA", "icon": "🧪"},

    # 6. Enterprise Ops
    {"id": "finance", "name": "Finance & Expenses", "category": "Enterprise Ops", "icon": "💰"},
    {"id": "it_support", "name": "IT Support Desk", "category": "Enterprise Ops", "icon": "🛠️"},
    {"id": "inventory", "name": "Inventory & Assets", "category": "Enterprise Ops", "icon": "📦"},

    # 7. Payroll Management
    {"id": "payroll", "name": "Payroll Overview", "category": "Payroll Management", "icon": "📊"},
    {"id": "payroll_structure", "name": "Salary Structure", "category": "Payroll Management", "icon": "💼"},
    {"id": "payroll_attendance", "name": "Attendance Integration", "category": "Payroll Management", "icon": "⏱️"},
    {"id": "payroll_allowances", "name": "Allowances & Bonuses", "category": "Payroll Management", "icon": "🎁"},
    {"id": "payroll_deductions", "name": "Deduction Rules", "category": "Payroll Management", "icon": "✂️"},
    {"id": "payroll_processing", "name": "Monthly Processing", "category": "Payroll Management", "icon": "⚙️"},
    {"id": "payroll_disbursement", "name": "Salary Disbursement", "category": "Payroll Management", "icon": "💳"},
    {"id": "payroll_payslips", "name": "Payslip Management", "category": "Payroll Management", "icon": "📄"},
    {"id": "payroll_reports", "name": "Payroll Reports", "category": "Payroll Management", "icon": "📈"},

    # 8. Collaboration & Sales
    {"id": "meetings", "name": "Meetings & AI Summaries", "category": "Collaboration & Sales", "icon": "📅"},
    {"id": "documents", "name": "Document Repository", "category": "Collaboration & Sales", "icon": "📄"},
    {"id": "sales", "name": "Sales & CRM Leads", "category": "Collaboration & Sales", "icon": "📢"},

    # 9. AI Health & Burnout
    {"id": "burnout", "name": "Burnout Radar", "category": "AI Health & Burnout", "icon": "🔥"},

    # 10. Governance
    {"id": "permissions", "name": "Permission Control", "category": "Governance", "icon": "🔐"},
    {"id": "audit_logs", "name": "Audit & Compliance", "category": "Governance", "icon": "🛡️"}
]

def _format_designation(d: Designation) -> dict:
    emp_count = len(d.employees) if d.employees else 0
    return {
        "id": d.id,
        "name": d.name,
        "office_id": d.office_id,
        "office_name": d.office.name if d.office else None,
        "rank_id": d.rank_id,
        "rank_name": d.rank.name if d.rank else None,
        "description": d.description,
        "permissions": d.permissions or {},
        "created_at": d.created_at,
        "employees_count": emp_count
    }

@router.get("/meta/panels")
def get_system_panels(current_user: User = Depends(get_current_user)):
    """Returns all system panels and their categories for permission matrix generation."""
    return SYSTEM_PANELS

@router.get("/", response_model=List[DesignationResponse])
def list_designations(
    office_id: Optional[int] = Query(None),
    rank_id: Optional[int] = Query(None),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(Designation)
    if office_id:
        query = query.filter(Designation.office_id == office_id)
    if rank_id:
        query = query.filter(Designation.rank_id == rank_id)
    if search:
        query = query.filter(Designation.name.ilike(f"%{search}%"))

    designations = query.order_by(Designation.name).all()
    return [_format_designation(d) for d in designations]

@router.get("/{designation_id}", response_model=DesignationResponse)
def get_designation(
    designation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    d = db.query(Designation).filter(Designation.id == designation_id).first()
    if not d:
        raise HTTPException(status_code=404, detail="Designation not found")
    return _format_designation(d)

@router.post("/", response_model=DesignationResponse)
def create_designation(
    desig_in: DesignationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(RoleChecker(ALLOWED_ROLES))
):
    # Validate Office if provided
    if desig_in.office_id:
        office = db.query(Office).filter(Office.id == desig_in.office_id).first()
        if not office:
            raise HTTPException(status_code=400, detail="Specified Office does not exist")

    # Validate Rank if provided
    if desig_in.rank_id:
        rank = db.query(Rank).filter(Rank.id == desig_in.rank_id).first()
        if not rank:
            raise HTTPException(status_code=400, detail="Specified Rank does not exist")

    # Check for duplicate designation with same name, office, and rank
    existing = db.query(Designation).filter(
        Designation.name == desig_in.name,
        Designation.office_id == desig_in.office_id,
        Designation.rank_id == desig_in.rank_id
    ).first()
    if existing:
        raise HTTPException(
            status_code=400,
            detail="A designation with this name, office, and rank combination already exists"
        )

    desig = Designation(
        name=desig_in.name,
        office_id=desig_in.office_id,
        rank_id=desig_in.rank_id,
        description=desig_in.description,
        permissions=desig_in.permissions or {}
    )
    db.add(desig)
    db.commit()
    db.refresh(desig)
    return _format_designation(desig)

@router.put("/{designation_id}", response_model=DesignationResponse)
def update_designation(
    designation_id: int,
    desig_in: DesignationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(RoleChecker(ALLOWED_ROLES))
):
    desig = db.query(Designation).filter(Designation.id == designation_id).first()
    if not desig:
        raise HTTPException(status_code=404, detail="Designation not found")

    if desig_in.office_id is not None:
        if desig_in.office_id > 0:
            office = db.query(Office).filter(Office.id == desig_in.office_id).first()
            if not office:
                raise HTTPException(status_code=400, detail="Specified Office does not exist")
            desig.office_id = desig_in.office_id
        else:
            desig.office_id = None

    if desig_in.rank_id is not None:
        if desig_in.rank_id > 0:
            rank = db.query(Rank).filter(Rank.id == desig_in.rank_id).first()
            if not rank:
                raise HTTPException(status_code=400, detail="Specified Rank does not exist")
            desig.rank_id = desig_in.rank_id
        else:
            desig.rank_id = None

    if desig_in.name is not None and desig_in.name.strip():
        desig.name = desig_in.name.strip()
        db.query(Employee).filter(Employee.designation_id == designation_id).update({Employee.designation: desig.name})
    if desig_in.description is not None:
        desig.description = desig_in.description
    if desig_in.permissions is not None:
        desig.permissions = desig_in.permissions

    db.commit()
    db.refresh(desig)
    return _format_designation(desig)

@router.delete("/{designation_id}")
def delete_designation(
    designation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(RoleChecker(ALLOWED_ROLES))
):
    desig = db.query(Designation).filter(Designation.id == designation_id).first()
    if not desig:
        raise HTTPException(status_code=404, detail="Designation not found")

    # Detach from employees if linked
    db.query(Employee).filter(Employee.designation_id == designation_id).update({Employee.designation_id: None})

    db.delete(desig)
    db.commit()
    return {"message": "Designation deleted successfully"}
