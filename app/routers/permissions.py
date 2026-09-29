from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel

from app.database import get_db
from app.models import User, Employee, UserRole
from app.schemas import UserPermissionUpdate, UserResponse
from app.security import get_current_user, RoleChecker

router = APIRouter(prefix="/permissions", tags=["Super Admin Permission Control"])

ALL_AVAILABLE_PANELS = [
    {"id": "EXECUTIVE", "name": "Executive Management", "icon": "🏠"},
    {"id": "HR", "name": "HR & Administration", "icon": "👥"},
    {"id": "PROJECTS", "name": "Project Management", "icon": "📋"},
    {"id": "DEVELOPMENT", "name": "Software Development", "icon": "💻"},
    {"id": "QA", "name": "QA & Testing", "icon": "🧪"},
    {"id": "DESIGN", "name": "UI/UX Design", "icon": "🎨"},
    {"id": "FINANCE", "name": "Finance & Accounts", "icon": "💰"},
    {"id": "PAYROLL", "name": "Payroll Management", "icon": "💵"},
    {"id": "IT_SUPPORT", "name": "IT Support", "icon": "🛠️"},
    {"id": "SALES", "name": "Sales & Marketing", "icon": "📢"},
    {"id": "INVENTORY", "name": "Inventory & Assets", "icon": "📦"},
    {"id": "MEETINGS", "name": "Meetings & Communication", "icon": "📅"},
    {"id": "DOCUMENTS", "name": "Document Management", "icon": "📄"},
    {"id": "BURNOUT", "name": "Burnout Radar & AI Health", "icon": "🔥"}
]

@router.get("/panels")
def get_available_panels(current_user: User = Depends(get_current_user)):
    return ALL_AVAILABLE_PANELS

@router.get("/users")
def get_all_users_permissions(
    db: Session = Depends(get_db),
    current_user: User = Depends(RoleChecker([UserRole.SUPER_ADMIN, UserRole.DEPARTMENT_HEAD]))
):
    users = db.query(User).all()
    res = []
    for u in users:
        emp = db.query(Employee).filter(Employee.user_id == u.id).first()
        res.append({
            "id": u.id,
            "user_id": u.id,
            "username": u.email,
            "email": u.email,
            "role": u.role,
            "is_active": u.is_active,
            "employee_name": f"{emp.first_name} {emp.last_name}" if emp else "System Admin",
            "department": emp.department.name if emp and emp.department else "N/A",
            "allowed_panels": u.allowed_panels or [],
            "custom_permissions": u.custom_permissions or {},
            "data_scope": u.data_scope or "DEPARTMENT"
        })
    return res

@router.put("/users/{user_id}")
def update_user_permissions(
    user_id: int,
    perm_in: UserPermissionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(RoleChecker([UserRole.SUPER_ADMIN]))
):
    u = db.query(User).filter(User.id == user_id).first()
    if not u:
        raise HTTPException(status_code=404, detail="User not found")

    if perm_in.allowed_panels is not None:
        u.allowed_panels = perm_in.allowed_panels
    if perm_in.custom_permissions is not None:
        u.custom_permissions = perm_in.custom_permissions
    if perm_in.data_scope is not None:
        u.data_scope = perm_in.data_scope

    db.commit()
    db.refresh(u)
    return {"message": "Permissions updated successfully", "user_id": u.id}
