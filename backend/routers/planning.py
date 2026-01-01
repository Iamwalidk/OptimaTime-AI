from datetime import datetime, date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas
from ..dependencies import get_current_user, get_db
from ..ml import generate_schedule

router = APIRouter(prefix="/planning", tags=["planning"])


def _parse_hour_str(val: str, fallback: int) -> int:
    try:
        hour = int(val.split(":")[0])
        if 0 <= hour <= 23:
            return hour
    except Exception:
        pass
    return fallback


def _is_workday(plan_date, mask: str | None) -> bool:
    if not mask or len(mask) < 7:
        return True
    idx = plan_date.weekday()
    try:
        return mask[idx] == "1"
    except Exception:
        return True


@router.post("/plan", response_model=schemas.PlanOut)
def generate_plan(plan_req: schemas.PlanRequest, db: Session = Depends(get_db), user=Depends(get_current_user)):
    start_of_day = datetime.combine(plan_req.date, datetime.min.time())

    settings = db.query(models.UserSettings).filter(models.UserSettings.user_id == user.id).first()
    if not settings:
        settings = models.UserSettings(user_id=user.id)
        db.add(settings)
        db.commit()
        db.refresh(settings)
    start_hour = _parse_hour_str(settings.working_hours_start, 8)
    end_hour = _parse_hour_str(settings.working_hours_end, 22)
    if end_hour <= start_hour:
        end_hour = min(start_hour + 12, 23)
    if not _is_workday(plan_req.date, settings.work_days_mask):
        raise HTTPException(
            status_code=400,
            detail="Selected date is outside your working days. Update your working hours in settings.",
        )

    tasks = (
        db.query(models.Task)
        .filter(
            models.Task.user_id == user.id,
            models.Task.deadline >= start_of_day,
            models.Task.status.in_([models.TaskStatus.pending, models.TaskStatus.unscheduled]),
        )
        .all()
    )

    if not tasks:
        raise HTTPException(status_code=400, detail="No pending tasks to plan for this date")

    feedback = (
        db.query(models.FeedbackLog)
        .filter(models.FeedbackLog.user_id == user.id)
        .order_by(models.FeedbackLog.created_at.desc())
        .all()
    )

    task_dicts = [
        dict(
            id=t.id,
            title=t.title,
            duration_minutes=t.duration_minutes,
            deadline=t.deadline,
            task_type=t.task_type,
            importance=t.importance,
            preferred_time=t.preferred_time,
            energy=t.energy,
        )
        for t in tasks
    ]

    scheduled, unscheduled, model_confidence = generate_schedule(
        tasks=task_dicts,
        user_profile=user.profile.value,
        plan_date=plan_req.date,
        feedback=feedback,
        start_hour=start_hour,
        end_hour=end_hour,
    )

    scheduled_ids = {s["task_id"] for s in scheduled}
    unscheduled_ids = {u["id"] for u in unscheduled}

    plan_datetime = datetime.combine(plan_req.date, datetime.min.time())
    existing_plan = (
        db.query(models.Plan)
        .filter(models.Plan.user_id == user.id, models.Plan.plan_date == plan_datetime)
        .first()
    )
    if existing_plan:
        db.delete(existing_plan)
        db.flush()

    plan = models.Plan(
        user_id=user.id,
        plan_date=plan_datetime,
        model_version="priority_model_v1",
        status=models.PlanStatus.generated,
        summary=f"{len(scheduled)} scheduled, {len(unscheduled)} unscheduled",
    )
    db.add(plan)
    db.flush()

    for t in tasks:
        if t.id in scheduled_ids:
            t.status = models.TaskStatus.scheduled
        elif t.id in unscheduled_ids:
            t.status = models.TaskStatus.unscheduled

    plan_items_map = []
    for idx, s in enumerate(scheduled):
        item = models.PlanItem(
            plan_id=plan.id,
            task_id=s["task_id"],
            start_datetime=datetime.fromisoformat(s["start"]),
            end_datetime=datetime.fromisoformat(s["end"]),
            explanation=s.get("explanation"),
            position=idx,
        )
        db.add(item)
        db.flush()
        plan_items_map.append((s, item.id))

    db.commit()

    unscheduled_schema = []
    for u in unscheduled:
        t = db.query(models.Task).filter(models.Task.id == u["id"]).first()
        if t:
            unscheduled_schema.append(t)

    unscheduled_reasons = {u["id"]: u.get("reason") for u in unscheduled}
    unscheduled_out = []
    for t in unscheduled_schema:
        unscheduled_out.append(
            schemas.UnscheduledTaskOut.from_orm(t).copy(
                update={"reason": unscheduled_reasons.get(t.id)}
            )
        )

    scheduled_out = [
        schemas.ScheduledTaskOut(**s, plan_item_id=item_id) for s, item_id in plan_items_map
    ]

    return schemas.PlanOut(
        model_version=plan.model_version,
        model_confidence=model_confidence,
        scheduled=scheduled_out,
        unscheduled=unscheduled_out,
    )


