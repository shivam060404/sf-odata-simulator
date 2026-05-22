# sf-odata-simulator

SuccessFactors (SF) **OData-flavored onboarding simulator** for prototyping polling-based ingestion and agentic onboarding automation.

## Goals
- Simulate SuccessFactors-like onboarding entities and workflows (post-recruitment, onboarding only)
- Provide OData-ish endpoints under `/odata/v2`
- Support delta sync for polling-based ingestion

## Quickstart (local)

### 1) Requirements
- Python 3.11+
- Docker (for PostgreSQL)

### 2) Start PostgreSQL
```bash
docker compose up -d db
```

### 3) Create venv + install deps
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 4) Run migrations + start API
```bash
alembic upgrade head
uvicorn app.main:app --reload
```

## Environment variables
- `DATABASE_URL` (e.g. `postgresql+psycopg://postgres:postgres@localhost:5432/sf_odata_sim`)
- `API_TOKEN` (bearer token for admin endpoints)

## API
Base: `/odata/v2`
- `/Candidate`
- `/OnboardingProcess`
- `/OnboardingTask`
- `/Document`
- `/OnboardingActivity`
- `/delta`

Admin:
- `POST /admin/seed`
- `POST /admin/simulate/tick`

## OData-flavored query support
- `$top`, `$skip`
- `$orderby=lastModifiedAt asc|desc`
- minimal `$filter`:
  - `eq`
  - `gt` (only on `lastModifiedAt`)
  - `and`

## Response shapes
- Collection:
```json
{
  "value": [],
  "count": 0,
  "next": null
}
```
- Singleton:
```json
{
  "value": {}
}
```
