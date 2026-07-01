from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from app.core.limiter import limiter

from app.api.v1.deps import get_current_user, get_db
from app.core.security import create_token, hash_password, verify_password
from app.models.user import User
from app.schemas.user import ProfileUpdate, Token, UserResponse
from fastapi.security import OAuth2PasswordRequestForm

router = APIRouter()


@router.post("/auth/login", response_model=Token)
@limiter.limit("10/minute")
def login(request: Request, form_data: Annotated[OAuth2PasswordRequestForm, Depends()], db: Annotated[Session, Depends(get_db)]):
    user = db.query(User).filter(User.email == form_data.username).first()
    if user is None or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Inactive user",
        )
    access_token = create_token({"sub": str(user.id)})
    return Token(access_token=access_token, token_type="bearer")


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
                detail="Current password is incorrect",
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
                detail="Email already registered",
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
                detail="Username already taken",
            )
        current_user.username = body.username

    if body.new_password is not None:
        current_user.hashed_password = hash_password(body.new_password)

    db.commit()
    db.refresh(current_user)
    return current_user
