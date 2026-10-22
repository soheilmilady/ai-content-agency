from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.core.limiter import limiter

from app.api.v1.deps import get_current_user, get_db
from app.core.security import create_token, hash_password, verify_password
from app.models.user import User
from app.schemas.user import ProfileUpdate, Token, UserResponse

router = APIRouter()


@router.post("/auth/login", response_model=Token)
@limiter.limit("10/minute")
def login(request: Request, form_data: Annotated[OAuth2PasswordRequestForm, Depends()], db: Annotated[Session, Depends(get_db)]):
    user = db.query(User).filter(
        (User.email == form_data.username) | (User.username == form_data.username)
    ).first()

    now = datetime.now(timezone.utc)

    # 1. Check if user account is locked
    if user and user.locked_until:
        locked_time = user.locked_until
        if locked_time.tzinfo is None:
            locked_time = locked_time.replace(tzinfo=timezone.utc)

        if now < locked_time:
            remaining = max(1, int((locked_time - now).total_seconds() / 60))
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"حساب کاربری موقتاً به دلیل ۵ تلاش ناموفق پیاپی قفل شده است. لطفاً {remaining} دقیقه دیگر مجدداً تلاش فرمایید.",
            )
        else:
            user.locked_until = None
            user.failed_login_attempts = 0
            db.commit()

    # 2. Verify password
    if user is None or not verify_password(form_data.password, user.hashed_password):
        if user:
            user.failed_login_attempts = (user.failed_login_attempts or 0) + 1
            if user.failed_login_attempts >= 5:
                user.locked_until = datetime.now(timezone.utc) + timedelta(minutes=15)
            db.commit()

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="ایمیل یا رمز عبور اشتباه است.",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="حساب کاربری غیرفعال است.",
        )

    # 3. Reset failed counters on successful login
    if (user.failed_login_attempts or 0) > 0 or user.locked_until is not None:
        user.failed_login_attempts = 0
        user.locked_until = None
        db.commit()

    # 4. Issue token with token_version binding
    tv = getattr(user, "token_version", 1) or 1
    access_token = create_token({"sub": str(user.id), "tv": tv})
    return Token(access_token=access_token, token_type="bearer")


@router.post("/auth/logout")
def logout(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    """Instant Session Invalidation: increment token_version to invalidate all issued JWTs."""
    current_user.token_version = (getattr(current_user, "token_version", 1) or 1) + 1
    db.commit()
    return {"detail": "با موفقیت خارج شدید. کلیه نشست‌های فعال باطل شدند."}


@router.get("/auth/me", response_model=UserResponse)
def me(current_user: Annotated[User, Depends(get_current_user)]):
    return current_user


@router.patch("/auth/me", response_model=UserResponse)
def update_me(
    body: ProfileUpdate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    if body.new_password is not None or body.email is not None:
        if not body.current_password or not verify_password(
            body.current_password, current_user.hashed_password
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="رمز عبور فعلی اشتباه است.",
            )

    if body.email is not None:
        existing = (
            db.query(User)
            .filter(User.email == body.email, User.id != current_user.id)
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="این ایمیل قبلاً ثبت شده است.",
            )
        current_user.email = body.email

    if body.username is not None:
        existing = (
            db.query(User)
            .filter(User.username == body.username, User.id != current_user.id)
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="این نام کاربری قبلاً استفاده شده است.",
            )
        current_user.username = body.username

    if body.new_password is not None:
        current_user.hashed_password = hash_password(body.new_password)
        # Invalidate all existing tokens on other devices after password change
        current_user.token_version = (getattr(current_user, "token_version", 1) or 1) + 1

    db.commit()
    db.refresh(current_user)
    return current_user
