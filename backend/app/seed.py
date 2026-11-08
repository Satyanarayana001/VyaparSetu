"""Synthetic demo data. All names, e-mails and balances are fictional. Product data is exactly as supplied in the client brief."""
import argparse
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from . import models
from .database import Base, SessionLocal, engine
from .models import OrderSource, OrderStatus, Role, SchemeType, utcnow
from .security import hash_password
from .services import pricing

# DEMO credentials (documented in deployment.md). Never use these outside a demo.
DEMO_RETAILER_PASSWORD = "Retailer@123"
DEMO_DESK_PASSWORD = "Desk@12345"
DEMO_SALESMAN_PASSWORD = "Salesman@123"


def seed(db: Session) -> None:
    if db.scalar(select(models.User.id).limit(1)) is not None:
        return
    biscuit = models.Product(sku="SKU-BS-075", name="Glucose biscuit 75 g", name_hi="ग्लूकोज बिस्कुट 75 ग्राम",
                             packaging_label="Case of 96", case_size=96, unit_price_paise=810, stock_cases=340)
    detergent = models.Product(sku="SKU-DT-1KG", name="Detergent powder 1 kg", name_hi="डिटर्जेंट पाउडर 1 किग्रा",
                               packaging_label="Case of 20", case_size=20, unit_price_paise=10150, stock_cases=85)
    tea = models.Product(sku="SKU-TE-250", name="Tea leaf 250 g", name_hi="चाय पत्ती 250 ग्राम",
                         packaging_label="Case of 40", case_size=40, unit_price_paise=11800, stock_cases=0)
    biscuit.schemes.append(models.Scheme(type=SchemeType.free_goods, description="Buy 10 cases, get 1 free", buy_qty=10, free_qty=1))
    detergent.schemes.append(models.Scheme(type=SchemeType.percent_discount, description="3% discount on 5 or more cases",
                                           min_cases=5, percent_bp=300))
    db.add_all([biscuit, detergent, tea])

    sm = models.Salesman(code="SM01", name="Demo Salesman")
    r1 = models.Retailer(code="R001", name="Sharma Kirana Store (demo)", salesman=sm,
                         credit_limit_paise=75_000_00, outstanding_paise=18_500_00)
    r2 = models.Retailer(code="R002", name="Narmada General Store (demo)", salesman=sm,
                         credit_limit_paise=30_000_00, outstanding_paise=24_000_00)   # tight limit: demonstrates a credit hold
    db.add_all([sm, r1, r2])
    db.flush()
    db.add_all([
        models.User(email="retailer1@demo.test", password_hash=hash_password(DEMO_RETAILER_PASSWORD), name="Sharma (demo)", role=Role.retailer, retailer_id=r1.id),
        models.User(email="retailer2@demo.test", password_hash=hash_password(DEMO_RETAILER_PASSWORD), name="Narmada (demo)", role=Role.retailer, retailer_id=r2.id),
        models.User(email="desk@demo.test", password_hash=hash_password(DEMO_DESK_PASSWORD), name="Order Desk (demo)", role=Role.desk),
        models.User(email="salesman@demo.test", password_hash=hash_password(DEMO_SALESMAN_PASSWORD), name="Demo Salesman", role=Role.salesman, salesman_id=sm.id),
    ])
    db.flush()
    creator = {u.retailer_id: u for u in db.scalars(select(models.User).where(models.User.role == Role.retailer))}

    # One historical (already dispatched) order per retailer so "repeat last order" works. Stock is NOT touched.
    def history(retailer, lines, days_ago):
        o = models.Order(retailer_id=retailer.id, created_by_user_id=creator[retailer.id].id, status=OrderStatus.dispatched,
                         source=OrderSource.manual, idempotency_key=f"seed-{retailer.code}", is_historical_seed=True,
                         created_at=utcnow() - timedelta(days=days_ago))
        db.add(o)
        db.flush()
        o.order_number = f"ORD-{o.id:06d}"
        for p, qty in lines:
            c = pricing.calculate_line(p.unit_price_paise, p.case_size, p.schemes, qty)
            o.items.append(models.OrderItem(product_id=p.id, sku=p.sku, product_name=p.name, packaging_label=p.packaging_label,
                                            case_size=p.case_size, unit_price_paise=p.unit_price_paise, case_price_paise=c.case_price_paise,
                                            quantity_cases=qty, free_cases=c.free_cases, gross_paise=c.gross_paise,
                                            discount_paise=c.discount_paise, line_total_paise=c.line_total_paise, scheme_applied=c.scheme_applied))
        o.subtotal_paise = sum(i.gross_paise for i in o.items)
        o.discount_paise = sum(i.discount_paise for i in o.items)
        o.total_paise = sum(i.line_total_paise for i in o.items)

    history(r1, [(biscuit, 10), (detergent, 5), (tea, 2)], 12)   # tea is out of stock now: shows the repeat-order warning
    history(r2, [(biscuit, 3), (detergent, 2)], 20)
    db.commit()


def reset() -> None:
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        seed(db)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Seed (or reset) the demo database")
    ap.add_argument("--reset", action="store_true", help="drop all tables first")
    args = ap.parse_args()
    if args.reset:
        reset()
    else:
        Base.metadata.create_all(engine)
        with SessionLocal() as db:
            seed(db)
    print("Database ready.")
