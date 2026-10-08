from fastapi.testclient import TestClient

from ops_ai.api import app
from ops_ai.schemas import TriageDraft

client = TestClient(app)


def test_service_ticket_requires_review_before_dispatch(tmp_path, monkeypatch):
    monkeypatch.setenv("OPS_DB_PATH", str(tmp_path / "ops.db"))
    monkeypatch.setenv("OPS_LLM_PROVIDER", "mock")
    response = client.post(
        "/v1/triage",
        json={"description": "Charging will not start", "diagnostic_code": "S-CHG-201"},
    )
    assert response.status_code == 200
    ticket = response.json()
    assert ticket["recommended_team"] == "charging"
    assert client.get(f"/v1/tickets/{ticket['ticket_id']}").json()["status"] == "awaiting_review"
    review = client.post(
        f"/v1/tickets/{ticket['ticket_id']}/review",
        json={"approved": True, "team": "charging", "note": "Verified code"},
    )
    assert review.status_code == 200
    assert review.json()["status"] == "dispatched_simulated"
    queue = client.get("/v1/work-orders", params={"team": "charging"})
    assert queue.status_code == 200
    assert any(item["ticket_id"] == ticket["ticket_id"] for item in queue.json()["items"])


def test_critical_report_cannot_be_downgraded(tmp_path, monkeypatch):
    monkeypatch.setenv("OPS_DB_PATH", str(tmp_path / "ops.db"))
    monkeypatch.setattr(
        "ops_ai.service.generate",
        lambda *args: TriageDraft(
            category="other",
            priority="routine",
            recommended_team="general_service",
            diagnostic_summary="No issue",
            evidence=[],
            customer_reply="Ride to a workshop",
            review_required=False,
            review_reason="",
        ),
    )
    response = client.post("/v1/triage", json={"description": "Smoke is coming from the battery"})
    assert response.status_code == 200
    ticket = response.json()
    assert ticket["priority"] == "critical"
    assert ticket["recommended_team"] == "battery"
    assert ticket["review_required"] is True
    assert ticket["evidence"][0]["source_id"] == "KB-BAT-102"
    assert "Ride to a workshop" not in ticket["customer_reply"]


def test_unknown_report_needs_human_review(tmp_path, monkeypatch):
    monkeypatch.setenv("OPS_DB_PATH", str(tmp_path / "ops.db"))
    monkeypatch.setenv("OPS_LLM_PROVIDER", "mock")
    response = client.post(
        "/v1/triage",
        json={
            "description": "Unknown warning code X-999 appeared with no symptoms",
            "diagnostic_code": "X-999",
        },
    )
    assert response.status_code == 200
    assert response.json()["recommended_team"] == "human_review"


def test_unretrieved_citation_forces_review(tmp_path, monkeypatch):
    monkeypatch.setenv("OPS_DB_PATH", str(tmp_path / "ops.db"))
    monkeypatch.setattr(
        "ops_ai.service.generate",
        lambda *args: TriageDraft(
            category="charging",
            priority="routine",
            recommended_team="charging",
            diagnostic_summary="Unsupported",
            evidence=[{"source_id": "KB-DOES-NOT-EXIST", "reason": "Made up"}],
            customer_reply="We found the cause",
            review_required=False,
            review_reason="",
        ),
    )
    response = client.post(
        "/v1/triage",
        json={"description": "Charging will not start", "diagnostic_code": "S-CHG-201"},
    )
    assert response.status_code == 200
    assert response.json()["recommended_team"] == "human_review"
    assert response.json()["evidence"] == []


def test_comparison_uses_same_evidence_without_creating_work_orders(tmp_path, monkeypatch):
    monkeypatch.setenv("OPS_DB_PATH", str(tmp_path / "ops.db"))
    monkeypatch.setenv("OPS_LLM_PROVIDER", "mock")
    response = client.post(
        "/v1/compare",
        json={
            "description": "App pairing fails over Bluetooth",
            "diagnostic_code": "S-CON-501",
            "versions": ["v1", "v2"],
        },
    )
    assert response.status_code == 200
    left, right = response.json()
    assert left["retrieval_ids"] == right["retrieval_ids"]
    assert left["ticket_id"] != right["ticket_id"]
    assert client.get(f"/v1/tickets/{left['ticket_id']}").status_code == 404
