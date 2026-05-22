from __future__ import annotations

from datetime import date
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Query, Request

from app.database import JsonStore, get_store
from app.models import Candidate, Document, OnboardingActivity, OnboardingProcess, OnboardingTask, utcnow
from app.odata import apply_filter, parse_iso8601, parse_orderby, to_collection_response, to_single_response
from app.security import require_admin_token
from app.state_machine import TASK_STATUSES, next_stage, validate_stage_transition

app = FastAPI(title="SF OData Onboarding Simulator", version="0.1.0")


def candidate_dict(c: Candidate) -> dict[str, Any]:
    return {
        "candidateId": c.id,
        "firstName": c.first_name,
        "lastName": c.last_name,
        "email": c.email,
        "status": c.status,
        "lastModifiedAt": c.last_modified_at.isoformat(),
        "version": c.version,
    }


def process_dict(p: OnboardingProcess) -> dict[str, Any]:
    return {
        "processId": p.id,
        "candidateId": p.candidate_id,
        "currentStage": p.current_stage,
        "doj": p.doj.isoformat() if p.doj else None,
        "lastModifiedAt": p.last_modified_at.isoformat(),
        "version": p.version,
    }


def task_dict(t: OnboardingTask) -> dict[str, Any]:
    return {
        "taskId": t.id,
        "processId": t.process_id,
        "type": t.task_type,
        "status": t.status,
        "assigneeType": t.assignee_type,
        "lastModifiedAt": t.last_modified_at.isoformat(),
        "version": t.version,
    }


def activity_dict(a: OnboardingActivity) -> dict[str, Any]:
    return {
        "activityId": a.id,
        "processId": a.process_id,
        "activityType": a.activity_type,
        "status": a.status,
        "lastModifiedAt": a.last_modified_at.isoformat(),
        "version": a.version,
    }


def document_dict(d: Document) -> dict[str, Any]:
    return {
        "documentId": d.id,
        "candidateId": d.candidate_id,
        "docType": d.doc_type,
        "status": d.status,
        "lastModifiedAt": d.last_modified_at.isoformat(),
        "version": d.version,
    }


SERIALIZERS = {
    Candidate: candidate_dict,
    OnboardingProcess: process_dict,
    OnboardingTask: task_dict,
    OnboardingActivity: activity_dict,
    Document: document_dict,
}

FILTER_FIELDS = {
    Candidate: {"candidateId": "id", "status": "status", "lastModifiedAt": "last_modified_at"},
    OnboardingProcess: {
        "processId": "id",
        "candidateId": "candidate_id",
        "currentStage": "current_stage",
        "lastModifiedAt": "last_modified_at",
    },
    OnboardingTask: {
        "taskId": "id",
        "processId": "process_id",
        "status": "status",
        "lastModifiedAt": "last_modified_at",
    },
    OnboardingActivity: {
        "activityId": "id",
        "processId": "process_id",
        "status": "status",
        "lastModifiedAt": "last_modified_at",
    },
    Document: {
        "documentId": "id",
        "candidateId": "candidate_id",
        "status": "status",
        "lastModifiedAt": "last_modified_at",
    },
}

ENTITY_MAP = {
    "Candidate": Candidate,
    "OnboardingProcess": OnboardingProcess,
    "OnboardingTask": OnboardingTask,
    "OnboardingActivity": OnboardingActivity,
    "Document": Document,
}


def add_event(store: JsonStore, entity_name: str, entity_id: str, action: str, payload: dict | None = None) -> None:
    store.add_event(entity_name=entity_name, entity_id=entity_id, action=action, payload=payload)


def _list_model(
    model,
    request: Request,
    store: JsonStore,
    top: int,
    skip: int,
    orderby: str | None,
    filter_expr: str | None,
):
    direction = parse_orderby(orderby)
    rows = apply_filter(store.list_entities(model), filter_expr, FILTER_FIELDS[model])
    total = len(rows)
    rows = sorted(
        rows,
        key=lambda row: (
            row.last_modified_at.timestamp() * (-1 if direction == "desc" else 1),
            row.version,
            row.id,
        ),
    )
    rows = rows[skip : skip + top]
    next_url = str(request.url.include_query_params(**{"$skip": skip + top, "$top": top})) if skip + top < total else None
    return to_collection_response([SERIALIZERS[model](row) for row in rows], total, next_url)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/odata/v2/Candidate")
def list_candidates(
    request: Request,
    store: JsonStore = Depends(get_store),
    top: int = Query(50, alias="$top", ge=1, le=500),
    skip: int = Query(0, alias="$skip", ge=0),
    orderby: str | None = Query(None, alias="$orderby"),
    filter_expr: str | None = Query(None, alias="$filter"),
):
    return _list_model(Candidate, request, store, top, skip, orderby, filter_expr)


