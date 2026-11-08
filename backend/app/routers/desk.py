from fastapi import APIRouter, Depends, Response
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from .. import models, schemas
from ..database import get_db
from ..deps import require_roles
from ..errors import ApiError
from ..models import OrderStatus, Role
from ..services import csv_export
from ..services import orders as svc
from ..services.aliases import upsert_alias

router = APIRouter(prefix="/desk", tags=["order desk"])
desk_user = require_roles(Role.desk)


def _order(db: Session, order_id: int) -> models.Order:
    o = db.scalar(select(models.Order).where(models.Order.id == order_id)
                  .options(selectinload(models.Order.items), selectinload(models.Order.retailer), selectinload(models.Order.ai_parse)))
    if o is None:
        raise ApiError(404, "NOT_FOUND", "Order not found.")
    return o


def _detail(db: Session, o: models.Order) -> dict:
    base = schemas.OrderOut.model_validate(o).model_dump(mode="json")
    r = o.retailer
    base["retailer_detail"] = {**schemas.RetailerBrief.model_validate(r).model_dump(), "credit": svc.credit_summary(db, r)}
    base["ai"] = ({"mode": o.ai_parse.mode, "fallback_reason": o.ai_parse.fallback_reason, "model": o.ai_parse.model}
                  if o.ai_parse else None)
    return base


@router.get("/orders")
def list_orders(status: OrderStatus | None = None, q: str | None = None, limit: int = 100, offset: int = 0,
                _: models.User = Depends(desk_user), db: Session = Depends(get_db)):
    limit = max(1, min(limit, 200))
    stmt = select(models.Order).join(models.Retailer).options(selectinload(models.Order.items), selectinload(models.Order.retailer))
    if status:
        stmt = stmt.where(models.Order.status == status)
    if q and q.strip():
        t = q.strip().lower()[:60]
        stmt = stmt.where(or_(func.lower(models.Order.order_number).contains(t, autoescape=True),
                              func.lower(models.Retailer.name).contains(t, autoescape=True),
                              func.lower(models.Retailer.code).contains(t, autoescape=True)))
    rows = db.scalars(stmt.order_by(models.Order.created_at.desc(), models.Order.id.desc()).limit(limit).offset(max(offset, 0)))
    counts = {s.value: 0 for s in OrderStatus}
    for s, n in db.execute(select(models.Order.status, func.count()).group_by(models.Order.status)):
        counts[s.value] = n
    return {"orders": [schemas.OrderSummaryOut(id=o.id, order_number=o.order_number, status=o.status, source=o.source,
                                               retailer=o.retailer, created_at=o.created_at, total_paise=o.total_paise,
                                               item_count=len(o.items), exported_at=o.exported_at).model_dump(mode="json") for o in rows],
            "counts": counts}


@router.get("/orders/{order_id}")
def get_order(order_id: int, _: models.User = Depends(desk_user), db: Session = Depends(get_db)):
    return _detail(db, _order(db, order_id))


@router.post("/orders/{order_id}/status")
def set_status(order_id: int, body: schemas.StatusChangeIn, user: models.User = Depends(desk_user), db: Session = Depends(get_db)):
    o = _order(db, order_id)
    svc.change_status(db, o, body.status, user, body.reason)
    return _detail(db, _order(db, order_id))


@router.patch("/orders/{order_id}/items/{item_id}")
def correct_item(order_id: int, item_id: int, body: schemas.ItemCorrectionIn, user: models.User = Depends(desk_user),
                 db: Session = Depends(get_db)):
    o = _order(db, order_id)
    item = next((i for i in o.items if i.id == item_id), None)
    if item is None:
        raise ApiError(404, "NOT_FOUND", "Order line not found.")
    svc.correct_item(db, o, item, user, body.sku, body.quantity_cases, body.save_alias)
    return _detail(db, _order(db, order_id))


@router.get("/retailers")
def retailers(_: models.User = Depends(desk_user), db: Session = Depends(get_db)):
    return [{**schemas.RetailerBrief.model_validate(r).model_dump(), "credit": svc.credit_summary(db, r)}
            for r in db.scalars(select(models.Retailer).order_by(models.Retailer.name))]


def _alias_out(a: models.RetailerAlias) -> schemas.AliasOut:
    return schemas.AliasOut(id=a.id, alias_text=a.alias_text, sku=a.product.sku, product_name=a.product.name, created_at=a.created_at)


@router.get("/retailers/{retailer_id}/aliases", response_model=list[schemas.AliasOut])
def list_aliases(retailer_id: int, _: models.User = Depends(desk_user), db: Session = Depends(get_db)):
    rows = db.scalars(select(models.RetailerAlias).where(models.RetailerAlias.retailer_id == retailer_id)
                      .options(selectinload(models.RetailerAlias.product)).order_by(models.RetailerAlias.alias_text))
    return [_alias_out(a) for a in rows]


@router.post("/retailers/{retailer_id}/aliases", response_model=schemas.AliasOut, status_code=201)
def add_alias(retailer_id: int, body: schemas.AliasIn, user: models.User = Depends(desk_user), db: Session = Depends(get_db)):
    if db.get(models.Retailer, retailer_id) is None:
        raise ApiError(404, "NOT_FOUND", "Retailer not found.")
    product = db.scalar(select(models.Product).where(models.Product.sku == body.sku, models.Product.is_active.is_(True)))
    if product is None:
        raise ApiError(422, "UNKNOWN_PRODUCT", "That product is not available.")
    a = upsert_alias(db, retailer_id, product, body.alias_text, user.id)
    db.commit()
    return _alias_out(a)


@router.delete("/retailers/{retailer_id}/aliases/{alias_id}", status_code=204)
def delete_alias(retailer_id: int, alias_id: int, _: models.User = Depends(desk_user), db: Session = Depends(get_db)):
    a = db.get(models.RetailerAlias, alias_id)
    if a is None or a.retailer_id != retailer_id:
        raise ApiError(404, "NOT_FOUND", "Alias not found.")
    db.delete(a)
    db.commit()
    return Response(status_code=204)


@router.post("/export/tally")
def export_tally(body: schemas.ExportIn, _: models.User = Depends(desk_user), db: Session = Depends(get_db)):
    """Tally-compatible CSV built from database records. Only CONFIRMED orders can be exported. No live Tally integration."""
    stmt = select(models.Order).where(models.Order.status == OrderStatus.confirmed).options(
        selectinload(models.Order.items), selectinload(models.Order.retailer)).order_by(models.Order.id)
    if body.order_ids is not None:
        found = list(db.scalars(select(models.Order).where(models.Order.id.in_(body.order_ids))))
        bad = [o.order_number for o in found if o.status != OrderStatus.confirmed]
        if bad or len(found) != len(set(body.order_ids)):
            raise ApiError(422, "NOT_EXPORTABLE", "Only confirmed orders can be exported.", bad)
        stmt = stmt.where(models.Order.id.in_(body.order_ids))
    elif not body.include_exported:
        stmt = stmt.where(models.Order.exported_at.is_(None))
    orders = list(db.scalars(stmt))
    if not orders:
        raise ApiError(422, "NOTHING_TO_EXPORT", "There are no confirmed orders to export.")
    content = csv_export.build_csv(orders)
    csv_export.mark_exported(orders)
    db.commit()
    return Response(content="\ufeff" + content, media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": 'attachment; filename="tally-orders.csv"',
                             "X-Exported-Orders": str(len(orders))})
