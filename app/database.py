from __future__ import annotations

import json
import os
import threading
from datetime import date, datetime
from typing import Any

from app.models import (
    Candidate,
    Document,
    EventLog,
    OnboardingActivity,
    OnboardingProcess,
    OnboardingTask,
    utcnow,
)


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    return date.fromisoformat(value)


def _serialize_datetime(value: datetime | None) -> str | None:
    if not value:
        return None
    return value.isoformat()


def _serialize_date(value: date | None) -> str | None:
    if not value:
        return None
    return value.isoformat()


class JsonStore:
    def __init__(self, path: str | None):
        self._path = path
        self._lock = threading.RLock()
        self._candidates: dict[str, Candidate] = {}
        self._processes: dict[str, OnboardingProcess] = {}
        self._tasks: dict[str, OnboardingTask] = {}
        self._activities: dict[str, OnboardingActivity] = {}
        self._documents: dict[str, Document] = {}
        self._event_logs: list[EventLog] = []
        self._process_by_candidate: dict[str, str] = {}
        self._next_event_id = 1
        if self._path:
            self._load()

    def _load(self) -> None:
        if not self._path or not os.path.exists(self._path):
            return
        with self._lock:
            with open(self._path, "r", encoding="utf-8") as handle:
                payload = json.load(handle)
            for item in payload.get("candidates", []):
                self._candidates[item["id"]] = Candidate(
                    id=item["id"],
                    first_name=item["first_name"],
                    last_name=item["last_name"],
                    email=item["email"],
                    status=item.get("status", "OFFER_ACCEPTED"),
                    last_modified_at=_parse_datetime(item.get("last_modified_at")) or utcnow(),
                    version=item.get("version", 1),
                )
            for item in payload.get("processes", []):
                process = OnboardingProcess(
                    id=item["id"],
                    candidate_id=item["candidate_id"],
                    current_stage=item["current_stage"],
                    doj=_parse_date(item.get("doj")),
                    last_modified_at=_parse_datetime(item.get("last_modified_at")) or utcnow(),
                    version=item.get("version", 1),
                )
                self._processes[item["id"]] = process
                self._process_by_candidate[process.candidate_id] = process.id
            for item in payload.get("tasks", []):
                self._tasks[item["id"]] = OnboardingTask(
                    id=item["id"],
                    process_id=item["process_id"],
                    task_type=item["task_type"],
                    status=item.get("status", "PENDING"),
                    assignee_type=item.get("assignee_type", "CANDIDATE"),
                    last_modified_at=_parse_datetime(item.get("last_modified_at")) or utcnow(),
                    version=item.get("version", 1),
                )
            for item in payload.get("activities", []):
                self._activities[item["id"]] = OnboardingActivity(
                    id=item["id"],
                    process_id=item["process_id"],
                    activity_type=item["activity_type"],
                    status=item.get("status", "OPEN"),
                    last_modified_at=_parse_datetime(item.get("last_modified_at")) or utcnow(),
                    version=item.get("version", 1),
                )
            for item in payload.get("documents", []):
                self._documents[item["id"]] = Document(
                    id=item["id"],
                    candidate_id=item["candidate_id"],
                    doc_type=item["doc_type"],
                    status=item.get("status", "PENDING"),
                    last_modified_at=_parse_datetime(item.get("last_modified_at")) or utcnow(),
                    version=item.get("version", 1),
                )
            self._event_logs = [
                EventLog(
                    id=item["id"],
                    entity_name=item["entity_name"],
                    entity_id=item["entity_id"],
                    action=item["action"],
                    payload=item.get("payload"),
                    created_at=_parse_datetime(item.get("created_at")) or utcnow(),
                    message=item.get("message"),
                )
                for item in payload.get("event_logs", [])
            ]
            max_event = max(self._event_logs, key=lambda event: event.id, default=None)
            max_event_id = max_event.id if max_event else 0
            stored_next = payload.get("next_event_id", 1)
            self._next_event_id = max(stored_next, max_event_id + 1)

    def _serialize(self) -> dict[str, Any]:
        return {
            "candidates": [
                {
                    "id": item.id,
                    "first_name": item.first_name,
                    "last_name": item.last_name,
                    "email": item.email,
                    "status": item.status,
                    "last_modified_at": _serialize_datetime(item.last_modified_at),
                    "version": item.version,
                }
                for item in self._candidates.values()
            ],
            "processes": [
                {
                    "id": item.id,
                    "candidate_id": item.candidate_id,
                    "current_stage": item.current_stage,
                    "doj": _serialize_date(item.doj),
                    "last_modified_at": _serialize_datetime(item.last_modified_at),
                    "version": item.version,
                }
                for item in self._processes.values()
            ],
            "tasks": [
                {
                    "id": item.id,
                    "process_id": item.process_id,
                    "task_type": item.task_type,
                    "status": item.status,
                    "assignee_type": item.assignee_type,
                    "last_modified_at": _serialize_datetime(item.last_modified_at),
                    "version": item.version,
                }
                for item in self._tasks.values()
            ],
            "activities": [
                {
                    "id": item.id,
                    "process_id": item.process_id,
                    "activity_type": item.activity_type,
                    "status": item.status,
                    "last_modified_at": _serialize_datetime(item.last_modified_at),
                    "version": item.version,
                }
                for item in self._activities.values()
            ],
            "documents": [
                {
                    "id": item.id,
                    "candidate_id": item.candidate_id,
                    "doc_type": item.doc_type,
                    "status": item.status,
                    "last_modified_at": _serialize_datetime(item.last_modified_at),
                    "version": item.version,
                }
                for item in self._documents.values()
            ],
            "event_logs": [
                {
                    "id": item.id,
                    "entity_name": item.entity_name,
                    "entity_id": item.entity_id,
                    "action": item.action,
                    "payload": item.payload,
                    "created_at": _serialize_datetime(item.created_at),
                    "message": item.message,
                }
                for item in self._event_logs
            ],
            "next_event_id": self._next_event_id,
        }

    def save(self) -> None:
        if not self._path:
            return
        with self._lock:
            directory = os.path.dirname(self._path)
            if directory:
                os.makedirs(directory, exist_ok=True)
            payload = self._serialize()
            tmp_path = f"{self._path}.tmp"
            with open(tmp_path, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, indent=2, sort_keys=True)
            os.replace(tmp_path, self._path)

    def list_entities(self, model: type) -> list[Any]:
        with self._lock:
            return list(self._collections()[model].values())

    def get_entity(self, model: type, entity_id: str):
        with self._lock:
            return self._collections()[model].get(entity_id)

    def add_entity(self, entity: Any) -> None:
        with self._lock:
            self._collections()[type(entity)][entity.id] = entity
            if isinstance(entity, OnboardingProcess):
                self._process_by_candidate[entity.candidate_id] = entity.id

    def get_process_by_candidate(self, candidate_id: str) -> OnboardingProcess | None:
        with self._lock:
            process_id = self._process_by_candidate.get(candidate_id)
            if not process_id:
                return None
            return self._processes.get(process_id)

    def add_event(
        self, entity_name: str, entity_id: str, action: str, payload: dict | None = None, message: str | None = None
    ) -> EventLog:
        with self._lock:
            event = EventLog(
                id=self._next_event_id,
                entity_name=entity_name,
                entity_id=entity_id,
                action=action,
                payload=payload,
                message=message,
            )
            self._next_event_id += 1
            self._event_logs.append(event)
            return event

    def _collections(self) -> dict[type, dict[str, Any]]:
        return {
            Candidate: self._candidates,
            OnboardingProcess: self._processes,
            OnboardingTask: self._tasks,
            OnboardingActivity: self._activities,
            Document: self._documents,
        }


DATA_FILE = os.getenv("DATA_FILE", "data.json")
STORE = JsonStore(DATA_FILE)


def get_store() -> JsonStore:
    return STORE
