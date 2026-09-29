from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Project, ProjectStatus, User, UserRole, Task, TaskStatus
from app.schemas import ProjectCreate, ProjectUpdate, ProjectResponse
from app.security import get_current_user, RoleChecker

router = APIRouter(prefix="/projects", tags=["Project Management"])

def _format_project(proj: Project, db: Session) -> ProjectResponse:
    dept_name = proj.department.name if proj.department else "General"
    pm_name = f"{proj.project_manager.first_name} {proj.project_manager.last_name}" if proj.project_manager else "Unassigned"
    
    tasks = db.query(Task).filter(Task.project_id == proj.id).all()
    task_count = len(tasks)
    completed_task_count = sum(1 for t in tasks if t.status == TaskStatus.DONE)

    return ProjectResponse(
        id=proj.id,
        title=proj.title,
        description=proj.description,
        department_id=proj.department_id,
        department_name=dept_name,
        project_manager_id=proj.project_manager_id,
        project_manager_name=pm_name,
        budget=proj.budget,
        status=proj.status,
        start_date=proj.start_date,
        end_date=proj.end_date,
        task_count=task_count,
        completed_task_count=completed_task_count,
        created_at=proj.created_at
    )

@router.get("/", response_model=List[ProjectResponse])
def list_projects(
    department_id: Optional[int] = None,
    status_filter: Optional[ProjectStatus] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(Project)
    if department_id:
        query = query.filter(Project.department_id == department_id)
    if status_filter:
        query = query.filter(Project.status == status_filter)
    projects = query.all()
    return [_format_project(p, db) for p in projects]

@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(project_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    proj = db.query(Project).filter(Project.id == project_id).first()
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")
    return _format_project(proj, db)

@router.post("/", response_model=ProjectResponse)
def create_project(
    proj_in: ProjectCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(RoleChecker([UserRole.SUPER_ADMIN, UserRole.DEPARTMENT_HEAD, UserRole.MANAGER]))
):
    proj = Project(
        title=proj_in.title,
        description=proj_in.description,
        department_id=proj_in.department_id,
        project_manager_id=proj_in.project_manager_id,
        budget=proj_in.budget,
        status=proj_in.status,
        start_date=proj_in.start_date,
        end_date=proj_in.end_date
    )
    db.add(proj)
    db.commit()
    db.refresh(proj)
    return _format_project(proj, db)

@router.put("/{project_id}", response_model=ProjectResponse)
def update_project(
    project_id: int,
    proj_in: ProjectUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(RoleChecker([UserRole.SUPER_ADMIN, UserRole.DEPARTMENT_HEAD, UserRole.MANAGER]))
):
    proj = db.query(Project).filter(Project.id == project_id).first()
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")

    if proj_in.title is not None:
        proj.title = proj_in.title
    if proj_in.description is not None:
        proj.description = proj_in.description
    if proj_in.department_id is not None:
        proj.department_id = proj_in.department_id
    if proj_in.project_manager_id is not None:
        proj.project_manager_id = proj_in.project_manager_id
    if proj_in.budget is not None:
        proj.budget = proj_in.budget
    if proj_in.status is not None:
        proj.status = proj_in.status
    if proj_in.start_date is not None:
        proj.start_date = proj_in.start_date
    if proj_in.end_date is not None:
        proj.end_date = proj_in.end_date

    db.commit()
    db.refresh(proj)
    return _format_project(proj, db)

@router.delete("/{project_id}")
def delete_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(RoleChecker([UserRole.SUPER_ADMIN, UserRole.MANAGER]))
):
    proj = db.query(Project).filter(Project.id == project_id).first()
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")
    db.delete(proj)
    db.commit()
    return {"message": "Project deleted successfully"}
