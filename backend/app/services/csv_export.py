import csv
import io
from datetime import datetime, timezone

from .. import models

COLUMNS = ["Order ID", "Order Date", "Retailer Code", "Retailer", "SKU", "Product Name", "Quantity (Cases)",
           "Free Quantity (Cases)", "Packs per Case", "Unit Price per Pack (INR)", "Price per Case (INR)",
           "Discount (INR)", "Total (INR)", "Order Status"]


def _safe(value: str) -> str:
    """Neutralise spreadsheet formula injection in text cells."""
    return "'" + value if value and value[0] in "=+-@\t\r" else value


def _inr(paise: int) -> str:
    return f"{paise // 100}.{paise % 100:02d}"


def build_csv(orders: list[models.Order]) -> str:
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\r\n")
    w.writerow(COLUMNS)
    for o in orders:
        for i in o.items:
            w.writerow([o.order_number, o.created_at.astimezone(timezone.utc).strftime("%Y-%m-%d"), _safe(o.retailer.code),
                        _safe(o.retailer.name), _safe(i.sku), _safe(i.product_name), i.quantity_cases, i.free_cases,
                        i.case_size, _inr(i.unit_price_paise), _inr(i.case_price_paise), _inr(i.discount_paise),
                        _inr(i.line_total_paise), o.status.value])
    return buf.getvalue()


def mark_exported(orders: list[models.Order]) -> None:
    now = datetime.now(timezone.utc)
    for o in orders:
        o.exported_at = now
