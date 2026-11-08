"""Orchestrates AI order capture: LLM (if configured) -> rule-based fallback -> shared validation."""
import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models
from ..config import settings
from . import llm, pricing
from .ai_types import RawLine
from .nlp_fallback import extract_product_phrase, normalize_alias, parse_with_rules

log = logging.getLogger("app.ai")
MIN_CONFIDENCE = 0.7      # below this a line must be confirmed/corrected by a human
MAX_MESSAGE_CHARS = 1000

# Overridable in tests
provider_factory = lambda: llm.build_provider(settings)  # noqa: E731


def _catalogue_text(products, aliases) -> str:
    alias_by_sku: dict[str, list[str]] = {}
    for a, sku in aliases:
        alias_by_sku.setdefault(sku, []).append(a)
    rows = []
    for p in products:
        extra = f" | this retailer's own words: {', '.join(alias_by_sku[p.sku])}" if p.sku in alias_by_sku else ""
        rows.append(f"- {p.sku}: {p.name}, {p.packaging_label}{extra}")
    return "\n".join(rows)


def _apply_aliases(raw: list[RawLine], aliases: list[tuple[str, str]], products) -> None:
    """Retailer aliases always win over the model's guess (controlled, per-retailer learning)."""
    skus = [p.sku for p in products]
    for line in raw:
        phrase = set(extract_product_phrase(line.original_phrase).split())
        best = None
        for text, sku in aliases:
            a = set(normalize_alias(text).split())
            if a and a <= phrase and (best is None or len(a) > best[0]):
                best = (len(a), sku)
        if best and best[1] in skus:
            line.sku, line.confidence, line.source, line.ambiguous = best[1], 0.98, "alias", False
            line.alternative_skus = [s for s in skus if s != best[1]][:2]


def _from_llm(llm_lines: list[llm.LLMLine], products) -> list[RawLine]:
    valid = {p.sku for p in products}
    out = []
    for l in llm_lines:
        sku = l.sku if l.sku in valid else None          # never trust an SKU that isn't in the catalogue
        alts = [s for s in l.alternative_skus if s in valid and s != sku]
        out.append(RawLine(original_phrase=l.original_phrase.strip(), raw_quantity=l.quantity, unit=l.unit, sku=sku,
                           confidence=l.confidence if sku else 0.0, alternative_skus=alts, source="llm"))
    return out


def _finalize(raw: list[RawLine], products) -> list[dict]:
    by_sku = {p.sku: p for p in products}
    order = [p.sku for p in products]
    lines = []
    for n, r in enumerate(raw, start=1):
        product = by_sku.get(r.sku) if r.sku else None
        alts = [s for s in r.alternative_skus if s in by_sku and s != r.sku]
        for s in order:                                   # pad to two alternatives
            if len(alts) >= (2 if product else 3):
                break
            if s != r.sku and s not in alts:
                alts.append(s)
        alts = alts[: (2 if product else 3)]
        status, clar, msgs = "ok", None, []
        qty = None
        raw_q = r.raw_quantity

        if product is None or r.confidence < MIN_CONFIDENCE or r.ambiguous:
            status, clar = "needs_clarification", "product"
            msgs.append("We couldn't tell which product this is. Choose the right one." if product is None
                        else "Not sure about this match. Please check the product.")
        if r.unit == "case" and raw_q is not None:
            if raw_q != int(raw_q) or raw_q < 1 or raw_q > pricing.MAX_CASES_PER_LINE:
                if status == "ok":
                    status, clar = "invalid_quantity", "quantity"
                msgs.append("Quantity must be a whole number of cases (1 or more).")
            else:
                qty = int(raw_q)
        elif r.unit == "piece":
            if status == "ok":
                status, clar = "needs_clarification", "unit"
            size = f" ({product.case_size} packs per case)" if product else ""
            msgs.append(f"You wrote {_fmt(raw_q)} packs. Orders are placed in whole cases{size}. Enter the number of cases.")
        elif r.unit == "unknown":
            if status == "ok":
                status, clar = "needs_clarification", "unit" if raw_q is not None else "quantity"
            if raw_q is None:
                msgs.append("No quantity found. Enter the number of cases.")
            else:
                msgs.append(f"Is {_fmt(raw_q)} cases or packs? Orders are placed in cases, so please confirm.")

        if qty is None and status == "ok":
            status, clar = "needs_clarification", "quantity"
            msgs.append("No quantity found. Enter the number of cases.")

        stock = product.stock_cases if product else None
        free = total = None
        if status == "ok" and product and qty is not None:
            calc = pricing.calculate_line(product.unit_price_paise, product.case_size,
                                          [s for s in product.schemes if s.is_active], qty)
            free, total = calc.free_cases, calc.line_total_paise
            if product.stock_cases <= 0:
                status = "out_of_stock"
                msgs.append("Out of stock. Remove this line or pick another product.")
            elif qty + calc.free_cases > product.stock_cases:
                status = "insufficient_stock"
                msgs.append(f"Only {product.stock_cases} cases in stock"
                            + (f" ({qty} + {calc.free_cases} free needed)." if calc.free_cases else "."))
        lines.append({
            "line_id": f"l{n}", "original_phrase": r.original_phrase, "sku": r.sku if product else None,
            "product_name": product.name if product else None, "quantity": qty, "raw_quantity": raw_q, "unit": r.unit,
            "packaging": product.packaging_label if product else None, "confidence": round(r.confidence, 2),
            "match_source": r.source, "alternatives": [{"sku": s, "name": by_sku[s].name} for s in alts],
            "validation_status": status, "clarification": clar, "messages": msgs, "stock_cases": stock,
            "free_cases": free, "line_total_paise": total,
        })
    return lines


def _fmt(v) -> str:
    return str(int(v)) if v is not None and float(v) == int(v) else str(v)


def parse_message(db: Session, retailer: models.Retailer, user: models.User, message: str) -> models.AiParse:
    products = list(db.scalars(select(models.Product).where(models.Product.is_active.is_(True)).order_by(models.Product.id)))
    alias_rows = db.execute(select(models.RetailerAlias.alias_text, models.Product.sku)
                            .join(models.Product, models.Product.id == models.RetailerAlias.product_id)
                            .where(models.RetailerAlias.retailer_id == retailer.id)).all()
    aliases = [(a, s) for a, s in alias_rows]

    mode, reason, model_name, raw = "fallback", None, None, None
    provider = provider_factory()
    if provider is None:
        reason = llm.LLMNotConfigured.reason
    else:
        try:
            llm_lines = llm.extract_lines(provider, message, _catalogue_text(products, aliases))
            raw, mode, model_name = _from_llm(llm_lines, products), "llm", provider.model
            _apply_aliases(raw, aliases, products)
        except llm.LLMError as e:
            reason = e.reason
            log.warning("LLM failed (%s); using rule-based fallback", type(e).__name__)
        except Exception:  # defensive: never let a provider bug break ordering
            reason = "LLM error"
            log.exception("Unexpected LLM failure; using rule-based fallback")
    if raw is None:
        raw = parse_with_rules(message, products, aliases)
    parse = models.AiParse(retailer_id=retailer.id, user_id=user.id, message=message, mode=mode, fallback_reason=reason,
                           model=model_name, result=_finalize(raw, products))
    db.add(parse)
    db.commit()
    return parse
