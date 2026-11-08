"""Order validation, creation and desk workflows. The backend is the single source of truth for money and stock."""
from dataclasses import dataclass, field

from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from .. import models
from ..errors import ApiError
from ..models import OrderSource, OrderStatus
from . import pricing
from .aliases import upsert_alias
from .nlp_fallback import extract_product_phrase

ALLOWED_TRANSITIONS = {
    OrderStatus.placed: {OrderStatus.confirmed, OrderStatus.rejected},
    OrderStatus.confirmed: {OrderStatus.dispatched, OrderStatus.rejected},
    OrderStatus.dispatched: set(),
    OrderStatus.rejected: set(),
}
OPEN_STATUSES = (OrderStatus.placed, OrderStatus.confirmed, OrderStatus.dispatched)


@dataclass
class ItemInput:
    sku: str
    quantity_cases: int
    ai_line_id: str | None = None


@dataclass
class PricedLine:
    sku: str
    quantity_cases: int
    product: models.Product | None = None
    calc: pricing.LineCalc | None = None
    unit_price_paise: int | None = None
    ai_line_ids: list[str] = field(default_factory=list)
    issues: list[dict] = field(default_factory=list)


def effective_unit_price(db: Session, retailer_id: int, product: models.Product) -> int:
    override = db.scalar(select(models.RetailerPrice.unit_price_paise).where(
        models.RetailerPrice.retailer_id == retailer_id, models.RetailerPrice.product_id == product.id))
    return override if override is not None else product.unit_price_paise


def stock_issue(product: models.Product, qty: int, free: int) -> dict | None:
    if product.stock_cases <= 0:
        return {"code": "OUT_OF_STOCK", "message": f"{product.name} is out of stock."}
    if qty + free > product.stock_cases:
        need = f"{qty} + {free} free" if free else str(qty)
        return {"code": "INSUFFICIENT_STOCK",
                "message": f"Only {product.stock_cases} cases of {product.name} in stock (you need {need})."}
    return None


def price_items(db: Session, retailer: models.Retailer, items: list[ItemInput]) -> list[PricedLine]:
    merged: dict[str, PricedLine] = {}
    for it in items:                                    # same SKU on two lines is one line for scheme purposes
        line = merged.setdefault(it.sku, PricedLine(sku=it.sku, quantity_cases=0))
        line.quantity_cases += it.quantity_cases
        if it.ai_line_id:
            line.ai_line_ids.append(it.ai_line_id)
    products = {p.sku: p for p in db.scalars(select(models.Product).where(models.Product.sku.in_(list(merged)))
                                             .options(selectinload(models.Product.schemes)))}
    for sku, line in merged.items():
        product = products.get(sku)
        if product is None or not product.is_active:
            line.issues.append({"code": "UNKNOWN_PRODUCT", "message": f"Product {sku} is not available."})
            continue
        line.product = product
        if not (1 <= line.quantity_cases <= pricing.MAX_CASES_PER_LINE):
            line.issues.append({"code": "INVALID_QUANTITY", "message": "Quantity must be a whole number of cases, 1 or more."})
            continue
        line.unit_price_paise = effective_unit_price(db, retailer.id, product)
        line.calc = pricing.calculate_line(line.unit_price_paise, product.case_size,
                                           [s for s in product.schemes if s.is_active], line.quantity_cases)
        issue = stock_issue(product, line.quantity_cases, line.calc.free_cases)
        if issue:
            line.issues.append(issue)
    return list(merged.values())


def totals(lines: list[PricedLine]) -> dict:
    ok = [l for l in lines if l.calc]
    return {"subtotal_paise": sum(l.calc.gross_paise for l in ok), "discount_paise": sum(l.calc.discount_paise for l in ok),
            "total_paise": sum(l.calc.line_total_paise for l in ok), "free_cases": sum(l.calc.free_cases for l in ok)}


def credit_summary(db: Session, retailer: models.Retailer) -> dict:
    open_total = db.scalar(select(func.coalesce(func.sum(models.Order.total_paise), 0)).where(
        models.Order.retailer_id == retailer.id, models.Order.status.in_(OPEN_STATUSES),
        models.Order.is_historical_seed.is_(False))) or 0
    used = retailer.outstanding_paise + open_total
    return {"credit_limit_paise": retailer.credit_limit_paise, "outstanding_paise": retailer.outstanding_paise,
            "open_orders_paise": open_total, "available_paise": max(retailer.credit_limit_paise - used, 0),
            "is_demo_data": True}


