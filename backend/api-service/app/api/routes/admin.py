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
    """
    Lấy danh sách tất cả users trong hệ thống.
    Chỉ admin mới có quyền truy cập endpoint này.
    """
    return admin_service.list_users(db)


@router.get("/logs", response_model=List[SystemLogResponse])
def get_logs(
    db: Session = Depends(get_db),
    _current_admin: AppUser = Depends(get_current_admin_user),
):
    """
    Lấy system logs gần đây (mặc định 200 logs).
    Dùng cho monitoring và debugging.
    """
    return admin_service.get_logs(db)


@router.get("/analytics", response_model=AdminAnalyticsResponse)
def get_analytics(
    db: Session = Depends(get_db),
    _current_admin: AppUser = Depends(get_current_admin_user),
):
    """
    Lấy toàn bộ analytics data cho admin dashboard.
    Bao gồm: overview metrics, charts, tables, system/model/data metrics.
    """
    return admin_service.get_admin_analytics(db)


@router.patch("/users/{user_id}/role", response_model=UserResponse)
def update_user_role(
    user_id: UUID,
    payload: UserRoleUpdate,
    db: Session = Depends(get_db),
    current_admin: AppUser = Depends(get_current_admin_user),
):
    """
    Cập nhật role của user (admin/user).
    Chỉ admin mới có quyền thay đổi role.
    """
    user = user_service.update_user_role(db, user_id, payload.role)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    return user
