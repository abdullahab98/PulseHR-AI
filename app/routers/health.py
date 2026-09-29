from typing import Dict, Any
from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.config import settings
from app.database import get_db
from app.timezone import get_local_now
from app.mongodb import mongo_manager

router = APIRouter(tags=["Health & System Status"])

@router.get("/health")
def health_check(response: Response, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Comprehensive system health check:
    - Verifies API service status
    - Checks SQLite / Relational database connectivity (SELECT 1)
    - Checks MongoDB connection status (if initialized)
    - Returns current timestamp, timezone, and API version
    """
    health_status: Dict[str, Any] = {
        "status": "healthy",
        "system": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "timestamp": get_local_now().isoformat(),
        "timezone": getattr(settings, "TIMEZONE", "Asia/Dhaka"),
        "services": {}
    }

    # 1. Relational Database Check (SQLAlchemy)
    try:
        db.execute(text("SELECT 1"))
        db_type = "sqlite" if settings.DATABASE_URL.startswith("sqlite") else "relational_db"
        health_status["services"]["database"] = {
            "status": "connected",
            "type": db_type
        }
    except Exception as e:
        health_status["status"] = "degraded"
        health_status["services"]["database"] = {
            "status": "error",
            "error": str(e)
        }
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    # 2. MongoDB Check (Optional / Document DB)
    if not settings.MONGODB_URL:
        health_status["services"]["mongodb"] = {
            "status": "not_configured"
        }
    elif mongo_manager.client is not None:
        try:
            mongo_manager.client.admin.command("ping")
            health_status["services"]["mongodb"] = {
                "status": "connected",
                "database": settings.MONGODB_DB_NAME
            }
        except Exception as e:
            health_status["services"]["mongodb"] = {
                "status": "unreachable",
                "warning": str(e)
            }
    else:
        health_status["services"]["mongodb"] = {
            "status": "ready"
        }

    return health_status


@router.get("/health/live")
def liveness_check() -> Dict[str, str]:
    """
    Simple, lightweight liveness check for container orchestration and load balancers.
    """
    return {
        "status": "alive",
        "system": settings.PROJECT_NAME
    }
