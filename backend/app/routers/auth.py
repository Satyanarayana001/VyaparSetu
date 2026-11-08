from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..deps import get_current_user
from ..errors import ApiError
from ..security import create_access_token, login_throttle, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=schemas.LoginOut)
def login(body: schemas.LoginIn, request: Request, db: Session = Depends(get_db)):
    email = body.email.strip().lower()
    key = f"{email}|{request.client.host if request.client else '-'}"
    if login_throttle.blocked(key):
        raise ApiError(429, "TOO_MANY_ATTEMPTS", "Too many failed sign-ins. Wait a minute and try again.")
    user = db.scalar(select(models.User).where(models.User.email == email))
    ok = verify_password(body.password, user.password_hash if user else None)
    if not user or not ok or not user.is_active:
        login_throttle.record_failure(key)
        raise ApiError(401, "INVALID_CREDENTIALS", "Email or password is incorrect.")
    login_throttle.reset(key)
    return schemas.LoginOut(access_token=create_access_token(user.id, user.role.value), user=schemas.UserOut.model_validate(user))


@router.get("/me", response_model=schemas.UserOut)
def me(user: models.User = Depends(get_current_user)):
    return user
