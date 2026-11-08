from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..deps import current_retailer, retailer_user
from ..services import ai_capture, llm

router = APIRouter(prefix="/ai", tags=["ai"])


@router.get("/status", response_model=schemas.AiStatusOut)
def status(_: models.Retailer = Depends(current_retailer)):
    provider = ai_capture.provider_factory()
    if provider is None:
        return schemas.AiStatusOut(mode="fallback", model=None, reason=llm.LLMNotConfigured.reason)
    return schemas.AiStatusOut(mode="llm", model=provider.model, reason=None)


@router.post("/parse", response_model=schemas.ParseOut)
def parse(body: schemas.ParseIn, user: models.User = Depends(retailer_user), db: Session = Depends(get_db)):
    """Interpret a free-text order. Nothing is placed: the retailer reviews, corrects and confirms."""
    p = ai_capture.parse_message(db, user.retailer, user, body.message.strip())
    return schemas.ParseOut(parse_id=p.id, mode=p.mode, fallback_reason=p.fallback_reason, model=p.model,
                            original_message=p.message, lines=p.result)
