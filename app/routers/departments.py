from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Department, User, UserRole
from app.schemas import DepartmentCreate, DepartmentResponse
from app.security import get_current_user, RoleChecker

router = APIRouter(prefix="/departments", tags=["Department Management"])

@router.get("/", response_model=List[DepartmentResponse])
def list_departments(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(Department).all()

@router.post("/", response_model=DepartmentResponse)
def create_department(
    dept_in: DepartmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(RoleChecker([UserRole.SUPER_ADMIN, UserRole.DEPARTMENT_HEAD]))
):
    existing = db.query(Department).filter(
        (Department.name == dept_in.name) | (Department.code == dept_in.code)
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Department with this name or code already exists")

    dept = Department(
        name=dept_in.name,
        code=dept_in.code,
        budget=dept_in.budget
    )
    db.add(dept)
    db.commit()
    db.refresh(dept)
    return dept
