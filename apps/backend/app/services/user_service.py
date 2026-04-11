from uuid import UUID

from sqlalchemy.orm import Session

from app.models.user import AppUser
from app.schemas.user import UserCreate
from app.services.auth_service import get_password_hash


def get_user_by_email(db: Session, email: str) -> AppUser | None:
    return db.query(AppUser).filter(AppUser.email == email.strip().lower()).first()


def get_user_by_id(db: Session, user_id: UUID) -> AppUser | None:
    return db.query(AppUser).filter(AppUser.id == user_id).first()


def create_user(db: Session, user: UserCreate, role: str = "user") -> AppUser:
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
    user = get_user_by_id(db, user_id)
    if user is None:
        return None

    user.role = role
    db.commit()
    db.refresh(user)
    return user


def find_or_create_google_user(db: Session, google_id: str, email: str) -> AppUser:
    """Find existing user by google_id or email, or create a new one."""
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
