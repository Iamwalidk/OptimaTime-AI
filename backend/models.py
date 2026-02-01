from datetime import datetime, date
import enum

from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    Enum,
    ForeignKey,
    Text,
    Float,
    Boolean,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from .database import Base


class UserProfile(str, enum.Enum):
    student = "student"
    worker = "worker"
    entrepreneur = "entrepreneur"


class UserRole(str, enum.Enum):
    user = "user"
    admin = "admin"


class TaskStatus(str, enum.Enum):
    pending = "pending"
    scheduled = "scheduled"
    completed = "completed"
    unscheduled = "unscheduled"


class PlanStatus(str, enum.Enum):
    generated = "generated"
    adjusted = "adjusted"
    archived = "archived"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    profile = Column(Enum(UserProfile), nullable=False)
    role = Column(Enum(UserRole), default=UserRole.user, nullable=False)
    timezone = Column(String, default="UTC", nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    token_version = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login_at = Column(DateTime, nullable=True)

    tasks = relationship("Task", back_populates="user", cascade="all, delete-orphan")
    feedback = relationship("FeedbackLog", back_populates="user", cascade="all, delete-orphan")
    settings = relationship("UserSettings", back_populates="user", uselist=False, cascade="all, delete-orphan")
    plans = relationship("Plan", back_populates="user", cascade="all, delete-orphan")


class UserSettings(Base):
    __tablename__ = "user_settings"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    working_hours_start = Column(String, default="08:00", nullable=False)
    working_hours_end = Column(String, default="18:00", nullable=False)
    work_days_mask = Column(String, default="1111111", nullable=False)  # Mon-Sun
    default_planning_horizon_hours = Column(Integer, default=72, nullable=False)
    notifications_enabled = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="settings")


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    duration_minutes = Column(Integer, nullable=False)
    deadline = Column(DateTime, nullable=False)

    task_type = Column(String, nullable=False)
    importance = Column(String, nullable=False)
    preferred_time = Column(String, nullable=False)
    energy = Column(String, nullable=False)

    status = Column(Enum(TaskStatus), default=TaskStatus.pending, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="tasks")
    feedback = relationship("FeedbackLog", back_populates="task")
    plan_items = relationship("PlanItem", back_populates="task", cascade="all, delete-orphan")


class Plan(Base):
    __tablename__ = "plans"
    __table_args__ = (UniqueConstraint("user_id", "plan_date", name="uq_user_plan_date"),)

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    plan_date = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    model_version = Column(String, default="priority_model_v1")
    status = Column(Enum(PlanStatus), default=PlanStatus.generated, nullable=False)
    summary = Column(String, nullable=True)

    user = relationship("User", back_populates="plans")
    items = relationship("PlanItem", back_populates="plan", cascade="all, delete-orphan")


class PlanItem(Base):
    __tablename__ = "plan_items"

    id = Column(Integer, primary_key=True)
    plan_id = Column(Integer, ForeignKey("plans.id", ondelete="CASCADE"), nullable=False, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, index=True)
    start_datetime = Column(DateTime, nullable=False)
    end_datetime = Column(DateTime, nullable=False)
    explanation = Column(Text, nullable=True)
    position = Column(Integer, default=0, nullable=False)
    source = Column(String, default="ai", nullable=False)

    plan = relationship("Plan", back_populates="items")
    task = relationship("Task", back_populates="plan_items")


class FeedbackLog(Base):
    __tablename__ = "feedback_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    task_id = Column(Integer, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=True)

    feature_vector = Column(Text, nullable=True)
    old_priority = Column(Float, nullable=True)
    outcome = Column(Integer, nullable=False)  # +1 earlier is better, -1 later/removed
    note = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="feedback")
    task = relationship("Task", back_populates="feedback")


class Note(Base):
    __tablename__ = "notes"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String, nullable=False)
    body = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User")
