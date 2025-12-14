from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas
from ..dependencies import get_current_user, get_db

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.post("/", response_model=schemas.TaskOut)
def create_task(
    task_in: schemas.TaskCreate,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    task = models.Task(
        user_id=user.id,
        title=task_in.title,
        description=task_in.description,
        duration_minutes=task_in.duration_minutes,
        deadline=task_in.deadline,
        task_type=task_in.task_type,
        importance=task_in.importance.lower(),
        preferred_time=task_in.preferred_time.lower(),
        energy=task_in.energy.lower(),
        status=models.TaskStatus.pending,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


@router.get("/", response_model=list[schemas.TaskOut])
def list_tasks(db: Session = Depends(get_db), user=Depends(get_current_user)):
    tasks = (
        db.query(models.Task)
        .filter(models.Task.user_id == user.id)
        .order_by(models.Task.deadline.asc())
        .all()
    )
    return tasks


@router.delete("/{task_id}")
def delete_task(task_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    task = (
        db.query(models.Task)
        .filter(models.Task.user_id == user.id, models.Task.id == task_id)
        .first()
    )
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    db.delete(task)
    db.commit()
    return {"detail": "Task deleted"}


@router.get("/{task_id}", response_model=schemas.TaskOut)
def get_task(task_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    task = (
        db.query(models.Task)
        .filter(models.Task.user_id == user.id, models.Task.id == task_id)
        .first()
    )
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task
