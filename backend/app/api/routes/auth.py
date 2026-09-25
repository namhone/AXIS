from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile, status
from fastapi.responses import StreamingResponse
from io import BytesIO
from sqlalchemy.orm import Session

from ..deps import get_current_user
from ...core.config import get_settings
from ...core.database import get_db
from ...core.security import create_access_token
from ...models.user import User
from ...schemas.auth import LoginRequest, RegisterRequest, UserUpdate
from ...schemas.user import UserResponse
from ...services.auth import authenticate_user, register_user

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])
MAX_AVATAR_BYTES = 5 * 1024 * 1024
ALLOWED_AVATAR_TYPES = {"image/jpeg", "image/png", "image/webp"}


def _set_auth_cookie(response: Response, token: str) -> None:
    settings = get_settings()
    response.set_cookie(
        key=settings.cookie_name,
        value=token,
        max_age=settings.access_token_expire_minutes * 60,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/",
    )


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(
    payload: RegisterRequest,
    response: Response,
    db: Session = Depends(get_db),
) -> User:
    try:
        user = register_user(db, str(payload.email), payload.password, payload.full_name)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists",
        ) from None
    _set_auth_cookie(response, create_access_token(str(user.id)))
    return user


@router.post("/login", response_model=UserResponse)
def login(
    payload: LoginRequest,
    response: Response,
    db: Session = Depends(get_db),
) -> User:
    user = authenticate_user(db, str(payload.email), payload.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    _set_auth_cookie(response, create_access_token(str(user.id)))
    return user


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response) -> None:
    settings = get_settings()
    response.delete_cookie(
        key=settings.cookie_name,
        path="/",
        secure=settings.cookie_secure,
        httponly=True,
        samesite="lax",
    )


@router.get("/me", response_model=UserResponse)
def me(current_user: User = Depends(get_current_user)) -> User:
    return current_user


@router.patch("/me", response_model=UserResponse)
def update_me(
    payload: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:
    current_user.full_name = payload.full_name
    db.commit()
    db.refresh(current_user)
    return current_user


@router.put("/avatar", status_code=status.HTTP_204_NO_CONTENT)
def upload_avatar(
    response: Response,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    if file.content_type not in ALLOWED_AVATAR_TYPES:
        raise HTTPException(status_code=415, detail="Only JPEG, PNG, or WebP images are allowed")
    data = file.file.read(MAX_AVATAR_BYTES + 1)
    if len(data) > MAX_AVATAR_BYTES:
        raise HTTPException(status_code=413, detail="Avatar image must be 5 MB or smaller")
    if not data:
        raise HTTPException(status_code=400, detail="Avatar image is empty")
    signatures = {
        "image/jpeg": data.startswith(b"\xff\xd8\xff"),
        "image/png": data.startswith(b"\x89PNG\r\n\x1a\n"),
        "image/webp": data.startswith(b"RIFF") and data[8:12] == b"WEBP",
    }
    if not signatures.get(file.content_type, False):
        raise HTTPException(status_code=415, detail="The uploaded file is not a valid image")
    current_user.avatar_data = data
    current_user.avatar_mime_type = file.content_type
    db.commit()
    response.status_code = status.HTTP_204_NO_CONTENT


@router.get("/avatar")
def get_avatar(current_user: User = Depends(get_current_user)) -> StreamingResponse:
    if not current_user.avatar_data or not current_user.avatar_mime_type:
        raise HTTPException(status_code=404, detail="Avatar not found")
    return StreamingResponse(
        BytesIO(current_user.avatar_data),
        media_type=current_user.avatar_mime_type,
        headers={"Cache-Control": "private, no-store"},
    )
