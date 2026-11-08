"""Deterministic pricing and scheme engine. Pure functions, integer paise, no floats.

Assumptions (also in the TDD):
  A1  Dealer price is per PACK (the sellable piece). Case price = dealer price x case size.
  A2  Biscuit scheme "buy 10 cases, get 1 free": free cases = floor(qty / 10) x 1 (completed groups only).
      Free cases are drawn from the same stock and are not charged.
  A3  Detergent scheme "3% off for 5+ cases": 3% of the line gross, rounded half-up to the paisa.
  A4  No GST is added or removed: the brief does not specify GST treatment.
"""
from dataclasses import dataclass
from typing import Iterable, Protocol

MAX_CASES_PER_LINE = 10_000


class SchemeLike(Protocol):
    type: object
    description: str
    buy_qty: int
    free_qty: int
    min_cases: int
    percent_bp: int


@dataclass(frozen=True)
class LineCalc:
    quantity_cases: int
    free_cases: int
    case_price_paise: int
    gross_paise: int
    discount_paise: int
    line_total_paise: int
    scheme_applied: str | None


def case_price(unit_price_paise: int, case_size: int) -> int:
    return unit_price_paise * case_size


def percent_of(amount_paise: int, percent_bp: int) -> int:
    """amount * bp / 10000, rounded half-up, integer arithmetic only."""
    return (amount_paise * percent_bp * 2 + 10_000) // 20_000


def calculate_line(unit_price_paise: int, case_size: int, schemes: Iterable[SchemeLike], quantity_cases: int) -> LineCalc:
    if not isinstance(quantity_cases, int) or isinstance(quantity_cases, bool) or not (1 <= quantity_cases <= MAX_CASES_PER_LINE):
        raise ValueError("quantity_cases must be an integer between 1 and %d" % MAX_CASES_PER_LINE)
    cp = case_price(unit_price_paise, case_size)
    gross = cp * quantity_cases
    free = 0
    discount = 0
    applied: list[str] = []
    for s in schemes:
        kind = getattr(s.type, "value", s.type)
        if kind == "free_goods" and s.buy_qty > 0 and s.free_qty > 0:
            groups = quantity_cases // s.buy_qty
            if groups:
                free += groups * s.free_qty
                applied.append(f"{s.description} ({groups} x {s.free_qty} free)")
        elif kind == "percent_discount" and s.percent_bp > 0 and quantity_cases >= s.min_cases:
            d = percent_of(gross, s.percent_bp)
            discount += d
            applied.append(s.description)
    discount = min(discount, gross)
    return LineCalc(quantity_cases, free, cp, gross, discount, gross - discount, "; ".join(applied) or None)
