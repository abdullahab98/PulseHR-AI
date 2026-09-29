from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from app.database import get_db
from app.models import DocumentRecord, Employee, UserRole
from app.schemas import DocumentRecordResponse
from app.security import get_current_user, RoleChecker

router = APIRouter(prefix="/documents", tags=["Document Management Panel"])

class DocumentCreate(BaseModel):
    title: str
    category: str
    file_name: str
    uploader_id: Optional[int] = None
    confidentiality_level: Optional[str] = "INTERNAL"

@router.get("/files", response_model=List[DocumentRecordResponse])
@router.get("/records", response_model=List[DocumentRecordResponse])
def get_documents(db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    docs = db.query(DocumentRecord).all()
    res = []
    for d in docs:
        emp = db.query(Employee).filter(Employee.id == d.uploader_id).first() if d.uploader_id else None
        res.append(DocumentRecordResponse(
            id=d.id,
            title=d.title,
            category=d.category,
            file_name=d.file_name,
            uploader_id=d.uploader_id,
            uploader_name=f"{emp.first_name} {emp.last_name}" if emp else "System",
            confidentiality_level=d.confidentiality_level or "INTERNAL",
            created_at=d.created_at or datetime.utcnow()
        ))
    return res

@router.post("/files", response_model=DocumentRecordResponse)
@router.post("/records", response_model=DocumentRecordResponse)
def upload_document(doc_in: DocumentCreate, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    emp = db.query(Employee).filter(Employee.user_id == current_user.id).first()
    uploader_id = doc_in.uploader_id or (emp.id if emp else None)
    
    doc = DocumentRecord(
        title=doc_in.title,
        category=doc_in.category,
        file_name=doc_in.file_name,
        uploader_id=uploader_id,
        confidentiality_level=doc_in.confidentiality_level
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    
    uploader_name = f"{emp.first_name} {emp.last_name}" if emp else "System"
    return DocumentRecordResponse(
        id=doc.id,
        title=doc.title,
        category=doc.category,
        file_name=doc.file_name,
        uploader_id=doc.uploader_id,
        uploader_name=uploader_name,
        confidentiality_level=doc.confidentiality_level,
        created_at=doc.created_at or datetime.utcnow()
    )
