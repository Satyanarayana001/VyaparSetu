from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from .. import models, schemas
from ..database import get_db
from ..deps import current_retailer, retailer_for_access, require_roles
from ..services import orders as order_svc
from ..services import pricing

router = APIRouter(tags=["catalogue"])

GST_NOTE = ("GST treatment is not specified in the client brief. Prices are shown exactly as supplied; "
            "no GST has been added or removed.")
PRICE_BASIS = "Dealer price is per pack. Case price = dealer price x packs per case."


def build_catalogue(db: Session, retailer: models.Retailer, q: str | None) -> schemas.CatalogueOut:
    stmt = select(models.Product).where(models.Product.is_active.is_(True)).options(selectinload(models.Product.schemes)).order_by(models.Product.id)
    if q and q.strip():
        term = q.strip().lower()[:60]
        stmt = stmt.where(or_(func.lower(models.Product.name).contains(term, autoescape=True),
                              func.lower(models.Product.sku).contains(term, autoescape=True),
                              models.Product.name_hi.contains(term, autoescape=True)))
    out = []
    for p in db.scalars(stmt):
        unit = order_svc.effective_unit_price(db, retailer.id, p)
        scheme = next((s for s in p.schemes if s.is_active), None)
        out.append(schemas.ProductOut(
            sku=p.sku, name=p.name, name_hi=p.name_hi, packaging_label=p.packaging_label, case_size=p.case_size,
            unit_price_paise=unit, case_price_paise=pricing.case_price(unit, p.case_size), stock_cases=p.stock_cases,
            stock_status="in_stock" if p.stock_cases > 0 else "out_of_stock",
            scheme=schemas.SchemeOut.model_validate(scheme) if scheme else None))
    return schemas.CatalogueOut(products=out, price_basis=PRICE_BASIS, gst_note=GST_NOTE)


@router.get("/catalogue", response_model=schemas.CatalogueOut)
def my_catalogue(q: str | None = Query(default=None, max_length=60), retailer: models.Retailer = Depends(current_retailer),
                 db: Session = Depends(get_db)):
    return build_catalogue(db, retailer, q)


@router.get("/retailers/{retailer_id}/catalogue", response_model=schemas.CatalogueOut)
def retailer_catalogue(q: str | None = Query(default=None, max_length=60), retailer: models.Retailer = Depends(retailer_for_access),
                       db: Session = Depends(get_db)):
    return build_catalogue(db, retailer, q)


@router.get("/retailer/me")
def my_profile(retailer: models.Retailer = Depends(current_retailer), db: Session = Depends(get_db)):
    return {"retailer": schemas.RetailerBrief.model_validate(retailer), "credit": order_svc.credit_summary(db, retailer)}
