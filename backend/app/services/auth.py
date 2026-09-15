import uuid

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..core.security import hash_password, verify_password
from ..models.user import User


def normalize_email(email: str) -> str:
    return email.strip().casefold()


def register_user(db: Session, email: str, password: str, full_name: str) -> User:
    normalized_email = normalize_email(email)
    if db.scalar(select(User).where(User.email == normalized_email)) is not None:
        raise ValueError("email already registered")

    user = User(
        email=normalized_email,
        full_name=full_name.strip(),
        password_hash=hash_password(password),
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ValueError("email already registered") from exc
    db.refresh(user)
    return user


def authenticate_user(db: Session, email: str, password: str) -> User | None:
    user = db.scalar(select(User).where(User.email == normalize_email(email)))
    if user is None or not user.is_active or not verify_password(password, user.password_hash):
        return None
    return user


def get_user(db: Session, user_id: uuid.UUID) -> User | None:
    return db.get(User, user_id)
