
from sqlalchemy import select

from tests.conftest import GOOD
from app.database.database import Base
from app.models.recalibration import RecalibrationAssessment


def audit_count(client):
    Session = client.test_session_factory
    with Session() as db:
        return db.query(RecalibrationAssessment).count()


def non_rola_state(client):
    excluded = {
        "recalibration_assessments",
        "recalibration_candidates",
    }
    Session = client.test_session_factory

    with Session() as db:
        snapshot = {}

        for table in Base.metadata.sorted_tables:
            if table.name in excluded:
                continue

            rows = db.execute(select(table)).all()
            snapshot[table.name] = [tuple(row) for row in rows]

        return snapshot


def create_experience(client, *, source="real", completed=True):
    response = client.post(
        "/api/experiences",
        json={
            "condition": GOOD,
            "intervention": "light_irrigation",
            "source": source,
        },
    )
    assert response.status_code == 201
    experience_id = response.json()["id"]

    if completed:
        outcome = client.patch(
            f"/api/experiences/{experience_id}/outcome",
            json={"status": "SUCCESSFUL", "after": GOOD},
        )
        assert outcome.status_code == 200

    return experience_id


def valid_assessment(**overrides):
    payload = {
        "predicted_value": 40.0,
        "predicted_unit": "%VWC",
        "predicted_at": "2026-10-14T10:00:00Z",
        "observed_value": 34.0,
        "observed_unit": "%VWC",
        "observed_at": "2026-10-14T12:00:00Z",
        "source_type": "reference_measurement",
        "value_kind": "numeric_measurement",
        "independent_of_target_sensor": True,
        "predicted_depth_cm": 10.0,
        "observed_depth_cm": 10.0,
        "event_recorded": True,
        "event_timing_trustworthy": True,
        "model_calibrated_for_context": True,
        "observation_quality_ok": True,
    }
    payload.update(overrides)
    return payload


def test_stateless_assessment_keeps_existing_response(client):
    before = non_rola_state(client)

    response = client.post(
        "/api/rola/assess",
        json=valid_assessment(),
    )

    assert response.status_code == 200
    result = response.json()
    assert result["comparable"] is True
    assert result["signed_error"] == -6.0
    assert result["attribution_eligible"] is True
    assert result["recalibration_applied"] is False
    assert result["recommendation_or_aci_modified"] is False

    assert audit_count(client) == 0
    assert non_rola_state(client) == before


def test_assessment_can_be_persisted_once_for_completed_real_experience(client):
    experience_id = create_experience(client)
    payload = valid_assessment(experience_id=experience_id)
    before = non_rola_state(client)

    first = client.post("/api/rola/assess", json=payload)

    assert first.status_code == 200
    assert first.json()["signed_error"] == -6.0
    assert audit_count(client) == 1
    assert non_rola_state(client) == before

    second = client.post("/api/rola/assess", json=payload)

    assert second.status_code == 409
    assert audit_count(client) == 1
    assert non_rola_state(client) == before


def test_persistence_rejects_unknown_experience(client):
    response = client.post(
        "/api/rola/assess",
        json=valid_assessment(experience_id=99999),
    )

    assert response.status_code == 404
    assert audit_count(client) == 0


def test_persistence_rejects_pending_experience(client):
    experience_id = create_experience(client, completed=False)

    response = client.post(
        "/api/rola/assess",
        json=valid_assessment(experience_id=experience_id),
    )

    assert response.status_code == 409
    assert audit_count(client) == 0


def test_persistence_rejects_seed_experience(client):
    experience_id = create_experience(client, source="seed")

    response = client.post(
        "/api/rola/assess",
        json=valid_assessment(experience_id=experience_id),
    )

    assert response.status_code == 409
    assert audit_count(client) == 0


def test_noncomparable_assessment_does_not_become_attribution_eligible(client):
    experience_id = create_experience(client)
    before = non_rola_state(client)

    payload = valid_assessment(
        experience_id=experience_id,
        observed_unit="kPa",
    )

    response = client.post("/api/rola/assess", json=payload)

    assert response.status_code == 200
    result = response.json()
    assert result["comparable"] is False
    assert result["attribution_eligible"] is False
    assert "unit_mismatch" in result["reasons"]
    assert result["recalibration_applied"] is False
    assert result["recommendation_or_aci_modified"] is False

    # Non-comparable assessments are audited but do not alter other tables.
    assert audit_count(client) == 1
    assert non_rola_state(client) == before

    duplicate = client.post("/api/rola/assess", json=payload)

    assert duplicate.status_code == 409
    assert audit_count(client) == 1
    assert non_rola_state(client) == before