@router.get("/plan", response_model=schemas.PlanOut)
def get_plan(plan_date: date, db: Session = Depends(get_db), user=Depends(get_current_user)):
    plan_datetime = datetime.combine(plan_date, datetime.min.time())
    plan = (
        db.query(models.Plan)
        .filter(models.Plan.user_id == user.id, models.Plan.plan_date == plan_datetime)
        .first()
    )
    if not plan:
        raise HTTPException(status_code=404, detail="No plan found for this date")

    items = (
        db.query(models.PlanItem)
        .filter(models.PlanItem.plan_id == plan.id)
        .order_by(models.PlanItem.position.asc())
        .all()
    )
    scheduled = [
        schemas.ScheduledTaskOut(
            plan_item_id=i.id,
            task_id=i.task_id,
            title=i.task.title if i.task else "",
            start=i.start_datetime,
            end=i.end_datetime,
            explanation=i.explanation or "",
            priority=0.0,
            llm_explanation=None,
        )
        for i in items
    ]

    start_of_day = plan_datetime
    unscheduled_tasks = (
        db.query(models.Task)
        .filter(
            models.Task.user_id == user.id,
            models.Task.status == models.TaskStatus.unscheduled,
            models.Task.deadline >= start_of_day,
        )
        .all()
    )
    unscheduled = [
        schemas.UnscheduledTaskOut.from_orm(t).copy(update={"reason": "Not placed in the last plan"})
        for t in unscheduled_tasks
    ]

    return schemas.PlanOut(
        model_version=plan.model_version,
        model_confidence=None,
        scheduled=scheduled,
        unscheduled=unscheduled,
    )


@router.get("/calendar")
def calendar(
    start_date: date,
    end_date: date,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    plans = (
        db.query(models.Plan)
        .filter(
            models.Plan.user_id == user.id,
            models.Plan.plan_date >= datetime.combine(start_date, datetime.min.time()),
            models.Plan.plan_date <= datetime.combine(end_date, datetime.min.time()),
        )
        .order_by(models.Plan.plan_date.asc())
        .all()
    )

    items = (
        db.query(models.PlanItem)
        .join(models.Plan, models.PlanItem.plan_id == models.Plan.id)
        .filter(
            models.Plan.user_id == user.id,
            models.Plan.plan_date >= datetime.combine(start_date, datetime.min.time()),
            models.Plan.plan_date <= datetime.combine(end_date, datetime.min.time()),
        )
        .all()
    )
    items_by_plan = {}
    for it in items:
        items_by_plan.setdefault(it.plan_id, []).append(it)

    calendar = []
    for plan in plans:
        day_items = items_by_plan.get(plan.id, [])
        calendar.append(
            {
                "plan_date": plan.plan_date.date().isoformat(),
                "model_version": plan.model_version,
                "summary": plan.summary,
                "scheduled": [
                    {
                        "plan_item_id": it.id,
                        "task_id": it.task_id,
                        "title": it.task.title if it.task else "",
                        "start": it.start_datetime.isoformat(),
                        "end": it.end_datetime.isoformat(),
                        "explanation": it.explanation or "",
                        "llm_explanation": None,
                        "priority": 0.0,
                    }
                    for it in sorted(day_items, key=lambda i: i.position)
                ],
            }
        )
    return {"days": calendar}


@router.patch("/item/{item_id}", response_model=schemas.ScheduledTaskOut)
def update_plan_item(
    item_id: int,
    start: datetime,
    end: datetime,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    item = (
        db.query(models.PlanItem)
        .join(models.Plan, models.PlanItem.plan_id == models.Plan.id)
        .filter(models.PlanItem.id == item_id, models.Plan.user_id == user.id)
        .first()
    )
    if not item:
        raise HTTPException(status_code=404, detail="Plan item not found")

    original_start = item.start_datetime
    new_plan_date = start.date()

    # move to another plan if date changed
    if item.plan.plan_date.date() != new_plan_date:
        new_plan_datetime = datetime.combine(new_plan_date, datetime.min.time())
        new_plan = (
            db.query(models.Plan)
            .filter(models.Plan.user_id == user.id, models.Plan.plan_date == new_plan_datetime)
            .first()
        )
        if not new_plan:
            new_plan = models.Plan(
                user_id=user.id,
                plan_date=new_plan_datetime,
                model_version=item.plan.model_version,
                status=models.PlanStatus.adjusted,
                summary=None,
            )
            db.add(new_plan)
            db.flush()
        item.plan_id = new_plan.id
        item.position = 0

    item.start_datetime = start
    item.end_datetime = end
    if item.task:
        item.task.status = models.TaskStatus.scheduled
    db.commit()
    db.refresh(item)

    # feedback: earlier (+1) vs later (-1)
    delta = (start - original_start).total_seconds()
    outcome = 1 if delta < 0 else -1 if delta > 0 else 0
    if outcome != 0:
        fb = models.FeedbackLog(
            user_id=user.id,
            task_id=item.task_id,
            outcome=outcome,
            note="User manually adjusted schedule",
        )
        db.add(fb)
        db.commit()

    return schemas.ScheduledTaskOut(
        plan_item_id=item.id,
        task_id=item.task_id,
        title=item.task.title if item.task else "",
        start=item.start_datetime,
        end=item.end_datetime,
        explanation=item.explanation or "",
        priority=0.0,
        llm_explanation=None,
    )


@router.delete("/item/{item_id}")
def delete_plan_item(item_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    item = (
        db.query(models.PlanItem)
        .join(models.Plan, models.PlanItem.plan_id == models.Plan.id)
        .filter(models.PlanItem.id == item_id, models.Plan.user_id == user.id)
        .first()
    )
    if not item:
        raise HTTPException(status_code=404, detail="Plan item not found")
    task = item.task
    db.delete(item)
    if task:
        task.status = models.TaskStatus.unscheduled
    db.commit()
    return {"detail": "Removed from calendar"}
