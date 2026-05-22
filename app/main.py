from __future__ import annotations

from datetime import date
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db, utcnow
from app.models import Candidate, Document, EventLog, OnboardingActivity, OnboardingProcess, OnboardingTask
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
    Candidate: {"candidateId": Candidate.id, "status": Candidate.status, "lastModifiedAt": Candidate.last_modified_at},
    OnboardingProcess: {
        "processId": OnboardingProcess.id,
        "candidateId": OnboardingProcess.candidate_id,
        "currentStage": OnboardingProcess.current_stage,
        "lastModifiedAt": OnboardingProcess.last_modified_at,
    },
    OnboardingTask: {
        "taskId": OnboardingTask.id,
        "processId": OnboardingTask.process_id,
        "status": OnboardingTask.status,
        "lastModifiedAt": OnboardingTask.last_modified_at,
    },
    OnboardingActivity: {
        "activityId": OnboardingActivity.id,
        "processId": OnboardingActivity.process_id,
        "status": OnboardingActivity.status,
        "lastModifiedAt": OnboardingActivity.last_modified_at,
    },
    Document: {
        "documentId": Document.id,
        "candidateId": Document.candidate_id,
        "status": Document.status,
        "lastModifiedAt": Document.last_modified_at,
    },
}

ENTITY_MAP = {
    "Candidate": Candidate,
    "OnboardingProcess": OnboardingProcess,
    "OnboardingTask": OnboardingTask,
    "OnboardingActivity": OnboardingActivity,
    "Document": Document,
}


def add_event(db: Session, entity_name: str, entity_id: str, action: str, payload: dict | None = None) -> None:
    db.add(EventLog(entity_name=entity_name, entity_id=entity_id, action=action, payload=payload))


def _list_model(
    model,
    request: Request,
    db: Session,
    top: int,
    skip: int,
    orderby: str | None,
    filter_expr: str | None,
):
    direction = parse_orderby(orderby)
    query = apply_filter(select(model), filter_expr, FILTER_FIELDS[model])
    count_query = select(func.count()).select_from(query.subquery())
    total = db.execute(count_query).scalar_one()

    order_col = model.last_modified_at.asc() if direction == "asc" else model.last_modified_at.desc()
    rows = db.execute(query.order_by(order_col, model.version.asc(), model.id.asc()).offset(skip).limit(top)).scalars().all()
    next_url = str(request.url.include_query_params(**{"$skip": skip + top, "$top": top})) if skip + top < total else None
    return to_collection_response([SERIALIZERS[model](row) for row in rows], total, next_url)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/odata/v2/Candidate")
def list_candidates(
    request: Request,
    db: Session = Depends(get_db),
    top: int = Query(50, alias="$top", ge=1, le=500),
    skip: int = Query(0, alias="$skip", ge=0),
    orderby: str | None = Query(None, alias="$orderby"),
    filter_expr: str | None = Query(None, alias="$filter"),
):
    return _list_model(Candidate, request, db, top, skip, orderby, filter_expr)


@app.get("/odata/v2/OnboardingProcess")
def list_processes(
    request: Request,
    db: Session = Depends(get_db),
    top: int = Query(50, alias="$top", ge=1, le=500),
    skip: int = Query(0, alias="$skip", ge=0),
    orderby: str | None = Query(None, alias="$orderby"),
    filter_expr: str | None = Query(None, alias="$filter"),
):
    return _list_model(OnboardingProcess, request, db, top, skip, orderby, filter_expr)


@app.get("/odata/v2/OnboardingTask")
def list_tasks(
    request: Request,
    db: Session = Depends(get_db),
    top: int = Query(50, alias="$top", ge=1, le=500),
    skip: int = Query(0, alias="$skip", ge=0),
    orderby: str | None = Query(None, alias="$orderby"),
    filter_expr: str | None = Query(None, alias="$filter"),
):
    return _list_model(OnboardingTask, request, db, top, skip, orderby, filter_expr)


@app.get("/odata/v2/OnboardingActivity")
def list_activities(
    request: Request,
    db: Session = Depends(get_db),
    top: int = Query(50, alias="$top", ge=1, le=500),
    skip: int = Query(0, alias="$skip", ge=0),
    orderby: str | None = Query(None, alias="$orderby"),
    filter_expr: str | None = Query(None, alias="$filter"),
):
    return _list_model(OnboardingActivity, request, db, top, skip, orderby, filter_expr)


@app.get("/odata/v2/Document")
def list_documents(
    request: Request,
    db: Session = Depends(get_db),
    top: int = Query(50, alias="$top", ge=1, le=500),
    skip: int = Query(0, alias="$skip", ge=0),
    orderby: str | None = Query(None, alias="$orderby"),
    filter_expr: str | None = Query(None, alias="$filter"),
):
    return _list_model(Document, request, db, top, skip, orderby, filter_expr)


@app.get("/odata/v2/Candidate('{candidate_id}')")
def get_candidate(candidate_id: str, db: Session = Depends(get_db)):
    candidate = db.get(Candidate, candidate_id)
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    return to_single_response(candidate_dict(candidate))