def _reserve(db: Session, product_id: int, cases: int) -> bool:
    res = db.execute(update(models.Product).where(models.Product.id == product_id, models.Product.stock_cases >= cases)
                     .values(stock_cases=models.Product.stock_cases - cases).execution_options(synchronize_session=False))
    return res.rowcount == 1


def _release(db: Session, product_id: int, cases: int) -> None:
    db.execute(update(models.Product).where(models.Product.id == product_id)
               .values(stock_cases=models.Product.stock_cases + cases).execution_options(synchronize_session=False))


def create_order(db: Session, user: models.User, retailer: models.Retailer, items: list[ItemInput], source: OrderSource,
                 idempotency_key: str, ai_parse_id: int | None, repeat_of_order_id: int | None) -> tuple[models.Order, bool]:
    """Returns (order, duplicate). A repeated idempotency key returns the original order and never creates a second one."""
    existing = db.scalar(select(models.Order).where(models.Order.retailer_id == retailer.id,
                                                    models.Order.idempotency_key == idempotency_key))
    if existing:
        return existing, True
    if not items:
        raise ApiError(422, "EMPTY_ORDER", "Add at least one product.")

    parse = None
    if source == OrderSource.ai:
        parse = db.get(models.AiParse, ai_parse_id) if ai_parse_id else None
        if parse is None or parse.retailer_id != retailer.id:
            raise ApiError(422, "INVALID_AI_PARSE", "This AI review is no longer valid. Parse your message again.")
        known = {l["line_id"] for l in parse.result}
        if any(i.ai_line_id and i.ai_line_id not in known for i in items):
            raise ApiError(422, "INVALID_AI_LINE", "An AI line reference is invalid.")
    if repeat_of_order_id is not None:
        prev = db.get(models.Order, repeat_of_order_id)
        if prev is None or prev.retailer_id != retailer.id:
            raise ApiError(422, "INVALID_REPEAT", "The order to repeat was not found.")

    lines = price_items(db, retailer, items)
    problems = [{"sku": l.sku, **i} for l in lines for i in l.issues]
    if problems:
        raise ApiError(422, "ORDER_INVALID", "Some items can't be ordered. Fix or remove them and try again.", problems)
    t = totals(lines)
    credit = credit_summary(db, retailer)
    if t["total_paise"] > credit["available_paise"]:
        raise ApiError(422, "CREDIT_LIMIT_EXCEEDED",
                       "This order is above your available credit. Reduce the order or contact the distributor.",
                       {"available_paise": credit["available_paise"], "order_total_paise": t["total_paise"]})

    order = models.Order(retailer_id=retailer.id, created_by_user_id=user.id, status=OrderStatus.placed, source=source,
                         original_message=parse.message if parse else None, ai_parse_id=parse.id if parse else None,
                         repeat_of_order_id=repeat_of_order_id, idempotency_key=idempotency_key,
                         subtotal_paise=t["subtotal_paise"], discount_paise=t["discount_paise"], total_paise=t["total_paise"])
    audit = {l["line_id"]: l for l in parse.result} if parse else {}
    try:
        db.add(order)
        db.flush()
        order.order_number = f"ORD-{order.id:06d}"
        for l in lines:
            p, c = l.product, l.calc
            a = [audit[i] for i in l.ai_line_ids]
            order.items.append(models.OrderItem(
                product_id=p.id, sku=p.sku, product_name=p.name, packaging_label=p.packaging_label, case_size=p.case_size,
                unit_price_paise=l.unit_price_paise, case_price_paise=c.case_price_paise, quantity_cases=c.quantity_cases,
                free_cases=c.free_cases, gross_paise=c.gross_paise, discount_paise=c.discount_paise,
                line_total_paise=c.line_total_paise, scheme_applied=c.scheme_applied,
                original_phrase=" + ".join(x["original_phrase"] for x in a)[:300] if a else None,
                ai_confidence=min(x["confidence"] for x in a) if a else None,
                ai_matched_sku=a[0]["sku"] if a else None, ai_alternatives=a[0]["alternatives"] if a else None,
                was_corrected=any(x["sku"] != p.sku for x in a)))
            if not _reserve(db, p.id, c.quantity_cases + c.free_cases):
                db.rollback()
                raise ApiError(422, "ORDER_INVALID", "Stock changed while ordering. Review your cart and try again.",
                               [{"sku": p.sku, "code": "INSUFFICIENT_STOCK", "message": f"{p.name} no longer has enough stock."}])
        db.commit()
    except IntegrityError:
        db.rollback()
        again = db.scalar(select(models.Order).where(models.Order.retailer_id == retailer.id,
                                                     models.Order.idempotency_key == idempotency_key))
        if again:
            return again, True
        raise
    return order, False


