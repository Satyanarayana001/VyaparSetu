from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models
from ..errors import ApiError
from .nlp_fallback import normalize_alias


def upsert_alias(db: Session, retailer_id: int, product: models.Product, text: str, user_id: int | None) -> models.RetailerAlias:
    """Retailer-specific alias. Saving the same words again re-points them to the new product."""
    norm = normalize_alias(text)
    if not norm or len(norm) > 120:
        raise ApiError(422, "INVALID_ALIAS", "Alias must contain 1 to 120 characters of product words.")
    row = db.scalar(select(models.RetailerAlias).where(models.RetailerAlias.retailer_id == retailer_id,
                                                       models.RetailerAlias.alias_text == norm))
    if row:
        row.product_id, row.product = product.id, product
        row.created_by_user_id = user_id
    else:
        row = models.RetailerAlias(retailer_id=retailer_id, product_id=product.id, product=product, alias_text=norm,
                                   created_by_user_id=user_id)
        db.add(row)
    db.flush()
    return row
