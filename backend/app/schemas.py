from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, StrictInt

from .models import OrderSource, OrderStatus, Role


class LoginIn(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=72)


class RetailerBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    code: str
    name: str
    city: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: str
    name: str
    role: Role
    retailer: RetailerBrief | None = None


class LoginOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class SchemeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    type: str
    description: str
    buy_qty: int
    free_qty: int
    min_cases: int
    percent_bp: int


class ProductOut(BaseModel):
    sku: str
    name: str
    name_hi: str | None
    packaging_label: str
    case_size: int
    unit_price_paise: int
    case_price_paise: int
    stock_cases: int
    stock_status: Literal["in_stock", "out_of_stock"]
    scheme: SchemeOut | None


class CatalogueOut(BaseModel):
    products: list[ProductOut]
    price_basis: str
    gst_status: Literal["unspecified"] = "unspecified"
    gst_note: str


class CreditOut(BaseModel):
    credit_limit_paise: int
    outstanding_paise: int
    open_orders_paise: int
    available_paise: int
    is_demo_data: bool


class ItemIn(BaseModel):
    sku: str = Field(min_length=1, max_length=30)
    quantity_cases: StrictInt
    ai_line_id: str | None = Field(default=None, max_length=10)


class QuoteIn(BaseModel):
    items: list[ItemIn] = Field(max_length=50)


class IssueOut(BaseModel):
    code: str
    message: str


class QuoteLineOut(BaseModel):
    sku: str
    product_name: str | None
    quantity_cases: int
    free_cases: int
    case_price_paise: int | None
    gross_paise: int | None
    discount_paise: int | None
    line_total_paise: int | None
    scheme_applied: str | None
    issues: list[IssueOut]


class QuoteOut(BaseModel):
    lines: list[QuoteLineOut]
    subtotal_paise: int
    discount_paise: int
    total_paise: int
    free_cases: int
    can_order: bool
    credit: CreditOut
    credit_ok: bool


class OrderCreateIn(BaseModel):
    items: list[ItemIn] = Field(min_length=1, max_length=50)
    source: OrderSource = OrderSource.manual
    ai_parse_id: int | None = None
    repeat_of_order_id: int | None = None
    idempotency_key: str = Field(min_length=8, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")


class OrderItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    sku: str
    product_name: str
    packaging_label: str
    case_size: int
    unit_price_paise: int
    case_price_paise: int
    quantity_cases: int
    free_cases: int
    gross_paise: int
    discount_paise: int
    line_total_paise: int
    scheme_applied: str | None
    original_phrase: str | None
    ai_confidence: float | None
    ai_matched_sku: str | None
    ai_alternatives: list | None
    was_corrected: bool


class OrderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    order_number: str
    status: OrderStatus
    source: OrderSource
    retailer: RetailerBrief
    created_at: datetime
    updated_at: datetime
    subtotal_paise: int
    discount_paise: int
    total_paise: int
    original_message: str | None
    rejection_reason: str | None
    exported_at: datetime | None
    repeat_of_order_id: int | None
    items: list[OrderItemOut]


class OrderCreatedOut(BaseModel):
    order: OrderOut
    duplicate: bool


class OrderSummaryOut(BaseModel):
    id: int
    order_number: str
    status: OrderStatus
    source: OrderSource
    retailer: RetailerBrief
    created_at: datetime
    total_paise: int
    item_count: int
    exported_at: datetime | None


class RepeatOut(BaseModel):
    order_id: int
    order_number: str
    created_at: datetime
    items: list[ItemIn]


class ParseIn(BaseModel):
    message: str = Field(min_length=1, max_length=1000)


class AlternativeOut(BaseModel):
    sku: str
    name: str


class ParsedLineOut(BaseModel):
    line_id: str
    original_phrase: str
    sku: str | None
    product_name: str | None
    quantity: int | None
    raw_quantity: float | None
    unit: Literal["case", "piece", "unknown"]
    packaging: str | None
    confidence: float
    match_source: str
    alternatives: list[AlternativeOut]
    validation_status: Literal["ok", "needs_clarification", "out_of_stock", "insufficient_stock", "invalid_quantity"]
    clarification: Literal["product", "unit", "quantity"] | None
    messages: list[str]
    stock_cases: int | None
    free_cases: int | None
    line_total_paise: int | None


class ParseOut(BaseModel):
    parse_id: int
    mode: Literal["llm", "fallback"]
    fallback_reason: str | None
    model: str | None
    original_message: str
    lines: list[ParsedLineOut]


class AiStatusOut(BaseModel):
    mode: Literal["llm", "fallback"]
    model: str | None
    reason: str | None


class StatusChangeIn(BaseModel):
    status: OrderStatus
    reason: str | None = Field(default=None, max_length=300)


class ItemCorrectionIn(BaseModel):
    sku: str | None = Field(default=None, max_length=30)
    quantity_cases: StrictInt | None = None
    save_alias: bool = True


class AliasIn(BaseModel):
    alias_text: str = Field(min_length=1, max_length=120)
    sku: str = Field(min_length=1, max_length=30)


class AliasOut(BaseModel):
    id: int
    alias_text: str
    sku: str
    product_name: str
    created_at: datetime


class ExportIn(BaseModel):
    order_ids: list[int] | None = Field(default=None, max_length=500)
    include_exported: bool = False
