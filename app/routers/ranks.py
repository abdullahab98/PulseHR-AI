from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Rank, User, UserRole
from app.schemas import RankCreate, RankUpdate, RankResponse
from app.security import get_current_user, RoleChecker

router = APIRouter(prefix="/ranks", tags=["Rank Management"])

ALLOWED_ROLES = [UserRole.SUPER_ADMIN, UserRole.DEPARTMENT_HEAD, UserRole.MANAGER]

@router.get("/", response_model=List[RankResponse])
def list_ranks(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return db.query(Rank).order_by(Rank.name).all()

@router.get("/{rank_id}", response_model=RankResponse)
def get_rank(
    rank_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    rank = db.query(Rank).filter(Rank.id == rank_id).first()
    if not rank:
        raise HTTPException(status_code=404, detail="Rank not found")
    return rank

@router.post("/", response_model=RankResponse)
def create_rank(
    rank_in: RankCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(RoleChecker(ALLOWED_ROLES))
):
    existing = db.query(Rank).filter(Rank.name == rank_in.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Rank with this name already exists")

    rank = Rank(name=rank_in.name)
    db.add(rank)
    db.commit()
    db.refresh(rank)
    return rank

@router.put("/{rank_id}", response_model=RankResponse)
def update_rank(
    rank_id: int,
    rank_in: RankUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(RoleChecker(ALLOWED_ROLES))
):
    rank = db.query(Rank).filter(Rank.id == rank_id).first()
    if not rank:
        raise HTTPException(status_code=404, detail="Rank not found")

    if rank_in.name is not None:
        rank.name = rank_in.name

    db.commit()
    db.refresh(rank)
    return rank

@router.delete("/{rank_id}")
def delete_rank(
    rank_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(RoleChecker(ALLOWED_ROLES))
):
    rank = db.query(Rank).filter(Rank.id == rank_id).first()
    if not rank:
        raise HTTPException(status_code=404, detail="Rank not found")
    db.delete(rank)
    db.commit()
    return {"message": "Rank deleted successfully"}
