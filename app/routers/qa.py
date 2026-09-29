from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel

from app.database import get_db
from app.models import QABugReport, Project, Employee, BugStatus, UserRole
from app.schemas import QABugResponse
from app.security import get_current_user, RoleChecker

router = APIRouter(prefix="/qa", tags=["QA & Testing Panel"])

class BugCreate(BaseModel):
    project_id: int
    title: str
    description: Optional[str] = None
    severity: Optional[str] = "MEDIUM"
    assignee_id: Optional[int] = None

class BugStatusUpdate(BaseModel):
    status: BugStatus

@router.get("/bugs", response_model=List[QABugResponse])
def get_bugs(db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    bugs = db.query(QABugReport).all()
    res = []
    for b in bugs:
        proj = db.query(Project).filter(Project.id == b.project_id).first()
        rep = db.query(Employee).filter(Employee.id == b.reporter_id).first() if b.reporter_id else None
        assignee = db.query(Employee).filter(Employee.id == b.assignee_id).first() if b.assignee_id else None
        res.append(QABugResponse(
            id=b.id,
            project_id=b.project_id,
            project_title=proj.title if proj else "N/A",
            title=b.title,
            description=b.description or "",
            severity=b.severity or "MEDIUM",
            status=b.status or BugStatus.OPEN,
            reporter_id=b.reporter_id,
            reporter_name=f"{rep.first_name} {rep.last_name}" if rep else "QA Staff",
            assignee_id=b.assignee_id,
            assignee_name=f"{assignee.first_name} {assignee.last_name}" if assignee else "Unassigned",
            created_at=b.created_at
        ))
    return res

@router.post("/bugs", response_model=QABugResponse)
def create_bug(bug_in: BugCreate, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    emp = db.query(Employee).filter(Employee.user_id == current_user.id).first()
    reporter_id = emp.id if emp else None
    
    bug = QABugReport(
        project_id=bug_in.project_id,
        title=bug_in.title,
        description=bug_in.description,
        severity=bug_in.severity,
        status=BugStatus.OPEN,
        reporter_id=reporter_id,
        assignee_id=bug_in.assignee_id
    )
    db.add(bug)
    db.commit()
    db.refresh(bug)
    
    proj = db.query(Project).filter(Project.id == bug.project_id).first()
    assignee = db.query(Employee).filter(Employee.id == bug.assignee_id).first() if bug.assignee_id else None
    
    return QABugResponse(
        id=bug.id,
        project_id=bug.project_id,
        project_title=proj.title if proj else "N/A",
        title=bug.title,
        description=bug.description or "",
        severity=bug.severity or "MEDIUM",
        status=bug.status,
        reporter_id=bug.reporter_id,
        reporter_name=f"{emp.first_name} {emp.last_name}" if emp else "QA Staff",
        assignee_id=bug.assignee_id,
        assignee_name=f"{assignee.first_name} {assignee.last_name}" if assignee else "Unassigned",
        created_at=bug.created_at
    )

@router.put("/bugs/{bug_id}/status", response_model=QABugResponse)
def update_bug_status(bug_id: int, update: BugStatusUpdate, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    bug = db.query(QABugReport).filter(QABugReport.id == bug_id).first()
    if not bug:
        raise HTTPException(status_code=404, detail="Bug report not found")
    
    bug.status = update.status
    db.commit()
    db.refresh(bug)
    
    proj = db.query(Project).filter(Project.id == bug.project_id).first()
    rep = db.query(Employee).filter(Employee.id == bug.reporter_id).first() if bug.reporter_id else None
    assignee = db.query(Employee).filter(Employee.id == bug.assignee_id).first() if bug.assignee_id else None
    
    return QABugResponse(
        id=bug.id,
        project_id=bug.project_id,
        project_title=proj.title if proj else "N/A",
        title=bug.title,
        description=bug.description or "",
        severity=bug.severity or "MEDIUM",
        status=bug.status,
        reporter_id=bug.reporter_id,
        reporter_name=f"{rep.first_name} {rep.last_name}" if rep else "QA Staff",
        assignee_id=bug.assignee_id,
        assignee_name=f"{assignee.first_name} {assignee.last_name}" if assignee else "Unassigned",
        created_at=bug.created_at
    )
