from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.dependencies.deps import get_current_active_user, get_db
from app.core.config import settings
from app.models.user import AppUser
from app.schemas.auth import Token
from app.schemas.user import UserCreate, UserResponse
from app.services import auth_service, user_service


router = APIRouter()


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(user: UserCreate, db: Session = Depends(get_db)):
    """
    Đăng ký user mới với email/password.
    Kiểm tra email đã tồn tại trước khi tạo.
    """
    existing_user = user_service.get_user_by_email(db, user.email)
    if existing_user:
        raise HTTPException(status_code=400, detail="Email đã được đăng ký")
    return user_service.create_user(db, user)


@router.post("/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """
    Login với email/password, trả về JWT access token.

    Security:
    - Verify password bằng PBKDF2 hash comparison (timing-safe)
    - Token chứa user_id và role trong payload
    """
    user = user_service.get_user_by_email(db, form_data.username)
    if not user or not user.password_hash or not auth_service.verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sai email hoặc mật khẩu",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = auth_service.create_access_token(data={"sub": str(user.id), "role": user.role})
    return Token(access_token=access_token)


class GoogleLoginRequest(BaseModel):
    id_token: str


@router.post("/google", response_model=Token)
def google_login(payload: GoogleLoginRequest, db: Session = Depends(get_db)):
    """
    Google OAuth login: verify Google ID token và trả về JWT.

    Flow:
    1. Verify ID token với Google API
    2. Extract google_id và email từ token
    3. Find hoặc create user (link Google account nếu user đã tồn tại)
    4. Trả về JWT access token

    Security: Google ID token được verify với Google's public keys.
    """
    if not settings.google_client_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="GOOGLE_CLIENT_ID chưa được cấu hình trên server.",
        )

    try:
        from google.oauth2 import id_token as google_id_token
        from google.auth.transport import requests as google_requests

        idinfo = google_id_token.verify_oauth2_token(
            payload.id_token,
            google_requests.Request(),
            settings.google_client_id,
            clock_skew_in_seconds=10,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token Google không hợp lệ: {e}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Lỗi xác thực Google: {type(e).__name__}: {e}",
        )

    google_id = idinfo["sub"]
    email = idinfo.get("email", "")

    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tài khoản Google không có email.",
        )

    user = user_service.find_or_create_google_user(db, google_id=google_id, email=email)
    access_token = auth_service.create_access_token(data={"sub": str(user.id), "role": user.role})
    return Token(access_token=access_token)


@router.get("/me", response_model=UserResponse)
def read_current_user(current_user: AppUser = Depends(get_current_active_user)):
    """
    Lấy thông tin user hiện tại từ JWT token.
    Dependency get_current_active_user tự động verify token và load user.
    """
    return current_user
