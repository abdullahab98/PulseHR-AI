from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from datetime import date

from app.database import get_db
from app.models import FinanceRecord, Department, Employee, UserRole
from app.schemas import FinanceRecordResponse
from app.security import get_current_user, RoleChecker

router = APIRouter(prefix="/finance", tags=["Finance & Accounts Panel"])

class FinanceRecordCreate(BaseModel):
    title: str
    record_type: str  # INCOME / EXPENSE
    amount: float
    department_id: Optional[int] = None
    employee_id: Optional[int] = None
    notes: Optional[str] = None

@router.get("/records", response_model=List[FinanceRecordResponse])
def get_finance_records(db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    records = db.query(FinanceRecord).all()
    res = []
    for r in records:
        dept = db.query(Department).filter(Department.id == r.department_id).first() if r.department_id else None
        emp = db.query(Employee).filter(Employee.id == r.employee_id).first() if r.employee_id else None
        res.append(FinanceRecordResponse(
            id=r.id,
            title=r.title,
            record_type=r.record_type,
            amount=r.amount,
            department_id=r.department_id,
            department_name=dept.name if dept else "General Company",
            employee_id=r.employee_id,
            employee_name=f"{emp.first_name} {emp.last_name}" if emp else None,
            date=r.date or date.today(),
            notes=r.notes
        ))
    return res

@router.post("/records", response_model=FinanceRecordResponse)
def create_finance_record(
    rec_in: FinanceRecordCreate,
    db: Session = Depends(get_db),
    current_user = Depends(RoleChecker([UserRole.SUPER_ADMIN, UserRole.DEPARTMENT_HEAD, UserRole.MANAGER, UserRole.SPECIAL_USER]))
):
    rec = FinanceRecord(
        title=rec_in.title,
        record_type=rec_in.record_type.upper(),
        amount=rec_in.amount,
        department_id=rec_in.department_id,
        employee_id=rec_in.employee_id,
        date=date.today(),
        notes=rec_in.notes
    )
    db.add(rec)
    db.commit()
    db.refresh(rec)

    dept = db.query(Department).filter(Department.id == rec.department_id).first() if rec.department_id else None
    emp = db.query(Employee).filter(Employee.id == rec.employee_id).first() if rec.employee_id else None

    return FinanceRecordResponse(
        id=rec.id,
        title=rec.title,
        record_type=rec.record_type,
        amount=rec.amount,
        department_id=rec.department_id,
        department_name=dept.name if dept else "General Company",
        employee_id=rec.employee_id,
        employee_name=f"{emp.first_name} {emp.last_name}" if emp else None,
        date=rec.date,
        notes=rec.notes
    )
