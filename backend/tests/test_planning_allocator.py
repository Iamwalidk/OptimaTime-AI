from datetime import date, datetime, timedelta

from backend.routers import planning


class _DummyTask:
    def __init__(self, task_id: int, deadline: datetime, duration_minutes: int, importance: str = "medium"):
        self.id = task_id
        self.deadline = deadline
        self.duration_minutes = duration_minutes
        self.importance = importance


def test_allocator_spreads_across_days():
    plan_start = date(2025, 1, 6)
    horizon_dates = [plan_start + timedelta(days=offset) for offset in range(7)]
    deadline = datetime.combine(plan_start + timedelta(days=6), datetime.min.time()) + timedelta(hours=17)

    tasks = [_DummyTask(task_id=i, deadline=deadline, duration_minutes=240) for i in range(4)]
    existing_minutes_by_day = {day: 0 for day in horizon_dates}

    assigned, _, unscheduled = planning._allocate_tasks_to_days(
        tasks=tasks,
        horizon_dates=horizon_dates,
        plan_start_date=plan_start,
        existing_minutes_by_day=existing_minutes_by_day,
        start_hour=8,
        end_hour=22,
    )

    days_with_tasks = [day for day, day_tasks in assigned.items() if day_tasks]
    assert len(days_with_tasks) >= 2
    assert unscheduled == {}