@app.get("/odata/v2/OnboardingProcess('{process_id}')")
def get_process(process_id: str, db: Session = Depends(get_db)):
    process = db.get(OnboardingProcess, process_id)
    if not process:
        raise HTTPException(status_code=404, detail="OnboardingProcess not found")
    return to_single_response(process_dict(process))


@app.get("/odata/v2/OnboardingTask('{task_id}')")
def get_task(task_id: str, db: Session = Depends(get_db)):
    task = db.get(OnboardingTask, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="OnboardingTask not found")
    return to_single_response(task_dict(task))


@app.get("/odata/v2/OnboardingActivity('{activity_id}')")
def get_activity(activity_id: str, db: Session = Depends(get_db)):
    activity = db.get(OnboardingActivity, activity_id)
    if not activity:
        raise HTTPException(status_code=404, detail="OnboardingActivity not found")
    return to_single_response(activity_dict(activity))


@app.get("/odata/v2/Document('{document_id}')")
def get_document(document_id: str, db: Session = Depends(get_db)):
    document = db.get(Document, document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    return to_single_response(document_dict(document))


@app.patch("/odata/v2/Candidate('{candidate_id}')")
def patch_candidate(candidate_id: str, payload: dict[str, Any], db: Session = Depends(get_db)):
    candidate = db.get(Candidate, candidate_id)
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    process = db.execute(select(OnboardingProcess).where(OnboardingProcess.candidate_id == candidate_id)).scalar_one_or_none()

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
    add_event(db, "Candidate", candidate.id, "PATCH", payload)
    if process:
        add_event(db, "OnboardingProcess", process.id, "PATCH", {"currentStage": process.current_stage})
    db.commit()
    db.refresh(candidate)
    return to_single_response(candidate_dict(candidate))


@app.patch("/odata/v2/OnboardingProcess('{process_id}')")
def patch_process(process_id: str, payload: dict[str, Any], db: Session = Depends(get_db)):
    process = db.get(OnboardingProcess, process_id)
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
    add_event(db, "OnboardingProcess", process.id, "PATCH", payload)
    db.commit()
    db.refresh(process)
    return to_single_response(process_dict(process))


@app.patch("/odata/v2/OnboardingTask('{task_id}')")
def patch_task(task_id: str, payload: dict[str, Any], db: Session = Depends(get_db)):
    task = db.get(OnboardingTask, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="OnboardingTask not found")
    process = db.get(OnboardingProcess, task.process_id)

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
    add_event(db, "OnboardingTask", task.id, "PATCH", payload)
    add_event(db, "OnboardingProcess", process.id, "PATCH", {"currentStage": process.current_stage})
    db.commit()
    db.refresh(task)
    return to_single_response(task_dict(task))


@app.get("/odata/v2/delta")
def delta(
    entity: str,
    since: str,
    sinceVersion: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    model = ENTITY_MAP.get(entity)
    if not model:
        raise HTTPException(status_code=400, detail="Unknown entity")
    since_dt = parse_iso8601(since)
    query = (
        select(model)
        .where((model.last_modified_at > since_dt) | ((model.last_modified_at == since_dt) & (model.version > sinceVersion)))
        .order_by(model.last_modified_at.asc(), model.version.asc(), model.id.asc())
        .limit(limit)
    )
    rows = db.execute(query).scalars().all()
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
def admin_seed(db: Session = Depends(get_db)):
    if db.get(Candidate, "CAND_001"):
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
    db.add(candidate)
    db.add(process)
    db.add_all(tasks)
    db.add(OnboardingActivity(id="ACT_001", process_id="ONB_001", activity_type="INIT", status="OPEN"))
    db.add(Document(id="DOC_001", candidate_id="CAND_001", doc_type="ID_PROOF", status="PENDING"))
    db.flush()
    add_event(db, "Candidate", candidate.id, "CREATE", candidate_dict(candidate))
    add_event(db, "OnboardingProcess", process.id, "CREATE", process_dict(process))
    db.commit()
    return {"seeded": True}


@app.post("/admin/simulate/tick", dependencies=[Depends(require_admin_token)])
def admin_tick(db: Session = Depends(get_db)):
    task = (
        db.execute(select(OnboardingTask).where(OnboardingTask.status != "COMPLETED").order_by(OnboardingTask.id.asc()).limit(1))
        .scalar_one_or_none()
    )
    if not task:
        return {"advanced": False, "reason": "no pending tasks"}
    task.status = "COMPLETED"
    task.last_modified_at = utcnow()
    task.version += 1
    process = db.get(OnboardingProcess, task.process_id)
    nxt = next_stage(process.current_stage)
    if nxt:
        process.current_stage = nxt
        process.last_modified_at = utcnow()
        process.version += 1
    add_event(db, "OnboardingTask", task.id, "SIM_TICK", {"status": "COMPLETED"})
    add_event(db, "OnboardingProcess", process.id, "SIM_TICK", {"currentStage": process.current_stage})
    db.commit()
    return {"advanced": True, "taskId": task.id, "processId": process.id, "currentStage": process.current_stage}
