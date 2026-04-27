from uuid import UUID

from sqlalchemy.orm import Session

from app.models.user import AppUser
from app.schemas.user import UserCreate
from app.services.auth_service import get_password_hash


def get_user_by_email(db: Session, email: str) -> AppUser | None:
    """
    Tìm user theo email (case-insensitive, trim whitespace).
    """
    return db.query(AppUser).filter(AppUser.email == email.strip().lower()).first()


def get_user_by_id(db: Session, user_id: UUID) -> AppUser | None:
    """Tìm user theo UUID."""
    return db.query(AppUser).filter(AppUser.id == user_id).first()


def create_user(db: Session, user: UserCreate, role: str = "user") -> AppUser:
    """
    Tạo user mới với email/password authentication.
    Password được hash bằng PBKDF2 trước khi lưu.
    """
    db_user = AppUser(
        email=user.email,
        password_hash=get_password_hash(user.password),
        role=role,
        is_active=True,
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def update_user_role(db: Session, user_id: UUID, role: str) -> AppUser | None:
    """
    Cập nhật role của user (admin/user).
    Trả về None nếu user không tồn tại.
    """
    user = get_user_by_id(db, user_id)
    if user is None:
        return None

    user.role = role
    db.commit()
    db.refresh(user)
    return user


def find_or_create_google_user(db: Session, google_id: str, email: str) -> AppUser:
    """
    Tìm hoặc tạo user cho Google OAuth login.

    Logic:
    1. Tìm theo google_id trước (user đã link Google account)
    2. Nếu không có: tìm theo email (user có thể đã đăng ký bằng email/password trước đó)
       -> Link Google account vào user hiện có
    3. Nếu không có: tạo user mới với Google authentication (không có password)

    Pattern này cho phép user có thể login bằng cả email/password và Google.
    """
    # 1. Try to find by google_id first
    user = db.query(AppUser).filter(AppUser.google_id == google_id).first()
    if user:
        return user

    # 2. Try to find by email (user might have registered with email/password before)
    user = get_user_by_email(db, email)
    if user:
        # Link the Google account to the existing user
        user.google_id = google_id
        db.commit()
        db.refresh(user)
        return user

    # 3. Create a brand-new user (no password since they use Google)
    new_user = AppUser(
        email=email.strip().lower(),
        password_hash=None,
        google_id=google_id,
        role="user",
        is_active=True,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user
