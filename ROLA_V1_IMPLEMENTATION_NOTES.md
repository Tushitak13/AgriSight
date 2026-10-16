# AgriSight ROLA v1 overlay patch

## Scope

This patch adds a pure-Python response assessment service, Pydantic request/result contracts, and isolated unit tests. It is intentionally an overlay and does not replace existing AgriSight files.

- `backend/app/services/learning/rola_engine.py`
- `backend/app/schemas/rola_schema.py`
- `backend/tests/test_rola_engine.py`

## Safety properties

- No change to ACI, CRI, sensor reliability, existing endpoints, or farmer-facing recommendations.
- No database persistence or API route is wired in this first patch because the supplied ZIP contains only the CRI/ACI patch files, not the complete backend's DB setup, models, and route registration.
- `recalibration_applied` and `recommendation_or_aci_modified` are always false.
- A single error is never used to declare a sensor faulty.
- Units, timestamps, depth, observation quality, event logging, independence, and context calibration are checked explicitly.
- Qualitative manual observations can be stored, but cannot be treated as numeric moisture measurements.
- A same-device operational sensor can produce a monitoring error but does not count as independent verification.

## Data integration plan

Use `RolaEventCreate` and `RolaObservationCreate` as initial schema contracts. When integrating with the complete backend, persist separate event and observation records (or equivalent tables) so original evidence is immutable and provenance is preserved. The assessment can be stored as a derived record. Do not mutate existing `Experience` rows to represent sensor-response diagnostics.

## Validation

Run from the backend directory:

```powershell
$env:PYTHONPATH = "."
python -m pytest -q tests/test_rola_engine.py
python -m pytest -q
```

The full suite cannot be verified from this overlay alone: the uploaded `agrisight_cri_aci_patch(1).zip` contains seven files and omits the backend database, models, app initialization, and most existing tests. Apply the overlay to the full backend before running the complete regression suite.
