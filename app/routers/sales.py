from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel

from app.database import get_db
from app.models import SalesLead, Employee, UserRole
from app.schemas import SalesLeadResponse
from app.security import get_current_user, RoleChecker

router = APIRouter(prefix="/sales", tags=["Sales & Marketing Panel"])

class SalesLeadCreate(BaseModel):
    client_name: str
    deal_title: str
    deal_value: float
    stage: Optional[str] = "NEW"
    assigned_to_id: Optional[int] = None

class SalesStageUpdate(BaseModel):
    stage: str

@router.get("/leads", response_model=List[SalesLeadResponse])
def get_sales_leads(db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    leads = db.query(SalesLead).all()
    res = []
    for l in leads:
        emp = db.query(Employee).filter(Employee.id == l.assigned_to_id).first() if l.assigned_to_id else None
        res.append(SalesLeadResponse(
            id=l.id,
            client_name=l.client_name,
            deal_title=l.deal_title,
            deal_value=l.deal_value,
            stage=l.stage or "NEW",
            assigned_to_id=l.assigned_to_id,
            assigned_to_name=f"{emp.first_name} {emp.last_name}" if emp else "Sales Team",
            created_at=l.created_at
        ))
    return res

@router.post("/leads", response_model=SalesLeadResponse)
def create_sales_lead(lead_in: SalesLeadCreate, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    lead = SalesLead(
        client_name=lead_in.client_name,
        deal_title=lead_in.deal_title,
        deal_value=lead_in.deal_value,
        stage=lead_in.stage,
        assigned_to_id=lead_in.assigned_to_id
    )
    db.add(lead)
    db.commit()
    db.refresh(lead)

    emp = db.query(Employee).filter(Employee.id == lead.assigned_to_id).first() if lead.assigned_to_id else None
    return SalesLeadResponse(
        id=lead.id,
        client_name=lead.client_name,
        deal_title=lead.deal_title,
        deal_value=lead.deal_value,
        stage=lead.stage,
        assigned_to_id=lead.assigned_to_id,
        assigned_to_name=f"{emp.first_name} {emp.last_name}" if emp else "Sales Team",
        created_at=lead.created_at
    )

@router.put("/leads/{lead_id}/stage", response_model=SalesLeadResponse)
def update_sales_stage(lead_id: int, update: SalesStageUpdate, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    lead = db.query(SalesLead).filter(SalesLead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Sales lead not found")

    lead.stage = update.stage
    db.commit()
    db.refresh(lead)

    emp = db.query(Employee).filter(Employee.id == lead.assigned_to_id).first() if lead.assigned_to_id else None
    return SalesLeadResponse(
        id=lead.id,
        client_name=lead.client_name,
        deal_title=lead.deal_title,
        deal_value=lead.deal_value,
        stage=lead.stage,
        assigned_to_id=lead.assigned_to_id,
        assigned_to_name=f"{emp.first_name} {emp.last_name}" if emp else "Sales Team",
        created_at=lead.created_at
    )
