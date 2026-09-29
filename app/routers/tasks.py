from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Task, TaskStatus, TaskPriority, TaskComment, Employee, Project, User
from app.schemas import TaskCreate, TaskUpdate, TaskResponse, TaskCommentCreate, TaskCommentResponse
from app.security import get_current_user

router = APIRouter(prefix="/tasks", tags=["Task Management"])

def _format_comment(c: TaskComment) -> TaskCommentResponse:
    author_name = f"{c.author.first_name} {c.author.last_name}" if c.author else "Anonymous"
    return TaskCommentResponse(
        id=c.id,
        task_id=c.task_id,
        author_id=c.author_id,
        author_name=author_name,
        comment=c.comment,
        created_at=c.created_at
    )

def _format_task(task: Task) -> TaskResponse:
    proj_title = task.project.title if task.project else "Unassigned Project"
    assignee_name = f"{task.assignee.first_name} {task.assignee.last_name}" if task.assignee else "Unassigned"
    comments_formatted = [_format_comment(c) for c in (task.comments or [])]

    return TaskResponse(
        id=task.id,
        project_id=task.project_id,
        project_title=proj_title,
        title=task.title,
        description=task.description,
        assignee_id=task.assignee_id,
        assignee_name=assignee_name,
        priority=task.priority,
        due_date=task.due_date,
        required_skills=task.required_skills or [],
        progress=task.progress,
        status=task.status,
        dependencies=task.dependencies or [],
        comments=comments_formatted,
        created_at=task.created_at
    )

@router.get("/", response_model=List[TaskResponse])
def list_tasks(
    project_id: Optional[int] = None,
    assignee_id: Optional[int] = None,
    status_filter: Optional[TaskStatus] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(Task)
    if project_id:
        query = query.filter(Task.project_id == project_id)
    if assignee_id:
        query = query.filter(Task.assignee_id == assignee_id)
    if status_filter:
        query = query.filter(Task.status == status_filter)
    tasks = query.all()
    return [_format_task(t) for t in tasks]

@router.get("/{task_id}", response_model=TaskResponse)
def get_task(task_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return _format_task(task)

@router.post("/", response_model=TaskResponse)
def create_task(task_in: TaskCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    task = Task(
        project_id=task_in.project_id,
        title=task_in.title,
        description=task_in.description,
        assignee_id=task_in.assignee_id,
        priority=task_in.priority,
        due_date=task_in.due_date,
        required_skills=task_in.required_skills,
        progress=task_in.progress,
        status=task_in.status,
        dependencies=task_in.dependencies
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return _format_task(task)

@router.put("/{task_id}", response_model=TaskResponse)
def update_task(task_id: int, task_in: TaskUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if task_in.title is not None:
        task.title = task_in.title
    if task_in.description is not None:
        task.description = task_in.description
    if task_in.assignee_id is not None:
        task.assignee_id = task_in.assignee_id
    if task_in.priority is not None:
        task.priority = task_in.priority
    if task_in.due_date is not None:
        task.due_date = task_in.due_date
    if task_in.required_skills is not None:
        task.required_skills = task_in.required_skills
    if task_in.progress is not None:
        task.progress = task_in.progress
        if task.progress == 100:
            task.status = TaskStatus.DONE
    if task_in.status is not None:
        task.status = task_in.status
        if task.status == TaskStatus.DONE:
            task.progress = 100
    if task_in.dependencies is not None:
        task.dependencies = task_in.dependencies

    db.commit()
    db.refresh(task)
    return _format_task(task)

@router.post("/{task_id}/comments", response_model=TaskCommentResponse)
def add_task_comment(
    task_id: int,
    comment_in: TaskCommentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    emp = db.query(Employee).filter(Employee.user_id == current_user.id).first()
    if not emp:
        raise HTTPException(status_code=400, detail="User does not have an employee profile")

    c = TaskComment(
        task_id=task_id,
        author_id=emp.id,
        comment=comment_in.comment
    )
    db.add(c)
    db.commit()
    db.refresh(c)
    return _format_comment(c)
