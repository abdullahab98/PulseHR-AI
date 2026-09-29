from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from datetime import date
import uuid

from app.database import get_db
from app.models import InventoryAsset, Employee, Department, UserRole
from app.schemas import InventoryAssetResponse
from app.security import get_current_user, RoleChecker

router = APIRouter(prefix="/inventory", tags=["Inventory & Asset Panel"])

class InventoryAssetCreate(BaseModel):
    name: str
    category: str
    serial_number: Optional[str] = None
    assigned_to_id: Optional[int] = None
    department_id: Optional[int] = None
    status: Optional[str] = "IN_USE"

@router.get("/assets", response_model=List[InventoryAssetResponse])
def get_inventory_assets(db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    assets = db.query(InventoryAsset).all()
    res = []
    for a in assets:
        emp = db.query(Employee).filter(Employee.id == a.assigned_to_id).first() if a.assigned_to_id else None
        dept = db.query(Department).filter(Department.id == a.department_id).first() if a.department_id else None
        res.append(InventoryAssetResponse(
            id=a.id,
            asset_code=a.asset_code,
            name=a.name,
            category=a.category,
            serial_number=a.serial_number or "",
            assigned_to_id=a.assigned_to_id,
            assigned_to_name=f"{emp.first_name} {emp.last_name}" if emp else "Unassigned",
            department_name=dept.name if dept else "General Pool",
            status=a.status or "IN_USE",
            purchased_date=a.purchased_date or date.today()
        ))
    return res

@router.post("/assets", response_model=InventoryAssetResponse)
def create_inventory_asset(a_in: InventoryAssetCreate, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    asset_code = f"AST-{uuid.uuid4().hex[:6].upper()}"

    asset = InventoryAsset(
        asset_code=asset_code,
        name=a_in.name,
        category=a_in.category,
        serial_number=a_in.serial_number or f"SN-{uuid.uuid4().hex[:8].upper()}",
        assigned_to_id=a_in.assigned_to_id,
        department_id=a_in.department_id,
        status=a_in.status,
        purchased_date=date.today()
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)

    emp = db.query(Employee).filter(Employee.id == asset.assigned_to_id).first() if asset.assigned_to_id else None
    dept = db.query(Department).filter(Department.id == asset.department_id).first() if asset.department_id else None

    return InventoryAssetResponse(
        id=asset.id,
        asset_code=asset.asset_code,
        name=asset.name,
        category=asset.category,
        serial_number=asset.serial_number,
        assigned_to_id=asset.assigned_to_id,
        assigned_to_name=f"{emp.first_name} {emp.last_name}" if emp else "Unassigned",
        department_name=dept.name if dept else "General Pool",
        status=asset.status,
        purchased_date=asset.purchased_date
    )
