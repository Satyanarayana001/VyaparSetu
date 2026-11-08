from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from . import models
from .database import get_db
from .errors import ApiError
from .security import decode_access_token

bearer = HTTPBearer(auto_error=False)


def get_current_user(creds: HTTPAuthorizationCredentials | None = Depends(bearer), db: Session = Depends(get_db)) -> models.User:
    if creds is None:
        raise ApiError(401, "NOT_AUTHENTICATED", "Sign in to continue.")
    payload = decode_access_token(creds.credentials)
    if not payload or not str(payload.get("sub", "")).isdigit():
        raise ApiError(401, "INVALID_TOKEN", "Your session has expired. Sign in again.")
    user = db.get(models.User, int(payload["sub"]))
    if user is None or not user.is_active:
        raise ApiError(401, "INVALID_TOKEN", "Your session has expired. Sign in again.")
    return user


def require_roles(*roles: models.Role):
    def dep(user: models.User = Depends(get_current_user)) -> models.User:
        if user.role not in roles:
            raise ApiError(403, "FORBIDDEN", "You don't have access to this.")
        return user
    return dep


retailer_user = require_roles(models.Role.retailer)


def current_retailer(user: models.User = Depends(retailer_user), db: Session = Depends(get_db)) -> models.Retailer:
    return db.get(models.Retailer, user.retailer_id)


def retailer_for_access(retailer_id: int, user: models.User = Depends(get_current_user),
                        db: Session = Depends(get_db)) -> models.Retailer:
    """Retailer: only their own. Salesman: only assigned retailers. Desk: any. Everything else is a 404 (no existence leak)."""
    retailer = db.get(models.Retailer, retailer_id)
    allowed = retailer is not None and (
        user.role == models.Role.desk
        or (user.role == models.Role.retailer and user.retailer_id == retailer.id)
        or (user.role == models.Role.salesman and user.salesman_id is not None and retailer.salesman_id == user.salesman_id))
    if not allowed:
        raise ApiError(404, "NOT_FOUND", "Retailer not found.")
    return retailer
