from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import AuditLog, User, UserRole
from app.schemas import AuditLogResponse
from app.security import get_current_user, RoleChecker

router = APIRouter(prefix="/audit-logs", tags=["Audit Logs & Compliance"])

@router.get("/", response_model=List[AuditLogResponse])
def list_audit_logs(
    db: Session = Depends(get_db),
    current_user: User = Depends(RoleChecker([UserRole.SUPER_ADMIN, UserRole.DEPARTMENT_HEAD, UserRole.SPECIAL_USER]))
):
    logs = db.query(AuditLog).order_by(AuditLog.timestamp.desc()).limit(100).all()
    res = []
    for l in logs:
        user_email = l.user.email if l.user else "System"
        res.append(
            AuditLogResponse(
                id=l.id,
                user_id=l.user_id,
                user_email=user_email,
                action=l.action,
                entity_type=l.entity_type,
                entity_id=l.entity_id,
                details=l.details or {},
                ip_address=l.ip_address,
                timestamp=l.timestamp
            )
        )
    return res
