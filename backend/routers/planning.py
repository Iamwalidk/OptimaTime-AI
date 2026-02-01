import logging
from datetime import datetime, date, timezone, timedelta, time

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, selectinload

from .. import models, schemas
from ..dependencies import get_current_user, get_db
from ..ml import generate_schedule

router = APIRouter(prefix="/planning", tags=["planning"])
logger = logging.getLogger(__name__)


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


def _normalize_dt(value: datetime) -> datetime:
    if value.tzinfo is not None and value.tzinfo.utcoffset(value) is not None:
        return value.astimezone(timezone.utc).replace(tzinfo=None)
    return value


def _get_or_create_settings(db: Session, user_id: int) -> models.UserSettings:
    settings = db.query(models.UserSettings).filter(models.UserSettings.user_id == user_id).first()
    if settings:
        return settings
    settings = models.UserSettings(user_id=user_id)
    db.add(settings)
    db.commit()
    db.refresh(settings)
    return settings


def _importance_rank(importance: str) -> int:
    return {"high": 0, "medium": 1, "low": 2}.get(importance, 1)


def _allocate_tasks_to_days(
    tasks,
    horizon_dates: list[date],
    plan_start_date: date,
    existing_minutes_by_day: dict[date, int],
    start_hour: int,
    end_hour: int,
):
    assigned_tasks_by_day = {day: [] for day in horizon_dates}
    assigned_minutes_by_day = {day: 0 for day in horizon_dates}
    unscheduled_reasons: dict[int, str] = {}

    if not horizon_dates:
        for task in tasks:
            unscheduled_reasons[task.id] = "Deadline outside horizon"
        return assigned_tasks_by_day, assigned_minutes_by_day, unscheduled_reasons

    day_capacity_minutes = max(1, (end_hour - start_hour) * 60)
    tasks_sorted = sorted(
        tasks,
        key=lambda t: (t.deadline, _importance_rank(getattr(t, "importance", "medium"))),
    )

    for task in tasks_sorted:
        deadline_date = task.deadline.date()
        candidates = [day for day in horizon_dates if day <= deadline_date]
        if not candidates:
            unscheduled_reasons[task.id] = "Deadline outside horizon"
            continue

        far_deadline = (deadline_date - plan_start_date).days >= 4
        best_day = None
        best_score = None

        for day in candidates:
            day_load_minutes = existing_minutes_by_day.get(day, 0) + assigned_minutes_by_day.get(day, 0)
            load_penalty = (day_load_minutes / day_capacity_minutes) ** 2 * 8.0

            days_until_deadline = max(0, (deadline_date - day).days)
            if days_until_deadline <= 1:
                deadline_penalty = 0.0
            else:
                deadline_penalty = min(6.0, days_until_deadline * 0.6)

            horizon_offset = (day - plan_start_date).days
            early_if_far_penalty = 2.5 if far_deadline and horizon_offset <= 1 else 0.0

            score = load_penalty + deadline_penalty + early_if_far_penalty

            if best_score is None or score < best_score:
                best_score = score
                best_day = day
            elif score == best_score and best_day is not None:
                if far_deadline:
                    if day > best_day:
                        best_day = day
                else:
                    if day < best_day:
                        best_day = day

        if best_day is None:
            unscheduled_reasons[task.id] = "Deadline outside horizon"
            continue

        assigned_tasks_by_day[best_day].append(task)
        assigned_minutes_by_day[best_day] += task.duration_minutes

    return assigned_tasks_by_day, assigned_minutes_by_day, unscheduled_reasons


@router.post("/plan", response_model=schemas.PlanOut)
def generate_plan(plan_req: schemas.PlanRequest, db: Session = Depends(get_db), user=Depends(get_current_user)):
    try:
        return _generate_plan_impl(plan_req=plan_req, db=db, user=user)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to generate plan")
        raise HTTPException(status_code=500, detail=f"Failed to generate plan: {exc}") from exc