def _retotal(order: models.Order) -> None:
    order.subtotal_paise = sum(i.gross_paise for i in order.items)
    order.discount_paise = sum(i.discount_paise for i in order.items)
    order.total_paise = sum(i.line_total_paise for i in order.items)


def change_status(db: Session, order: models.Order, new: OrderStatus, user: models.User, reason: str | None) -> models.Order:
    if new not in ALLOWED_TRANSITIONS[order.status]:
        raise ApiError(409, "INVALID_TRANSITION", f"An order that is {order.status.value} can't be set to {new.value}.")
    if new == OrderStatus.rejected:
        if not reason or len(reason.strip()) < 3:
            raise ApiError(422, "REASON_REQUIRED", "Give a reason for rejecting this order.")
        for i in order.items:                           # give reserved stock back
            _release(db, i.product_id, i.quantity_cases + i.free_cases)
        order.rejection_reason = reason.strip()[:300]
    order.status = new
    order.reviewed_by_user_id = user.id
    db.commit()
    return order


def correct_item(db: Session, order: models.Order, item: models.OrderItem, user: models.User, sku: str | None,
                 quantity_cases: int | None, save_alias: bool) -> models.Order:
    if order.status != OrderStatus.placed:
        raise ApiError(409, "ORDER_LOCKED", "Only orders waiting for review can be corrected.")
    new_sku = sku or item.sku
    new_qty = quantity_cases if quantity_cases is not None else item.quantity_cases
    sku_changed = new_sku != item.sku
    if not sku_changed and new_qty == item.quantity_cases:
        return order
    if any(o.sku == new_sku and o.id != item.id for o in order.items):
        raise ApiError(422, "DUPLICATE_LINE", "Another line already has this product. Change that line's quantity instead.")
    product = db.scalar(select(models.Product).where(models.Product.sku == new_sku).options(selectinload(models.Product.schemes)))
    if product is None or not product.is_active:
        raise ApiError(422, "UNKNOWN_PRODUCT", "That product is not available.")
    if not (1 <= new_qty <= pricing.MAX_CASES_PER_LINE):
        raise ApiError(422, "INVALID_QUANTITY", "Quantity must be a whole number of cases, 1 or more.")

    _release(db, item.product_id, item.quantity_cases + item.free_cases)      # same transaction: rolled back on failure
    db.flush()
    db.refresh(product)
    unit = effective_unit_price(db, order.retailer_id, product) if sku_changed else item.unit_price_paise
    calc = pricing.calculate_line(unit, product.case_size, [s for s in product.schemes if s.is_active], new_qty)
    issue = stock_issue(product, new_qty, calc.free_cases)
    if issue or not _reserve(db, product.id, new_qty + calc.free_cases):
        db.rollback()
        raise ApiError(422, issue["code"] if issue else "INSUFFICIENT_STOCK",
                       issue["message"] if issue else "Not enough stock.")
    item.product_id, item.product = product.id, product
    item.sku, item.product_name, item.packaging_label, item.case_size = product.sku, product.name, product.packaging_label, product.case_size
    item.unit_price_paise, item.case_price_paise, item.quantity_cases = unit, calc.case_price_paise, calc.quantity_cases
    item.free_cases, item.gross_paise, item.discount_paise = calc.free_cases, calc.gross_paise, calc.discount_paise
    item.line_total_paise, item.scheme_applied = calc.line_total_paise, calc.scheme_applied
    if sku_changed:
        item.was_corrected = True
        if save_alias and item.original_phrase:
            phrase = extract_product_phrase(item.original_phrase)
            if phrase:
                upsert_alias(db, order.retailer_id, product, phrase, user.id)
    _retotal(order)
    order.reviewed_by_user_id = user.id
    db.commit()
    return order
