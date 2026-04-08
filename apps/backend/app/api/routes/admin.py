from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.dependencies.deps import get_current_admin_user, get_db
from app.models.system_log import SystemLog
from app.models.user import AppUser
from app.schemas.admin import AdminAnalyticsResponse
from app.schemas.system_log import SystemLogResponse
from app.schemas.user import UserResponse, UserRoleUpdate
from app.services import admin_service, user_service


router = APIRouter()


@router.get("/users", response_model=List[UserResponse])
def list_users(
    db: Session = Depends(get_db),
    _current_admin: AppUser = Depends(get_current_admin_user),
):
    return admin_service.list_users(db)


@router.get("/logs", response_model=List[SystemLogResponse])
def get_logs(
    db: Session = Depends(get_db),
    _current_admin: AppUser = Depends(get_current_admin_user),
):
    return admin_service.get_logs(db)


@router.get("/analytics", response_model=AdminAnalyticsResponse)
def get_analytics(
    db: Session = Depends(get_db),
    _current_admin: AppUser = Depends(get_current_admin_user),
):
    return admin_service.get_admin_analytics(db)


@router.patch("/users/{user_id}/role", response_model=UserResponse)
def update_user_role(
    user_id: UUID,
    payload: UserRoleUpdate,
    db: Session = Depends(get_db),
    current_admin: AppUser = Depends(get_current_admin_user),
):
    user = user_service.update_user_role(db, user_id, payload.role)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    return user
