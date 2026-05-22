from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import HTTPException


def parse_iso8601(value: str) -> datetime:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid timestamp: {value}") from exc


def parse_orderby(orderby: str | None):
    if not orderby:
        return "asc"
    pieces = orderby.strip().split()
    if len(pieces) != 2 or pieces[0] != "lastModifiedAt" or pieces[1] not in {"asc", "desc"}:
        raise HTTPException(status_code=400, detail="Only $orderby=lastModifiedAt asc|desc is supported")
    return pieces[1]


def apply_filter(rows: list[Any], filter_str: str | None, field_map: dict[str, str]):
    if not filter_str:
        return rows

    clauses: list[tuple[str, str, Any]] = []
    for part in [p.strip() for p in filter_str.split(" and ")]:
        if " eq " in part:
            field, raw = part.split(" eq ", 1)
            if field not in field_map:
                raise HTTPException(status_code=400, detail=f"Unsupported filter field: {field}")
            value = raw.strip().strip("'")
            clauses.append(("eq", field_map[field], value))
        elif " gt " in part:
            field, raw = part.split(" gt ", 1)
            if field != "lastModifiedAt":
                raise HTTPException(status_code=400, detail="gt is only supported for lastModifiedAt")
            clauses.append(("gt", field_map[field], parse_iso8601(raw.strip().strip("'"))))
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported filter expression: {part}")

    def matches(row: Any) -> bool:
        for op, attr, value in clauses:
            actual = getattr(row, attr)
            if op == "eq":
                if isinstance(actual, datetime):
                    value_dt = parse_iso8601(value) if isinstance(value, str) else value
                    if actual != value_dt:
                        return False
                elif actual != value:
                    return False
            elif op == "gt":
                if actual <= value:
                    return False
        return True

    return [row for row in rows if matches(row)]


def to_collection_response(value: list[dict], count: int, next_url: str | None) -> dict:
    return {"value": value, "count": count, "next": next_url}


def to_single_response(value: dict) -> dict:
    return {"value": value}
