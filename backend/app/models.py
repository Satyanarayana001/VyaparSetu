"""Relational data model. All money is stored as integer paise to avoid floating-point error."""
import enum
from datetime import datetime, timezone

from sqlalchemy import (JSON, Boolean, CheckConstraint, DateTime, Enum, ForeignKey, Index, Integer, String, Text,
                        UniqueConstraint)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import TypeDecorator

from .database import Base


class UtcDateTime(TypeDecorator):
    impl = DateTime
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc).replace(tzinfo=None)

    def process_result_value(self, value, dialect):
        return value.replace(tzinfo=timezone.utc) if value is not None else None


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _enum(e):
    return Enum(e, native_enum=False, create_constraint=True, values_callable=lambda x: [m.value for m in x])


class Role(str, enum.Enum):
    retailer = "retailer"
    desk = "desk"
    salesman = "salesman"


class OrderStatus(str, enum.Enum):
    placed = "placed"          # retailer confirmed; waiting for the order desk
    confirmed = "confirmed"    # order desk accepted; eligible for Tally CSV export
    dispatched = "dispatched"
    rejected = "rejected"


class OrderSource(str, enum.Enum):
    manual = "manual"
    ai = "ai"
    repeat = "repeat"


class SchemeType(str, enum.Enum):
    free_goods = "free_goods"              # buy N cases, get M free (completed groups only)
    percent_discount = "percent_discount"  # P% off the line when >= min cases


class Salesman(Base):
    __tablename__ = "salesmen"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(20), unique=True)
    name: Mapped[str] = mapped_column(String(100))
    retailers: Mapped[list["Retailer"]] = relationship(back_populates="salesman")


class Retailer(Base):
    __tablename__ = "retailers"
    __table_args__ = (CheckConstraint("credit_limit_paise >= 0"), CheckConstraint("outstanding_paise >= 0"))
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(20), unique=True)
    name: Mapped[str] = mapped_column(String(150))
    city: Mapped[str] = mapped_column(String(80), default="Jabalpur")
    salesman_id: Mapped[int | None] = mapped_column(ForeignKey("salesmen.id"))
    # DEMO DATA ONLY: no real credit/banking integration exists.
    credit_limit_paise: Mapped[int] = mapped_column(Integer, default=0)
    outstanding_paise: Mapped[int] = mapped_column(Integer, default=0)
    salesman: Mapped[Salesman | None] = relationship(back_populates="retailers")