@app.get("/odata/v2/OnboardingProcess")
def list_processes(
    request: Request,
    store: JsonStore = Depends(get_store),
    top: int = Query(50, alias="$top", ge=1, le=500),
    skip: int = Query(0, alias="$skip", ge=0),
    orderby: str | None = Query(None, alias="$orderby"),
    filter_expr: str | None = Query(None, alias="$filter"),
):
    return _list_model(OnboardingProcess, request, store, top, skip, orderby, filter_expr)


@app.get("/odata/v2/OnboardingTask")
def list_tasks(
    request: Request,
    store: JsonStore = Depends(get_store),
    top: int = Query(50, alias="$top", ge=1, le=500),
    skip: int = Query(0, alias="$skip", ge=0),
    orderby: str | None = Query(None, alias="$orderby"),
    filter_expr: str | None = Query(None, alias="$filter"),
):
    return _list_model(OnboardingTask, request, store, top, skip, orderby, filter_expr)


@app.get("/odata/v2/OnboardingActivity")
def list_activities(
    request: Request,
    store: JsonStore = Depends(get_store),
    top: int = Query(50, alias="$top", ge=1, le=500),
    skip: int = Query(0, alias="$skip", ge=0),
    orderby: str | None = Query(None, alias="$orderby"),
    filter_expr: str | None = Query(None, alias="$filter"),
):
    return _list_model(OnboardingActivity, request, store, top, skip, orderby, filter_expr)


@app.get("/odata/v2/Document")
def list_documents(
    request: Request,
    store: JsonStore = Depends(get_store),
    top: int = Query(50, alias="$top", ge=1, le=500),
    skip: int = Query(0, alias="$skip", ge=0),
    orderby: str | None = Query(None, alias="$orderby"),
    filter_expr: str | None = Query(None, alias="$filter"),
):
    return _list_model(Document, request, store, top, skip, orderby, filter_expr)


@app.get("/odata/v2/Candidate('{candidate_id}')")
def get_candidate(candidate_id: str, store: JsonStore = Depends(get_store)):
    candidate = store.get_entity(Candidate, candidate_id)
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    return to_single_response(candidate_dict(candidate))


@app.get("/odata/v2/OnboardingProcess('{process_id}')")
def get_process(process_id: str, store: JsonStore = Depends(get_store)):
    process = store.get_entity(OnboardingProcess, process_id)
    if not process:
        raise HTTPException(status_code=404, detail="OnboardingProcess not found")
    return to_single_response(process_dict(process))


@app.get("/odata/v2/OnboardingTask('{task_id}')")
def get_task(task_id: str, store: JsonStore = Depends(get_store)):
    task = store.get_entity(OnboardingTask, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="OnboardingTask not found")
    return to_single_response(task_dict(task))


@app.get("/odata/v2/OnboardingActivity('{activity_id}')")
def get_activity(activity_id: str, store: JsonStore = Depends(get_store)):
    activity = store.get_entity(OnboardingActivity, activity_id)
    if not activity:
        raise HTTPException(status_code=404, detail="OnboardingActivity not found")
    return to_single_response(activity_dict(activity))


