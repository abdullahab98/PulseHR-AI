from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime
import uuid

from app.database import get_db
from app.models import ITSupportTicket, Employee, TicketStatus, UserRole
from app.schemas import ITTicketResponse
from app.security import get_current_user

router = APIRouter(prefix="/it-support", tags=["IT Support Panel"])

class ITTicketCreate(BaseModel):
    title: str
    description: Optional[str] = None
    priority: Optional[str] = "MEDIUM"
    assigned_to_id: Optional[int] = None

class ITTicketStatusUpdate(BaseModel):
    status: TicketStatus

@router.get("/tickets", response_model=List[ITTicketResponse])
def get_it_tickets(db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    tickets = db.query(ITSupportTicket).all()
    res = []
    for t in tickets:
        emp = db.query(Employee).filter(Employee.id == t.employee_id).first() if t.employee_id else None
        assignee = db.query(Employee).filter(Employee.id == t.assigned_to_id).first() if t.assigned_to_id else None
        res.append(ITTicketResponse(
            id=t.id,
            ticket_code=t.ticket_code,
            title=t.title,
            description=t.description or "",
            employee_id=t.employee_id,
            employee_name=f"{emp.first_name} {emp.last_name}" if emp else "Staff",
            assigned_to_id=t.assigned_to_id,
            assigned_to_name=f"{assignee.first_name} {assignee.last_name}" if assignee else "IT Desk",
            priority=t.priority or "MEDIUM",
            status=t.status or TicketStatus.OPEN,
            created_at=t.created_at or datetime.utcnow()
        ))
    return res

@router.post("/tickets", response_model=ITTicketResponse)
def create_it_ticket(t_in: ITTicketCreate, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    emp = db.query(Employee).filter(Employee.user_id == current_user.id).first()
    employee_id = emp.id if emp else 1
    ticket_code = f"IT-{uuid.uuid4().hex[:6].upper()}"

    t = ITSupportTicket(
        ticket_code=ticket_code,
        title=t_in.title,
        description=t_in.description,
        employee_id=employee_id,
        assigned_to_id=t_in.assigned_to_id,
        priority=t_in.priority,
        status=TicketStatus.OPEN
    )
    db.add(t)
    db.commit()
    db.refresh(t)

    assignee = db.query(Employee).filter(Employee.id == t.assigned_to_id).first() if t.assigned_to_id else None
    return ITTicketResponse(
        id=t.id,
        ticket_code=t.ticket_code,
        title=t.title,
        description=t.description or "",
        employee_id=t.employee_id,
        employee_name=f"{emp.first_name} {emp.last_name}" if emp else "Staff",
        assigned_to_id=t.assigned_to_id,
        assigned_to_name=f"{assignee.first_name} {assignee.last_name}" if assignee else "IT Desk",
        priority=t.priority,
        status=t.status,
        created_at=t.created_at or datetime.utcnow()
    )

@router.put("/tickets/{ticket_id}/status", response_model=ITTicketResponse)
def update_ticket_status(ticket_id: int, update: ITTicketStatusUpdate, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    t = db.query(ITSupportTicket).filter(ITSupportTicket.id == ticket_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="Ticket not found")

    t.status = update.status
    db.commit()
    db.refresh(t)

    emp = db.query(Employee).filter(Employee.id == t.employee_id).first() if t.employee_id else None
    assignee = db.query(Employee).filter(Employee.id == t.assigned_to_id).first() if t.assigned_to_id else None

    return ITTicketResponse(
        id=t.id,
        ticket_code=t.ticket_code,
        title=t.title,
        description=t.description or "",
        employee_id=t.employee_id,
        employee_name=f"{emp.first_name} {emp.last_name}" if emp else "Staff",
        assigned_to_id=t.assigned_to_id,
        assigned_to_name=f"{assignee.first_name} {assignee.last_name}" if assignee else "IT Desk",
        priority=t.priority,
        status=t.status,
        created_at=t.created_at or datetime.utcnow()
    )
