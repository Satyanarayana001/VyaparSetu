from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..deps import require_roles

router = APIRouter(prefix="/salesman", tags=["salesman"])


@router.get("/retailers", response_model=list[schemas.RetailerBrief])
def my_retailers(user: models.User = Depends(require_roles(models.Role.salesman)), db: Session = Depends(get_db)):
    """A salesman sees only the retailers assigned to them."""
    return list(db.scalars(select(models.Retailer).where(models.Retailer.salesman_id == user.salesman_id).order_by(models.Retailer.name)))
