from __future__ import annotations

from datetime import datetime, timedelta, timezone


def seed(client):
    response = client.post("/admin/seed", headers={"Authorization": "Bearer test-token"})
    assert response.status_code == 200


def test_lifecycle_transition_validation(client):
    seed(client)

    invalid = client.patch("/odata/v2/OnboardingProcess('ONB_001')", json={"currentStage": "DOCS_VERIFIED"})
    assert invalid.status_code == 400
    assert "Illegal stage transition" in invalid.json()["detail"]

    valid = client.patch("/odata/v2/OnboardingProcess('ONB_001')", json={"currentStage": "PHV_PENDING"})
    assert valid.status_code == 200
    assert valid.json()["value"]["currentStage"] == "PHV_PENDING"


def test_delta_sync_stable_cursor(client):
    seed(client)

    since = datetime.now(timezone.utc) - timedelta(days=1)
    first = client.get(
        "/odata/v2/delta",
        params={"entity": "OnboardingTask", "since": since.isoformat(), "sinceVersion": 0, "limit": 2},
    )
    assert first.status_code == 200
    first_payload = first.json()
    assert len(first_payload["value"]) == 2

    cursor = first_payload["next"]
    second = client.get(
        "/odata/v2/delta",
        params={
            "entity": "OnboardingTask",
            "since": cursor["since"],
            "sinceVersion": cursor["sinceVersion"],
            "limit": 2,
        },
    )
    assert second.status_code == 200
    second_payload = second.json()

    first_ids = [item["taskId"] for item in first_payload["value"]]
    second_ids = [item["taskId"] for item in second_payload["value"]]
    assert set(first_ids).isdisjoint(set(second_ids))


def test_deterministic_ordering_and_query(client):
    seed(client)

    collection = client.get(
        "/odata/v2/OnboardingTask",
        params={"$orderby": "lastModifiedAt asc", "$top": 3, "$skip": 0, "$filter": "processId eq 'ONB_001'"},
    )
    assert collection.status_code == 200
    payload = collection.json()
    assert payload["count"] == 3
    assert len(payload["value"]) == 3
    assert payload["next"] is None

    singleton = client.get("/odata/v2/Candidate('CAND_001')")
    assert singleton.status_code == 200
    assert singleton.json()["value"]["candidateId"] == "CAND_001"
