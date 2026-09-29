from typing import List, Optional
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Employee, User, UserRole, Department, Designation
from app.schemas import EmployeeCreate, EmployeeUpdate, EmployeeResponse, ChangePasswordRequest
from app.security import get_current_user, RoleChecker, verify_password, get_password_hash

router = APIRouter(prefix="/employees", tags=["Employee Management"])

def _format_employee_response(emp: Employee) -> EmployeeResponse:
    dept_name = emp.department.name if emp.department else None
    office_name = emp.office.name if emp.office else None
    rank_name = emp.rank.name if emp.rank else None
    desig_name = emp.designation_rel.name if emp.designation_rel else emp.designation
    return EmployeeResponse(
        id=emp.id,
        user_id=emp.user_id,
        employee_code=emp.employee_code,
        first_name=emp.first_name,
        last_name=emp.last_name,
        email=emp.user.email if emp.user else None,
        role=emp.user.role if emp.user else None,
        department_id=emp.department_id,
        department_name=dept_name,
        office_id=emp.office_id,
        office_name=office_name,
        rank_id=emp.rank_id,
        rank_name=rank_name,
        designation_id=emp.designation_id,
        designation_name=desig_name,
        designation=desig_name or emp.designation or "Employee",
        salary=emp.salary,
        phone=emp.phone,
        personal_email=emp.personal_email,
        address_info=emp.address_info or {},
        family_info=emp.family_info or {},
        bio=emp.bio,
        skills=emp.skills or [],
        emergency_contact=emp.emergency_contact or {},
        documents=emp.documents or [],
        hire_date=emp.hire_date
    )

@router.get("/me/profile", response_model=EmployeeResponse)
def get_my_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    emp = db.query(Employee).filter(Employee.user_id == current_user.id).first()
    if not emp:
        emp = Employee(
            user_id=current_user.id,
            employee_code=f"EMP-{current_user.id:03d}",
            first_name="User",
            last_name=str(current_user.id),
            designation="Employee",
            hire_date=date.today()
        )
        db.add(emp)
        db.commit()
        db.refresh(emp)
    return _format_employee_response(emp)

