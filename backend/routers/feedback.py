from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import models, schemas
from ..dependencies import get_current_user, get_db

router = APIRouter(prefix="/feedback", tags=["feedback"])


@router.post("/", response_model=schemas.FeedbackOut)
def create_feedback(fb_in: schemas.FeedbackCreate, db: Session = Depends(get_db), user=Depends(get_current_user)):
    fb = models.FeedbackLog(
        user_id=user.id,
        task_id=fb_in.task_id,
        outcome=fb_in.outcome,
        note=fb_in.note,
    )
    db.add(fb)
    db.commit()
    db.refresh(fb)
    return fb


@router.get("/", response_model=list[schemas.FeedbackOut])
def list_feedback(db: Session = Depends(get_db), user=Depends(get_current_user)):
    return (
        db.query(models.FeedbackLog)
        .filter(models.FeedbackLog.user_id == user.id)
        .order_by(models.FeedbackLog.created_at.desc())
        .all()
    )