class User(Base):
    __tablename__ = "users"
    __table_args__ = (CheckConstraint("(role = 'retailer') = (retailer_id IS NOT NULL)", name="retailer_role_has_retailer"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(254), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(100))
    name: Mapped[str] = mapped_column(String(100))
    role: Mapped[Role] = mapped_column(_enum(Role))
    retailer_id: Mapped[int | None] = mapped_column(ForeignKey("retailers.id"))
    salesman_id: Mapped[int | None] = mapped_column(ForeignKey("salesmen.id"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    retailer: Mapped[Retailer | None] = relationship()


class Product(Base):
    __tablename__ = "products"
    __table_args__ = (CheckConstraint("case_size > 0"), CheckConstraint("unit_price_paise >= 0"),
                      CheckConstraint("stock_cases >= 0"))
    id: Mapped[int] = mapped_column(primary_key=True)
    sku: Mapped[str] = mapped_column(String(30), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(150))
    name_hi: Mapped[str | None] = mapped_column(String(150))
    packaging_label: Mapped[str] = mapped_column(String(50))
    case_size: Mapped[int] = mapped_column(Integer)                 # packs per case
    unit_price_paise: Mapped[int] = mapped_column(Integer)          # dealer price PER PACK (see TDD assumption A1)
    stock_cases: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    schemes: Mapped[list["Scheme"]] = relationship(back_populates="product", cascade="all, delete-orphan")


class Scheme(Base):
    __tablename__ = "schemes"
    __table_args__ = (CheckConstraint("buy_qty >= 0 AND free_qty >= 0 AND min_cases >= 0 AND percent_bp >= 0 AND percent_bp <= 10000"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    type: Mapped[SchemeType] = mapped_column(_enum(SchemeType))
    description: Mapped[str] = mapped_column(String(200))
    buy_qty: Mapped[int] = mapped_column(Integer, default=0)
    free_qty: Mapped[int] = mapped_column(Integer, default=0)
    min_cases: Mapped[int] = mapped_column(Integer, default=0)
    percent_bp: Mapped[int] = mapped_column(Integer, default=0)     # basis points: 300 = 3%
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    product: Mapped[Product] = relationship(back_populates="schemes")


class RetailerPrice(Base):
    """Optional retailer-specific price override. Empty in the seed data (client supplied one dealer price)."""
    __tablename__ = "retailer_prices"
    __table_args__ = (UniqueConstraint("retailer_id", "product_id"), CheckConstraint("unit_price_paise >= 0"))
    id: Mapped[int] = mapped_column(primary_key=True)
    retailer_id: Mapped[int] = mapped_column(ForeignKey("retailers.id"))
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    unit_price_paise: Mapped[int] = mapped_column(Integer)


class RetailerAlias(Base):
    __tablename__ = "retailer_aliases"
    __table_args__ = (UniqueConstraint("retailer_id", "alias_text"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    retailer_id: Mapped[int] = mapped_column(ForeignKey("retailers.id"), index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    alias_text: Mapped[str] = mapped_column(String(120))
    created_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(UtcDateTime, default=utcnow)
    product: Mapped[Product] = relationship()


class AiParse(Base):
    """Server-side record of an AI interpretation. Orders reference it, so the stored audit trail can't be forged by the client."""
    __tablename__ = "ai_parses"
    id: Mapped[int] = mapped_column(primary_key=True)
    retailer_id: Mapped[int] = mapped_column(ForeignKey("retailers.id"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    message: Mapped[str] = mapped_column(Text)
    mode: Mapped[str] = mapped_column(String(20))          # "llm" | "fallback"
    fallback_reason: Mapped[str | None] = mapped_column(String(200))
    model: Mapped[str | None] = mapped_column(String(100))
    result: Mapped[list] = mapped_column(JSON)             # list of parsed line dicts
    created_at: Mapped[datetime] = mapped_column(UtcDateTime, default=utcnow)


class Order(Base):
    __tablename__ = "orders"
    __table_args__ = (UniqueConstraint("retailer_id", "idempotency_key"),
                      CheckConstraint("subtotal_paise >= 0 AND discount_paise >= 0 AND total_paise >= 0"),
                      Index("ix_orders_status_created", "status", "created_at"))
    id: Mapped[int] = mapped_column(primary_key=True)
    order_number: Mapped[str | None] = mapped_column(String(20), unique=True)
    retailer_id: Mapped[int] = mapped_column(ForeignKey("retailers.id"), index=True)
    created_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    status: Mapped[OrderStatus] = mapped_column(_enum(OrderStatus), default=OrderStatus.placed)
    source: Mapped[OrderSource] = mapped_column(_enum(OrderSource), default=OrderSource.manual)
    original_message: Mapped[str | None] = mapped_column(Text)
    ai_parse_id: Mapped[int | None] = mapped_column(ForeignKey("ai_parses.id"))
    repeat_of_order_id: Mapped[int | None] = mapped_column(ForeignKey("orders.id"))
    idempotency_key: Mapped[str] = mapped_column(String(64))
    subtotal_paise: Mapped[int] = mapped_column(Integer, default=0)
    discount_paise: Mapped[int] = mapped_column(Integer, default=0)
    total_paise: Mapped[int] = mapped_column(Integer, default=0)
    rejection_reason: Mapped[str | None] = mapped_column(String(300))
    reviewed_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    exported_at: Mapped[datetime | None] = mapped_column(UtcDateTime)
    is_historical_seed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(UtcDateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(UtcDateTime, default=utcnow, onupdate=utcnow)
    retailer: Mapped[Retailer] = relationship()
    ai_parse: Mapped[AiParse | None] = relationship()
    items: Mapped[list["OrderItem"]] = relationship(back_populates="order", cascade="all, delete-orphan",
                                                    order_by="OrderItem.id")


class OrderItem(Base):
    __tablename__ = "order_items"
    __table_args__ = (CheckConstraint("quantity_cases > 0"), CheckConstraint("free_cases >= 0"),
                      CheckConstraint("discount_paise >= 0 AND line_total_paise >= 0 AND gross_paise >= 0"))
    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    # Snapshots, so later catalogue changes never rewrite history
    sku: Mapped[str] = mapped_column(String(30))
    product_name: Mapped[str] = mapped_column(String(150))
    packaging_label: Mapped[str] = mapped_column(String(50))
    case_size: Mapped[int] = mapped_column(Integer)
    unit_price_paise: Mapped[int] = mapped_column(Integer)
    case_price_paise: Mapped[int] = mapped_column(Integer)
    quantity_cases: Mapped[int] = mapped_column(Integer)
    free_cases: Mapped[int] = mapped_column(Integer, default=0)
    gross_paise: Mapped[int] = mapped_column(Integer)
    discount_paise: Mapped[int] = mapped_column(Integer, default=0)
    line_total_paise: Mapped[int] = mapped_column(Integer)
    scheme_applied: Mapped[str | None] = mapped_column(String(200))
    # AI audit trail (copied server-side from the AiParse record, never trusted from the client)
    original_phrase: Mapped[str | None] = mapped_column(String(300))
    ai_confidence: Mapped[float | None] = mapped_column()
    ai_matched_sku: Mapped[str | None] = mapped_column(String(30))
    ai_alternatives: Mapped[list | None] = mapped_column(JSON)
    was_corrected: Mapped[bool] = mapped_column(Boolean, default=False)
    order: Mapped[Order] = relationship(back_populates="items")
    product: Mapped[Product] = relationship()
