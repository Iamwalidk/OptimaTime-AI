from datetime import date, datetime, timedelta
import sys
from pathlib import Path

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.append(str(REPO_ROOT))

from backend import models, schemas
from backend.database import Base
from backend.routers import planning


def _has_overlaps(items):
    parsed = [(i.start, i.end) for i in items]
    for idx, (start_a, end_a) in enumerate(parsed):
        for start_b, end_b in parsed[idx + 1 :]:
            if start_a < end_b and end_a > start_b:
                return True
    return False


def main() -> None:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    plan_date = date.today()
    deadline = datetime.combine(plan_date, datetime.min.time()) + timedelta(hours=23, minutes=59)

    with SessionLocal() as db:
        user = models.User(
            email="user@example.com",
            name="Test User",
            profile=models.UserProfile.worker,
            role=models.UserRole.user,
            timezone="UTC",
            hashed_password="not-used",
            is_active=True,
            token_version=0,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        for title in ("Task A", "Task B"):
            db.add(
                models.Task(
                    user_id=user.id,
                    title=title,
                    description=None,
                    duration_minutes=60,
                    deadline=deadline,
                    task_type="work",
                    importance="high",
                    preferred_time="morning",
                    energy="high",
                    status=models.TaskStatus.pending,
                )
            )
        db.commit()

        first_plan = planning.generate_plan(schemas.PlanRequest(date=plan_date), db=db, user=user)
        assert len(first_plan.scheduled) == 2, "expected 2 scheduled items"

        item_a = first_plan.scheduled[0]
        item_b = first_plan.scheduled[1]
        overlap_start = item_b.start + timedelta(minutes=15)
        overlap_end = overlap_start + (item_a.end - item_a.start)
        try:
            planning.update_plan_item(
                item_a.plan_item_id,
                start=overlap_start,
                end=overlap_end,
                db=db,
                user=user,
            )
            raise AssertionError("expected overlap error")
        except HTTPException as exc:
            assert exc.status_code == 400
            assert "Time slot already occupied" in exc.detail

        db.add(
            models.Task(
                user_id=user.id,
                title="Task C",
                description=None,
                duration_minutes=60,
                deadline=deadline,
                task_type="work",
                importance="high",
                preferred_time="morning",
                energy="high",
                status=models.TaskStatus.pending,
            )
        )
        db.commit()

        second_plan = planning.generate_plan(schemas.PlanRequest(date=plan_date), db=db, user=user)
        assert len(second_plan.scheduled) == 3, "expected 3 scheduled items"
        assert not _has_overlaps(second_plan.scheduled), "overlaps detected after replan"

        earliest = min(second_plan.scheduled, key=lambda item: item.start)
        moved_start = earliest.start - timedelta(hours=1)
        moved_end = moved_start + (earliest.end - earliest.start)
        planning.update_plan_item(
            earliest.plan_item_id,
            start=moved_start,
            end=moved_end,
            db=db,
            user=user,
        )

        feedback = (
            db.query(models.FeedbackLog)
            .filter(models.FeedbackLog.user_id == user.id)
            .order_by(models.FeedbackLog.created_at.desc())
            .all()
        )
        assert any(
            fb.task_id == earliest.task_id and fb.outcome == 1 for fb in feedback
        ), "expected feedback log for earlier move"

        moved_item = db.get(models.PlanItem, earliest.plan_item_id)
        assert moved_item.source == "manual", "expected manual source on moved item"

        db.add(
            models.Task(
                user_id=user.id,
                title="Task D",
                description=None,
                duration_minutes=60,
                deadline=deadline,
                task_type="work",
                importance="high",
                preferred_time="morning",
                energy="high",
                status=models.TaskStatus.pending,
            )
        )
        db.commit()

        third_plan = planning.generate_plan(schemas.PlanRequest(date=plan_date), db=db, user=user)
        assert len(third_plan.scheduled) == 4, "expected 4 scheduled items"
        assert not _has_overlaps(third_plan.scheduled), "overlaps detected after feedback"

    print("Planning persistence verification passed.")


if __name__ == "__main__":
    main()
