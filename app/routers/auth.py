from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.models import User, Employee, UserRole, Department, Designation
from app.schemas import Token, LoginRequest, RegisterRequest, UserResponse
from app.security import verify_password, get_password_hash, create_access_token, get_current_user

router = APIRouter(prefix="/auth", tags=["Authentication & Authorization"])

ALL_PANELS = [
    "EXECUTIVE", "HR", "PROJECTS", "DEVELOPMENT", "QA", 
    "DESIGN", "FINANCE", "IT_SUPPORT", "SALES", "INVENTORY", 
    "MEETINGS", "DOCUMENTS"
]

def get_default_panels_for_role(role: UserRole) -> List[str]:
    if role in [UserRole.SUPER_ADMIN]:
        return ALL_PANELS
    elif role in [UserRole.DEPARTMENT_HEAD]:
        return ["EXECUTIVE", "HR", "PROJECTS", "DEVELOPMENT", "QA", "DESIGN", "FINANCE", "IT_SUPPORT", "INVENTORY", "MEETINGS", "DOCUMENTS"]
    elif role in [UserRole.MANAGER]:
        return ["HR", "PROJECTS", "DEVELOPMENT", "QA", "DESIGN", "IT_SUPPORT", "INVENTORY", "MEETINGS", "DOCUMENTS"]
    elif role in [UserRole.TEAM_LEADER]:
        return ["PROJECTS", "DEVELOPMENT", "QA", "DESIGN", "IT_SUPPORT", "INVENTORY", "MEETINGS", "DOCUMENTS"]
    elif role in [UserRole.SPECIAL_USER]:
        return ["EXECUTIVE", "HR", "FINANCE", "DOCUMENTS"]  # Default Auditor/Consultant view
    else:  # EMPLOYEE
        return ["PROJECTS", "DEVELOPMENT", "IT_SUPPORT", "INVENTORY", "MEETINGS", "DOCUMENTS"]

@router.post("/login", response_model=Token)
def login(login_data: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == login_data.email).first()
    if not user or not verify_password(login_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Account is disabled")

    emp = db.query(Employee).filter(Employee.user_id == user.id).first()
    desig = None
    if emp and emp.designation_id:
        desig = db.query(Designation).filter(Designation.id == emp.designation_id).first()

    desig_permissions = desig.permissions if (desig and desig.permissions) else {}
    desig_name = desig.name if desig else (emp.designation if emp else None)
    
    # Compute effective allowed panels
    user_panels = list(user.allowed_panels) if (user.allowed_panels and len(user.allowed_panels) > 0) else get_default_panels_for_role(user.role)
    
    # If designation defines permissions, sync viewable panels
    if desig_permissions:
        for p_id, p_acts in desig_permissions.items():
            if isinstance(p_acts, dict) and p_acts.get("view"):
                upper_p = p_id.upper()
                if upper_p not in user_panels:
                    user_panels.append(upper_p)
                if p_id not in user_panels:
                    user_panels.append(p_id)

    user_scope = user.data_scope or ("ALL" if user.role == UserRole.SUPER_ADMIN else "DEPARTMENT" if user.role in [UserRole.DEPARTMENT_HEAD, UserRole.MANAGER] else "OWN")
    user_perms = user.custom_permissions or {}

    access_token = create_access_token(
        data={"sub": user.email, "username": user.email, "role": user.role.value, "user_id": user.id}
    )
    
    return Token(
        access_token=access_token,
        token_type="bearer",
        user_id=user.id,
        email=user.email,
        role=user.role,
        employee_id=emp.id if emp else None,
        first_name=emp.first_name if emp else "User",
        last_name=emp.last_name if emp else "",
        allowed_panels=user_panels,
        custom_permissions=user_perms,
        panel_permissions=desig_permissions,
        designation_name=desig_name,
        data_scope=user_scope
    )

@router.post("/register", response_model=UserResponse)
def register(reg_data: RegisterRequest, db: Session = Depends(get_db)):
    existing_user = db.query(User).filter(User.email == reg_data.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    existing_code = db.query(Employee).filter(Employee.employee_code == reg_data.employee_code).first()
    if existing_code:
        raise HTTPException(status_code=400, detail="Employee code already in use")

    default_panels = get_default_panels_for_role(reg_data.role)
    default_scope = "ALL" if reg_data.role == UserRole.SUPER_ADMIN else "OWN"

    # Create User
    new_user = User(
        email=reg_data.email,
        hashed_password=get_password_hash(reg_data.password),
        role=reg_data.role,
        allowed_panels=default_panels,
        custom_permissions={},
        data_scope=default_scope,
        is_active=True,
        is_verified=True
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # Create Employee Profile
    new_emp = Employee(
        user_id=new_user.id,
        employee_code=reg_data.employee_code,
        first_name=reg_data.first_name,
        last_name=reg_data.last_name,
        department_id=reg_data.department_id,
        designation=reg_data.designation,
        salary=reg_data.salary,
        skills=["Communication", "Office Operations"]
    )
    db.add(new_emp)
    db.commit()

    return new_user

@router.get("/me")
def get_me(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    emp = db.query(Employee).filter(Employee.user_id == current_user.id).first()
    dept_name = emp.department.name if emp and emp.department else None
    office_name = emp.office.name if emp and emp.office else None
    rank_name = emp.rank.name if emp and emp.rank else None
    desig = None
    if emp and emp.designation_id:
        desig = db.query(Designation).filter(Designation.id == emp.designation_id).first()
    
    desig_permissions = desig.permissions if (desig and desig.permissions) else {}
    desig_name = desig.name if desig else (emp.designation if emp else None)
    
    user_panels = list(current_user.allowed_panels) if (current_user.allowed_panels and len(current_user.allowed_panels) > 0) else get_default_panels_for_role(current_user.role)
    if desig_permissions:
        for p_id, p_acts in desig_permissions.items():
            if isinstance(p_acts, dict) and p_acts.get("view"):
                upper_p = p_id.upper()
                if upper_p not in user_panels:
                    user_panels.append(upper_p)
                if p_id not in user_panels:
                    user_panels.append(p_id)

    user_scope = current_user.data_scope or ("ALL" if current_user.role == UserRole.SUPER_ADMIN else "DEPARTMENT" if current_user.role in [UserRole.DEPARTMENT_HEAD, UserRole.MANAGER] else "OWN")

    return {
        "id": current_user.id,
        "username": current_user.email,
        "email": current_user.email,
        "role": current_user.role,
        "is_active": current_user.is_active,
        "allowed_panels": user_panels,
        "custom_permissions": current_user.custom_permissions or {},
        "panel_permissions": desig_permissions,
        "designation_name": desig_name,
        "data_scope": user_scope,
        "employee": {
            "id": emp.id if emp else None,
            "employee_code": emp.employee_code if emp else None,
            "first_name": emp.first_name if emp else "",
            "last_name": emp.last_name if emp else "",
            "designation": emp.designation if emp else "",
            "designation_id": emp.designation_id if emp else None,
            "designation_name": desig_name,
            "department_id": emp.department_id if emp else None,
            "department_name": dept_name,
            "office_id": emp.office_id if emp else None,
            "office_name": office_name,
            "rank_id": emp.rank_id if emp else None,
            "rank_name": rank_name,
            "skills": emp.skills if emp else []
        } if emp else None
    }
