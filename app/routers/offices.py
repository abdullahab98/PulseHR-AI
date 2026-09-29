from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Office, User, UserRole
from app.schemas import OfficeCreate, OfficeUpdate, OfficeResponse
from app.security import get_current_user, RoleChecker

router = APIRouter(prefix="/offices", tags=["Office Management"])

ALLOWED_ROLES = [UserRole.SUPER_ADMIN, UserRole.DEPARTMENT_HEAD, UserRole.MANAGER]

@router.get("/", response_model=List[OfficeResponse])
def list_offices(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return db.query(Office).order_by(Office.name).all()

@router.get("/{office_id}", response_model=OfficeResponse)
def get_office(
    office_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    office = db.query(Office).filter(Office.id == office_id).first()
    if not office:
        raise HTTPException(status_code=404, detail="Office not found")
    return office

@router.post("/", response_model=OfficeResponse)
def create_office(
    office_in: OfficeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(RoleChecker(ALLOWED_ROLES))
):
    existing = db.query(Office).filter(Office.name == office_in.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Office with this name already exists")

    office = Office(
        name=office_in.name,
        establishment=office_in.establishment,
        description=office_in.description,
        mission=office_in.mission,
        vision=office_in.vision
    )
    db.add(office)
    db.commit()
    db.refresh(office)
    return office

@router.put("/{office_id}", response_model=OfficeResponse)
def update_office(
    office_id: int,
    office_in: OfficeUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(RoleChecker(ALLOWED_ROLES))
):
    office = db.query(Office).filter(Office.id == office_id).first()
    if not office:
        raise HTTPException(status_code=404, detail="Office not found")

    if office_in.name is not None:
        office.name = office_in.name
    if office_in.establishment is not None:
        office.establishment = office_in.establishment
    if office_in.description is not None:
        office.description = office_in.description
    if office_in.mission is not None:
        office.mission = office_in.mission
    if office_in.vision is not None:
        office.vision = office_in.vision

    db.commit()
    db.refresh(office)
    return office

@router.delete("/{office_id}")
def delete_office(
    office_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(RoleChecker(ALLOWED_ROLES))
):
    office = db.query(Office).filter(Office.id == office_id).first()
    if not office:
        raise HTTPException(status_code=404, detail="Office not found")
    db.delete(office)
    db.commit()
    return {"message": "Office deleted successfully"}
