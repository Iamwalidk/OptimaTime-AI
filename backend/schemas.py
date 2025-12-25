from datetime import datetime, date
from typing import Optional, List, Literal

from pydantic import BaseModel, EmailStr, Field

from .models import UserProfile, TaskStatus


class UserBase(BaseModel):
    email: EmailStr
    name: str
    profile: UserProfile


class UserCreate(UserBase):
    password: str = Field(min_length=6)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)


class UserOut(BaseModel):
    id: int
    email: EmailStr
    name: str
    profile: UserProfile
    role: Optional[str] = None
    timezone: Optional[str] = None
    created_at: Optional[datetime] = None
    last_login_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    duration_minutes: int = Field(gt=0)
    deadline: datetime
    task_type: str
    importance: str
    preferred_time: str
    energy: str


class TaskOut(BaseModel):
    id: int
    user_id: int
    title: str
    description: Optional[str] = None
    duration_minutes: int
    deadline: datetime
    task_type: str
    importance: str
    preferred_time: str
    energy: str
    status: TaskStatus
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class PlanRequest(BaseModel):
    date: date


class ScheduledTaskOut(BaseModel):
    plan_item_id: Optional[int] = None
    task_id: int
    title: str
    start: datetime
    end: datetime
    explanation: str
    priority: float
    llm_explanation: Optional[str] = None


class PlanOut(BaseModel):
    model_version: str
    model_confidence: Optional[float] = None
    scheduled: List[ScheduledTaskOut]
    unscheduled: List["UnscheduledTaskOut"]


class FeedbackCreate(BaseModel):
    task_id: Optional[int] = None
    outcome: Literal[-1, 1] = Field(..., description="+1 if user wanted earlier/higher priority, -1 if later")
    note: Optional[str] = None


class FeedbackOut(BaseModel):
    id: int
    task_id: Optional[int]
    outcome: int
    note: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class NoteCreate(BaseModel):
    title: str
    body: Optional[str] = None


class NoteOut(BaseModel):
    id: int
    title: str
    body: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class UnscheduledTaskOut(TaskOut):
    reason: Optional[str] = None
