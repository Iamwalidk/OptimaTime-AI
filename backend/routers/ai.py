import json
import logging
from datetime import datetime, timedelta
from typing import List

from fastapi import APIRouter, Depends, HTTPException

from .. import schemas
from ..config import settings
from ..dependencies import get_current_user

try:
    from openai import OpenAI
except ImportError:  # pragma: no cover
    OpenAI = None  # type: ignore

router = APIRouter(prefix="/ai", tags=["ai"])
logger = logging.getLogger(__name__)


def _get_openai_client():
    if not settings.openai_api_key or OpenAI is None:
        return None
    return OpenAI(api_key=settings.openai_api_key)


def _fallback_parse(payload: schemas.AiParseRequest) -> List[schemas.AiParsedTask]:
    lines = [seg.strip() for seg in payload.text.replace("\n", ".").split(".") if seg.strip()]
    tasks: List[schemas.AiParsedTask] = []
    now = datetime.utcnow()
    for idx, line in enumerate(lines):
        tasks.append(
            schemas.AiParsedTask(
                title=line[:80],
                duration_minutes=payload.default_duration,
                deadline=now + timedelta(hours=payload.default_hours_until_deadline + idx),
                task_type="work",
                importance="medium",
                preferred_time="anytime",
                energy="medium",
            )
        )
    return tasks


def _parse_with_llm(payload: schemas.AiParseRequest) -> List[schemas.AiParsedTask]:
    client = _get_openai_client()
    if client is None:
        raise HTTPException(
            status_code=400,
            detail="LLM parsing not configured. Set OPENAI_API_KEY on the backend to enable natural language parsing.",
        )

    system_prompt = (
        "Extract tasks from the user's day description. "
        "Return JSON with a 'tasks' array. Each task has: "
        "title, duration_minutes (int), deadline (ISO8601), task_type (work/study/meeting/personal/social/admin), "
        "importance (low/medium/high), preferred_time (morning/afternoon/evening/anytime), energy (low/medium/high). "
        "Keep values concise."
    )

    try:
        completion = client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": payload.text},
            ],
            temperature=0.2,
        )
        content = completion.choices[0].message.content or ""
        try:
            data = json.loads(content)
        except Exception:
            logger.warning("LLM returned non-JSON content; falling back. content=%s", content)
            return _fallback_parse(payload)
        tasks_raw = data.get("tasks", [])
        tasks: List[schemas.AiParsedTask] = []
        for t in tasks_raw:
            try:
                deadline_str = t.get("deadline")
                deadline = (
                    datetime.fromisoformat(deadline_str)
                    if deadline_str
                    else datetime.utcnow() + timedelta(hours=payload.default_hours_until_deadline)
                )
                tasks.append(
                    schemas.AiParsedTask(
                        title=t.get("title", "Task")[:80],
                        duration_minutes=int(t.get("duration_minutes", payload.default_duration)),
                        deadline=deadline,
                        task_type=t.get("task_type", "work"),
                        importance=t.get("importance", "medium"),
                        preferred_time=t.get("preferred_time", "anytime"),
                        energy=t.get("energy", "medium"),
                    )
                )
            except Exception:
                continue
        if not tasks:
            logger.warning("LLM returned empty tasks; falling back.")
            return _fallback_parse(payload)
        return tasks
    except HTTPException:
        raise
    except Exception:
        logger.exception("LLM parse failed, falling back")
        return _fallback_parse(payload)


@router.post("/parse", response_model=schemas.AiParseResponse)
def parse_day_text(payload: schemas.AiParseRequest, user=Depends(get_current_user)):
    tasks = _parse_with_llm(payload)
    return schemas.AiParseResponse(tasks=tasks)


@router.post("/chat", response_model=schemas.AiChatResponse)
def chat_planner(payload: schemas.AiChatRequest, user=Depends(get_current_user)):
    client = _get_openai_client()
    if client is None:
        raise HTTPException(
            status_code=400,
            detail="LLM chat not configured. Set OPENAI_API_KEY on the backend to enable planner chat.",
        )

    system_prompt = (
        "You are an AI planner assistant. Acknowledge the request and suggest how to adapt the day. "
        "Be concise (2-3 sentences). Do not return JSON."
    )
    try:
        completion = client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": payload.message},
            ],
            temperature=0.4,
        )
        content = completion.choices[0].message.content or ""
        return schemas.AiChatResponse(reply=content)
    except HTTPException:
        raise
    except Exception:
        logger.exception("LLM chat failed")
        raise HTTPException(status_code=500, detail="AI planner chat failed. Please try again.")