def _generate_plan_impl(plan_req: schemas.PlanRequest, db: Session, user):
    LOOKAHEAD_DAYS = 14
    start_of_day = datetime.combine(plan_req.date, time.min)
    lookahead_end = start_of_day + timedelta(days=LOOKAHEAD_DAYS)

    settings = _get_or_create_settings(db, user.id)
    start_hour = _parse_hour_str(settings.working_hours_start, 8)
    end_hour = _parse_hour_str(settings.working_hours_end, 22)
    if end_hour <= start_hour:
        end_hour = min(start_hour + 12, 23)

    horizon_dates = [plan_req.date]
    for offset in range(1, 7):
        plan_date = plan_req.date + timedelta(days=offset)
        if _is_workday(plan_date, settings.work_days_mask):
            horizon_dates.append(plan_date)

    plans_by_date: dict[date, models.Plan] = {}
    for plan_date in horizon_dates:
        plan_datetime = datetime.combine(plan_date, datetime.min.time())
        plan = (
            db.query(models.Plan)
            .filter(models.Plan.user_id == user.id, models.Plan.plan_date == plan_datetime)
            .first()
        )
        if not plan:
            plan = models.Plan(
                user_id=user.id,
                plan_date=plan_datetime,
                model_version="priority_model_v1",
                status=models.PlanStatus.generated,
                summary=None,
            )
            db.add(plan)
            db.flush()
        plans_by_date[plan_date] = plan

    existing_items_by_day: dict[date, list[models.PlanItem]] = {}
    occupied_intervals_by_day: dict[date, list[tuple[datetime, datetime]]] = {}
    existing_minutes_by_day: dict[date, int] = {day: 0 for day in horizon_dates}
    existing_task_ids_any_day: set[int] = set()

    for plan_date, plan in plans_by_date.items():
        items = (
            db.query(models.PlanItem)
            .filter(models.PlanItem.plan_id == plan.id)
            .order_by(models.PlanItem.position.asc())
            .all()
        )
        existing_items_by_day[plan_date] = items
        existing_task_ids_any_day.update(item.task_id for item in items)
        occupied_intervals_by_day[plan_date] = [(item.start_datetime, item.end_datetime) for item in items]
        existing_minutes_by_day[plan_date] = int(
            sum((item.end_datetime - item.start_datetime).total_seconds() / 60.0 for item in items)
        )

    task_query = db.query(models.Task).filter(
        models.Task.user_id == user.id,
        models.Task.deadline >= start_of_day,
        models.Task.deadline <= lookahead_end,
        models.Task.status.in_([models.TaskStatus.pending, models.TaskStatus.unscheduled]),
    )
    if existing_task_ids_any_day:
        task_query = task_query.filter(~models.Task.id.in_(existing_task_ids_any_day))
    tasks_to_assign = task_query.all()

    if not tasks_to_assign and not any(existing_items_by_day.values()):
        raise HTTPException(status_code=400, detail="No pending tasks to plan for this date")

    feedback = (
        db.query(models.FeedbackLog)
        .options(selectinload(models.FeedbackLog.task))
        .filter(models.FeedbackLog.user_id == user.id)
        .order_by(models.FeedbackLog.created_at.desc())
        .limit(500)
        .all()
    )

    assigned_tasks_by_day, _, allocator_unscheduled = _allocate_tasks_to_days(
        tasks=tasks_to_assign,
        horizon_dates=horizon_dates,
        plan_start_date=plan_req.date,
        existing_minutes_by_day=existing_minutes_by_day,
        start_hour=start_hour,
        end_hour=end_hour,
    )

    scheduled_ids: set[int] = set()
    unscheduled_reasons: dict[int, str] = dict(allocator_unscheduled)
    scheduled_map_by_day: dict[date, list[tuple[dict, int]]] = {}
    model_confidence_by_day: dict[date, float | None] = {}

    for plan_date in horizon_dates:
        day_tasks = assigned_tasks_by_day.get(plan_date, [])
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
            for t in day_tasks
        ]

        scheduled = []
        unscheduled = []
        model_confidence = None
        if task_dicts:
            scheduled, unscheduled, model_confidence = generate_schedule(
                tasks=task_dicts,
                user_profile=user.profile.value,
                plan_date=plan_date,
                feedback=feedback,
                start_hour=start_hour,
                end_hour=end_hour,
                occupied=occupied_intervals_by_day.get(plan_date),
            )
        model_confidence_by_day[plan_date] = model_confidence

        for u in unscheduled:
            unscheduled_reasons[u["id"]] = u.get("reason")

        for s in scheduled:
            scheduled_ids.add(s["task_id"])

        existing_items = existing_items_by_day.get(plan_date, [])
        next_position = max((item.position for item in existing_items), default=-1) + 1
        plan_items_map = []
        for s in scheduled:
            item = models.PlanItem(
                plan_id=plans_by_date[plan_date].id,
                task_id=s["task_id"],
                start_datetime=_normalize_dt(datetime.fromisoformat(s["start"])),
                end_datetime=_normalize_dt(datetime.fromisoformat(s["end"])),
                explanation=s.get("explanation"),
                position=next_position,
                source="ai",
            )
            db.add(item)
            db.flush()
            plan_items_map.append((s, item.id))
            next_position += 1

        scheduled_map_by_day[plan_date] = plan_items_map
        total_scheduled = len(existing_items) + len(plan_items_map)
        plans_by_date[plan_date].summary = f"{total_scheduled} scheduled, {len(unscheduled)} unscheduled"

    for items in existing_items_by_day.values():
        for item in items:
            if item.task:
                item.task.status = models.TaskStatus.scheduled

    for t in tasks_to_assign:
        if t.id in scheduled_ids:
            t.status = models.TaskStatus.scheduled
        else:
            t.status = models.TaskStatus.unscheduled

    db.commit()

    plan = plans_by_date[plan_req.date]
    items = (
        db.query(models.PlanItem)
        .filter(models.PlanItem.plan_id == plan.id)
        .order_by(models.PlanItem.position.asc())
        .all()
    )
    scheduled_payload_by_id = {item_id: s for s, item_id in scheduled_map_by_day.get(plan_req.date, [])}
    scheduled_out = []
    for i in items:
        payload = scheduled_payload_by_id.get(i.id)
        scheduled_out.append(
            schemas.ScheduledTaskOut(
                plan_item_id=i.id,
                task_id=i.task_id,
                title=i.task.title if i.task else "",
                start=i.start_datetime,
                end=i.end_datetime,
                explanation=i.explanation or "",
                priority=payload["priority"] if payload else 0.0,
                llm_explanation=payload.get("llm_explanation") if payload else None,
            )
        )

    unscheduled_tasks = (
        db.query(models.Task)
        .filter(
            models.Task.user_id == user.id,
            models.Task.status == models.TaskStatus.unscheduled,
            models.Task.deadline >= start_of_day,
        )
        .all()
    )
    unscheduled_out = []
    for t in unscheduled_tasks:
        unscheduled_out.append(
            schemas.UnscheduledTaskOut.from_orm(t).copy(update={"reason": unscheduled_reasons.get(t.id)})
        )

    return schemas.PlanOut(
        model_version=plan.model_version,
        model_confidence=model_confidence_by_day.get(plan_req.date),
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

    start = _normalize_dt(start)
    end = _normalize_dt(end)

    if end <= start:
        raise HTTPException(status_code=400, detail="End time must be after start time.")

    original_start = item.start_datetime
    new_plan_date = start.date()
    target_plan = item.plan

    # move to another plan if date changed
    if item.plan.plan_date.date() != new_plan_date:
        new_plan_datetime = datetime.combine(new_plan_date, datetime.min.time())
        target_plan = (
            db.query(models.Plan)
            .filter(models.Plan.user_id == user.id, models.Plan.plan_date == new_plan_datetime)
            .first()
        )

    if target_plan:
        conflict = (
            db.query(models.PlanItem)
            .join(models.Task, models.PlanItem.task_id == models.Task.id)
            .filter(
                models.PlanItem.plan_id == target_plan.id,
                models.PlanItem.id != item.id,
                models.PlanItem.start_datetime < end,
                models.PlanItem.end_datetime > start,
            )
            .order_by(models.PlanItem.start_datetime.asc())
            .first()
        )
        if conflict:
            conflict_title = conflict.task.title if conflict.task else "another task"
            conflict_start = conflict.start_datetime.strftime("%H:%M")
            conflict_end = conflict.end_datetime.strftime("%H:%M")
            raise HTTPException(
                status_code=400,
                detail=f"Time slot already occupied by '{conflict_title}' from {conflict_start} to {conflict_end}.",
            )

    if item.plan.plan_date.date() != new_plan_date:
        if not target_plan:
            new_plan = models.Plan(
                user_id=user.id,
                plan_date=new_plan_datetime,
                model_version=item.plan.model_version,
                status=models.PlanStatus.adjusted,
                summary=None,
            )
            db.add(new_plan)
            db.flush()
            target_plan = new_plan
        item.plan_id = target_plan.id
        item.position = 0

    item.start_datetime = start
    item.end_datetime = end
    item.source = "manual"
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
        remaining = (
            db.query(models.PlanItem)
            .filter(models.PlanItem.task_id == task.id, models.PlanItem.id != item.id)
            .first()
        )
        if not remaining:
            task.status = models.TaskStatus.unscheduled
    db.commit()
    return {"detail": "Removed from calendar"}
