from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import models, schemas
from ..dependencies import get_current_user, get_db

router = APIRouter(prefix="/notes", tags=["notes"])


@router.get("/", response_model=list[schemas.NoteOut])
def list_notes(db: Session = Depends(get_db), user=Depends(get_current_user)):
    return (
        db.query(models.Note)
        .filter(models.Note.user_id == user.id)
        .order_by(models.Note.created_at.desc())
        .all()
    )


@router.post("/", response_model=schemas.NoteOut)
def create_note(note_in: schemas.NoteCreate, db: Session = Depends(get_db), user=Depends(get_current_user)):
    note = models.Note(user_id=user.id, title=note_in.title, body=note_in.body)
    db.add(note)
    db.commit()
    db.refresh(note)
    return note
