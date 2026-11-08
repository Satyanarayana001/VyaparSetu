from fastapi import APIRouter, Depends, Response
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from .. import models, schemas
from ..database import get_db
from ..deps import current_retailer, retailer_user
from ..errors import ApiError
from ..models import OrderStatus
from ..services import orders as svc

router = APIRouter(prefix="/orders", tags=["orders"])


def _load(db: Session, order_id: int, retailer: models.Retailer) -> models.Order:
    order = db.scalar(select(models.Order).where(models.Order.id == order_id, models.Order.retailer_id == retailer.id)
                      .options(selectinload(models.Order.items), selectinload(models.Order.retailer)))
    if order is None:
        raise ApiError(404, "NOT_FOUND", "Order not found.")
    return order


@router.post("/quote", response_model=schemas.QuoteOut)
def quote(body: schemas.QuoteIn, retailer: models.Retailer = Depends(current_retailer), db: Session = Depends(get_db)):
    """Server-side pricing for the cart. The UI shows these numbers; it never computes money itself."""
    lines = svc.price_items(db, retailer, [svc.ItemInput(i.sku, i.quantity_cases, i.ai_line_id) for i in body.items])
    t = svc.totals(lines)
    credit = svc.credit_summary(db, retailer)
    out = [schemas.QuoteLineOut(
        sku=l.sku, product_name=l.product.name if l.product else None, quantity_cases=l.quantity_cases,
        free_cases=l.calc.free_cases if l.calc else 0, case_price_paise=l.calc.case_price_paise if l.calc else None,
        gross_paise=l.calc.gross_paise if l.calc else None, discount_paise=l.calc.discount_paise if l.calc else None,
        line_total_paise=l.calc.line_total_paise if l.calc else None, scheme_applied=l.calc.scheme_applied if l.calc else None,
        issues=[schemas.IssueOut(**i) for i in l.issues]) for l in lines]
    return schemas.QuoteOut(lines=out, **t, can_order=bool(lines) and not any(l.issues for l in lines), credit=credit,
                            credit_ok=t["total_paise"] <= credit["available_paise"])


@router.post("", response_model=schemas.OrderCreatedOut, status_code=201)
def place_order(body: schemas.OrderCreateIn, response: Response, user: models.User = Depends(retailer_user),
                db: Session = Depends(get_db)):
    retailer = user.retailer
    order, duplicate = svc.create_order(db, user, retailer, [svc.ItemInput(i.sku, i.quantity_cases, i.ai_line_id) for i in body.items],
                                        body.source, body.idempotency_key, body.ai_parse_id, body.repeat_of_order_id)
    if duplicate:
        response.status_code = 200
    return schemas.OrderCreatedOut(order=_load(db, order.id, retailer), duplicate=duplicate)


@router.get("", response_model=list[schemas.OrderSummaryOut])
def my_orders(retailer: models.Retailer = Depends(current_retailer), db: Session = Depends(get_db)):
    rows = db.scalars(select(models.Order).where(models.Order.retailer_id == retailer.id)
                      .options(selectinload(models.Order.items), selectinload(models.Order.retailer))
                      .order_by(models.Order.created_at.desc(), models.Order.id.desc()).limit(100))
    return [schemas.OrderSummaryOut(id=o.id, order_number=o.order_number, status=o.status, source=o.source,
                                    retailer=o.retailer, created_at=o.created_at, total_paise=o.total_paise,
                                    item_count=len(o.items), exported_at=o.exported_at) for o in rows]


@router.get("/last-repeatable", response_model=schemas.RepeatOut)
def last_repeatable(retailer: models.Retailer = Depends(current_retailer), db: Session = Depends(get_db)):
    """The retailer's previous confirmed/dispatched order, as cart items. Prices and stock are re-checked by /quote."""
    order = db.scalar(select(models.Order).where(models.Order.retailer_id == retailer.id,
                                                 models.Order.status.in_([OrderStatus.confirmed, OrderStatus.dispatched]))
                      .options(selectinload(models.Order.items)).order_by(models.Order.created_at.desc(), models.Order.id.desc()).limit(1))
    if order is None:
        raise ApiError(404, "NO_PREVIOUS_ORDER", "You don't have a confirmed order to repeat yet.")
    return schemas.RepeatOut(order_id=order.id, order_number=order.order_number, created_at=order.created_at,
                             items=[schemas.ItemIn(sku=i.sku, quantity_cases=i.quantity_cases) for i in order.items])


@router.get("/{order_id}", response_model=schemas.OrderOut)
def get_order(order_id: int, retailer: models.Retailer = Depends(current_retailer), db: Session = Depends(get_db)):
    return _load(db, order_id, retailer)