@router.put("/me/profile", response_model=EmployeeResponse)
def update_my_profile(
    profile_in: EmployeeUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    emp = db.query(Employee).filter(Employee.user_id == current_user.id).first()
    if not emp:
        raise HTTPException(status_code=404, detail="Employee profile not found")

    if profile_in.first_name is not None:
        emp.first_name = profile_in.first_name
    if profile_in.last_name is not None:
        emp.last_name = profile_in.last_name
    if profile_in.phone is not None:
        emp.phone = profile_in.phone
    if profile_in.personal_email is not None:
        emp.personal_email = profile_in.personal_email
    if profile_in.address_info is not None:
        emp.address_info = profile_in.address_info
    if profile_in.family_info is not None:
        emp.family_info = profile_in.family_info
    if profile_in.bio is not None:
        emp.bio = profile_in.bio
    if profile_in.skills is not None:
        emp.skills = profile_in.skills
    if profile_in.emergency_contact is not None:
        emp.emergency_contact = profile_in.emergency_contact

    db.commit()
    db.refresh(emp)
    return _format_employee_response(emp)

@router.post("/me/change-password")
def change_my_password(
    req: ChangePasswordRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not verify_password(req.current_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Current password does not match")
    if len(req.new_password) < 6:
        raise HTTPException(status_code=400, detail="New password must be at least 6 characters")
    
    current_user.hashed_password = get_password_hash(req.new_password)
    db.commit()
    return {"message": "Password changed successfully"}

@router.get("/", response_model=List[EmployeeResponse])
def list_employees(
    department_id: Optional[int] = None,
    q: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(Employee)
    if department_id:
        query = query.filter(Employee.department_id == department_id)
    
    term = q or search
    if term and term.strip():
        search_pattern = f"%{term.strip()}%"
        query = query.filter(
            (Employee.first_name.ilike(search_pattern)) |
            (Employee.last_name.ilike(search_pattern)) |
            ((Employee.first_name + " " + Employee.last_name).ilike(search_pattern)) |
            (Employee.employee_code.ilike(search_pattern)) |
            (Employee.designation.ilike(search_pattern))
        )
    
    employees = query.all()
    return [_format_employee_response(emp) for emp in employees]

@router.get("/{employee_id}", response_model=EmployeeResponse)
def get_employee(
    employee_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    emp = db.query(Employee).filter(Employee.id == employee_id).first()
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")
    return _format_employee_response(emp)

@router.post("/", response_model=EmployeeResponse)
def create_employee(
    emp_in: EmployeeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(RoleChecker([UserRole.SUPER_ADMIN, UserRole.DEPARTMENT_HEAD, UserRole.MANAGER]))
):
    existing = db.query(Employee).filter(Employee.employee_code == emp_in.employee_code).first()
    if existing:
        raise HTTPException(status_code=400, detail="Employee code already exists")

    emp = Employee(
        user_id=emp_in.user_id or current_user.id,
        employee_code=emp_in.employee_code,
        first_name=emp_in.first_name,
        last_name=emp_in.last_name,
        department_id=emp_in.department_id,
        office_id=emp_in.office_id,
        rank_id=emp_in.rank_id,
        designation_id=emp_in.designation_id,
        designation=emp_in.designation or "Employee",
        salary=emp_in.salary,
        phone=emp_in.phone,
        personal_email=emp_in.personal_email,
        address_info=emp_in.address_info or {},
        family_info=emp_in.family_info or {},
        bio=emp_in.bio,
        skills=emp_in.skills,
        emergency_contact=emp_in.emergency_contact,
        documents=emp_in.documents,
        hire_date=emp_in.hire_date or date.today()
    )
    db.add(emp)
    db.commit()
    db.refresh(emp)
    return _format_employee_response(emp)

@router.put("/{employee_id}", response_model=EmployeeResponse)
def update_employee(
    employee_id: int,
    emp_update: EmployeeUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    emp = db.query(Employee).filter(Employee.id == employee_id).first()
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")

    is_admin = current_user.role in [UserRole.SUPER_ADMIN, UserRole.DEPARTMENT_HEAD, UserRole.MANAGER]
    is_self = (emp.user_id == current_user.id)
    if not (is_admin or is_self):
        raise HTTPException(status_code=403, detail="Not authorized to edit this employee")

    if emp_update.first_name is not None:
        emp.first_name = emp_update.first_name
    if emp_update.last_name is not None:
        emp.last_name = emp_update.last_name
    if emp_update.phone is not None:
        emp.phone = emp_update.phone
    if emp_update.personal_email is not None:
        emp.personal_email = emp_update.personal_email
    if emp_update.address_info is not None:
        emp.address_info = emp_update.address_info
    if emp_update.family_info is not None:
        emp.family_info = emp_update.family_info
    if emp_update.bio is not None:
        emp.bio = emp_update.bio
    if emp_update.skills is not None:
        emp.skills = emp_update.skills
    if emp_update.emergency_contact is not None:
        emp.emergency_contact = emp_update.emergency_contact

    if is_admin:
        if emp_update.department_id is not None:
            emp.department_id = emp_update.department_id
        if emp_update.office_id is not None:
            emp.office_id = emp_update.office_id
        if emp_update.rank_id is not None:
            emp.rank_id = emp_update.rank_id
        if emp_update.designation_id is not None:
            if emp_update.designation_id > 0:
                emp.designation_id = emp_update.designation_id
                desig_obj = db.query(Designation).filter(Designation.id == emp_update.designation_id).first()
                if desig_obj:
                    emp.designation = desig_obj.name
                    if desig_obj.office_id and not emp.office_id:
                        emp.office_id = desig_obj.office_id
                    if desig_obj.rank_id and not emp.rank_id:
                        emp.rank_id = desig_obj.rank_id
            else:
                emp.designation_id = None
                emp.designation = "Unassigned"
        elif emp_update.designation is not None:
            emp.designation = emp_update.designation
        if emp_update.salary is not None:
            emp.salary = emp_update.salary

    db.commit()
    db.refresh(emp)
    return _format_employee_response(emp)

class DesignationAssignmentPayload(BaseModel):
    designation_id: int

@router.put("/{employee_id}/designation", response_model=EmployeeResponse)
def assign_employee_designation(
    employee_id: int,
    payload: DesignationAssignmentPayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(RoleChecker([UserRole.SUPER_ADMIN, UserRole.DEPARTMENT_HEAD, UserRole.MANAGER]))
):
    """Allows Super Admin and HR to assign a designation to an employee directly from their profile."""
    emp = db.query(Employee).filter(Employee.id == employee_id).first()
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")

    desig = db.query(Designation).filter(Designation.id == payload.designation_id).first()
    if not desig:
        raise HTTPException(status_code=400, detail="Specified designation does not exist")

    emp.designation_id = desig.id
    emp.designation = desig.name
    if desig.office_id and not emp.office_id:
        emp.office_id = desig.office_id
    if desig.rank_id and not emp.rank_id:
        emp.rank_id = desig.rank_id

    db.commit()
    db.refresh(emp)
    return _format_employee_response(emp)

@router.delete("/{employee_id}/designation", response_model=EmployeeResponse)
def remove_employee_designation(
    employee_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(RoleChecker([UserRole.SUPER_ADMIN, UserRole.DEPARTMENT_HEAD, UserRole.MANAGER]))
):
    """Allows Super Admin and HR to delete/remove a designation from an employee profile."""
    emp = db.query(Employee).filter(Employee.id == employee_id).first()
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")

    emp.designation_id = None
    emp.designation = "Unassigned"
    db.commit()
    db.refresh(emp)
    return _format_employee_response(emp)

@router.delete("/{employee_id}")
def delete_employee(
    employee_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(RoleChecker([UserRole.SUPER_ADMIN, UserRole.DEPARTMENT_HEAD]))
):
    emp = db.query(Employee).filter(Employee.id == employee_id).first()
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    if emp.user:
        emp.user.is_active = False
    
    db.delete(emp)
    db.commit()
    return {"message": "Employee deleted successfully"}
