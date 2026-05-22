from __future__ import annotations

STAGES = [
    "OFFER_ACCEPTED",
    "PHV_PENDING",
    "PHV_COMPLETED",
    "DOCS_PENDING",
    "DOCS_VERIFIED",
    "DOJ_CONFIRMED",
    "ACTIVE_EMPLOYEE",
]

TASK_STATUSES = {"PENDING", "IN_PROGRESS", "COMPLETED", "BLOCKED", "CANCELLED"}


def validate_stage_transition(current: str, nxt: str) -> None:
    if current == nxt:
        return
    if current not in STAGES or nxt not in STAGES:
        raise ValueError("Invalid lifecycle stage")
    current_index = STAGES.index(current)
    next_index = STAGES.index(nxt)
    if next_index != current_index + 1:
        raise ValueError(f"Illegal stage transition: {current} -> {nxt}")


def next_stage(current: str) -> str | None:
    if current not in STAGES:
        return None
    idx = STAGES.index(current)
    if idx + 1 >= len(STAGES):
        return None
    return STAGES[idx + 1]