@app.get("/odata/v2/Document('{document_id}')")
def get_document(document_id: str, store: JsonStore = Depends(get_store)):
    document = store.get_entity(Document, document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    return to_single_response(document_dict(document))


@app.patch("/odata/v2/Candidate('{candidate_id}')")
def patch_candidate(candidate_id: str, payload: dict[str, Any], store: JsonStore = Depends(get_store)):
    candidate = store.get_entity(Candidate, candidate_id)
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    process = store.get_process_by_candidate(candidate_id)

    if "status" in payload:
        candidate.status = payload["status"]
    if payload.get("processStage") and process:
        try:
            validate_stage_transition(process.current_stage, payload["processStage"])
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        process.current_stage = payload["processStage"]
        process.last_modified_at = utcnow()
        process.version += 1

    candidate.last_modified_at = utcnow()
    candidate.version += 1
    add_event(store, "Candidate", candidate.id, "PATCH", payload)
    if process:
        add_event(store, "OnboardingProcess", process.id, "PATCH", {"currentStage": process.current_stage})
    store.save()
    return to_single_response(candidate_dict(candidate))


@app.patch("/odata/v2/OnboardingProcess('{process_id}')")
def patch_process(process_id: str, payload: dict[str, Any], store: JsonStore = Depends(get_store)):
    process = store.get_entity(OnboardingProcess, process_id)
    if not process:
        raise HTTPException(status_code=404, detail="OnboardingProcess not found")

    if "currentStage" in payload:
        try:
            validate_stage_transition(process.current_stage, payload["currentStage"])
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        process.current_stage = payload["currentStage"]
    if "doj" in payload:
        process.doj = date.fromisoformat(payload["doj"]) if payload["doj"] else None

    process.last_modified_at = utcnow()
    process.version += 1
    add_event(store, "OnboardingProcess", process.id, "PATCH", payload)
    store.save()
    return to_single_response(process_dict(process))


@app.patch("/odata/v2/OnboardingTask('{task_id}')")
def patch_task(task_id: str, payload: dict[str, Any], store: JsonStore = Depends(get_store)):
    task = store.get_entity(OnboardingTask, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="OnboardingTask not found")
    process = store.get_entity(OnboardingProcess, task.process_id)

    if "status" in payload:
        status = payload["status"]
        if status not in TASK_STATUSES:
            raise HTTPException(status_code=400, detail="Invalid task status")
        task.status = status

    if payload.get("processStage"):
        try:
            validate_stage_transition(process.current_stage, payload["processStage"])
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        process.current_stage = payload["processStage"]
    elif task.status == "COMPLETED":
        nxt = next_stage(process.current_stage)
        if nxt:
            process.current_stage = nxt

    task.last_modified_at = utcnow()
    task.version += 1
    process.last_modified_at = utcnow()
    process.version += 1
    add_event(store, "OnboardingTask", task.id, "PATCH", payload)
    add_event(store, "OnboardingProcess", process.id, "PATCH", {"currentStage": process.current_stage})
    store.save()
    return to_single_response(task_dict(task))


@app.get("/odata/v2/delta")
def delta(
    entity: str,
    since: str,
    sinceVersion: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    store: JsonStore = Depends(get_store),
):
    model = ENTITY_MAP.get(entity)
    if not model:
        raise HTTPException(status_code=400, detail="Unknown entity")
    since_dt = parse_iso8601(since)
    rows = [
        row
        for row in store.list_entities(model)
        if row.last_modified_at > since_dt or (row.last_modified_at == since_dt and row.version > sinceVersion)
    ]
    rows = sorted(rows, key=lambda row: (row.last_modified_at, row.version, row.id))[:limit]
    next_since = since
    next_version = sinceVersion
    if rows:
        next_since = rows[-1].last_modified_at.isoformat()
        next_version = rows[-1].version
    return {
        "entity": entity,
        "since": since,
        "sinceVersion": sinceVersion,
        "limit": limit,
        "value": [SERIALIZERS[model](row) for row in rows],
        "next": {"since": next_since, "sinceVersion": next_version},
    }


@app.post("/admin/seed", dependencies=[Depends(require_admin_token)])
def admin_seed(store: JsonStore = Depends(get_store)):
    if store.get_entity(Candidate, "CAND_001"):
        return {"seeded": False, "reason": "already seeded"}

    candidate = Candidate(
        id="CAND_001",
        first_name="Peeyush",
        last_name="Kumar",
        email="peeyush.kumar@example.com",
        status="ONBOARDING_IN_PROGRESS",
    )
    process = OnboardingProcess(id="ONB_001", candidate_id="CAND_001", current_stage="OFFER_ACCEPTED")
    tasks = [
        OnboardingTask(id="TASK_001", process_id="ONB_001", task_type="PHV", status="PENDING"),
        OnboardingTask(id="TASK_002", process_id="ONB_001", task_type="DOCUMENT_VERIFICATION", status="PENDING"),
        OnboardingTask(id="TASK_003", process_id="ONB_001", task_type="DOJ_CONFIRMATION", status="PENDING"),
    ]
    store.add_entity(candidate)
    store.add_entity(process)
    for task in tasks:
        store.add_entity(task)
    store.add_entity(OnboardingActivity(id="ACT_001", process_id="ONB_001", activity_type="INIT", status="OPEN"))
    store.add_entity(Document(id="DOC_001", candidate_id="CAND_001", doc_type="ID_PROOF", status="PENDING"))
    add_event(store, "Candidate", candidate.id, "CREATE", candidate_dict(candidate))
    add_event(store, "OnboardingProcess", process.id, "CREATE", process_dict(process))
    store.save()
    return {"seeded": True}


@app.post("/admin/simulate/tick", dependencies=[Depends(require_admin_token)])
def admin_tick(store: JsonStore = Depends(get_store)):
    pending = [item for item in store.list_entities(OnboardingTask) if item.status != "COMPLETED"]
    task = min(pending, key=lambda item: item.id, default=None)
    if not task:
        return {"advanced": False, "reason": "no pending tasks"}
    task.status = "COMPLETED"
    task.last_modified_at = utcnow()
    task.version += 1
    process = store.get_entity(OnboardingProcess, task.process_id)
    nxt = next_stage(process.current_stage)
    if nxt:
        process.current_stage = nxt
        process.last_modified_at = utcnow()
        process.version += 1
    add_event(store, "OnboardingTask", task.id, "SIM_TICK", {"status": "COMPLETED"})
    add_event(store, "OnboardingProcess", process.id, "SIM_TICK", {"currentStage": process.current_stage})
    store.save()
    return {"advanced": True, "taskId": task.id, "processId": process.id, "currentStage": process.current_stage}
