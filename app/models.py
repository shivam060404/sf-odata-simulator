from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class Candidate:
    id: str
    first_name: str
    last_name: str
    email: str
    status: str = "OFFER_ACCEPTED"
    last_modified_at: datetime = field(default_factory=utcnow)
    version: int = 1


@dataclass
class OnboardingProcess:
    id: str
    candidate_id: str
    current_stage: str
    doj: date | None = None
    last_modified_at: datetime = field(default_factory=utcnow)
    version: int = 1


@dataclass
class OnboardingTask:
    id: str
    process_id: str
    task_type: str
    status: str = "PENDING"
    assignee_type: str = "CANDIDATE"
    last_modified_at: datetime = field(default_factory=utcnow)
    version: int = 1


@dataclass
class OnboardingActivity:
    id: str
    process_id: str
    activity_type: str
    status: str = "OPEN"
    last_modified_at: datetime = field(default_factory=utcnow)
    version: int = 1


@dataclass
class Document:
    id: str
    candidate_id: str
    doc_type: str
    status: str = "PENDING"
    last_modified_at: datetime = field(default_factory=utcnow)
    version: int = 1


@dataclass
class EventLog:
    id: int
    entity_name: str
    entity_id: str
    action: str
    payload: dict | None = None
    created_at: datetime = field(default_factory=utcnow)
    message: str | None = None
