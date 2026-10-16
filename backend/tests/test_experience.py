"""Experience memory + similarity API tests."""
from tests.conftest import GOOD

COND = {"soil": 31, "temperature": 29, "humidity": 65, "rain": 0, "water": 1700, "light": 450}


def make(client, **over):
    body = dict(condition=COND, decision="irrigation_needed", intervention="light_irrigation",
                expected_soil_change=30.0)
    body.update(over)
    return client.post("/api/experiences", json=body)


# ---------------- memory
def test_create_pending_experience_computes_states(client):
    r = make(client)
    assert r.status_code == 201
    d = r.json()
    assert d["outcome_status"] is None and d["soil_change"] is None       # pending
    assert d["device_id"] == "esp32-01" and d["source"] == "real"
    assert d["condition_states"]["soil_state"] == "DRY"
    assert d["condition_states"]["rain_state"] == "NO_RAIN"


def test_create_with_outcome_computes_soil_change(client):
    d = make(client, outcome={"status": "SUCCESSFUL", "after": dict(COND, soil=63)}).json()
    assert d["outcome_status"] == "SUCCESSFUL" and d["soil_change"] == 32.0
    assert d["outcome_condition"]["soil"] == 63 and d["outcome_recorded_at"] is not None


def test_outcome_without_after_readings_has_no_soil_change(client):
    d = make(client, outcome={"status": "UNSUCCESSFUL"}).json()
    assert d["outcome_status"] == "UNSUCCESSFUL" and d["soil_change"] is None


def test_record_outcome_later_and_only_once(client):
    eid = make(client).json()["id"]
    r = client.patch(f"/api/experiences/{eid}/outcome",
                     json={"status": "PARTIALLY_SUCCESSFUL", "after": dict(COND, soil=52)})
    assert r.status_code == 200 and r.json()["soil_change"] == 21.0
    again = client.patch(f"/api/experiences/{eid}/outcome", json={"status": "SUCCESSFUL"})
    assert again.status_code == 409
    assert client.get(f"/api/experiences/{eid}").json()["outcome_status"] == "PARTIALLY_SUCCESSFUL"


def test_get_and_patch_unknown_id_404(client):
    assert client.get("/api/experiences/999").status_code == 404
    assert client.patch("/api/experiences/999/outcome", json={"status": "SUCCESSFUL"}).status_code == 404


def test_validation_rejects_bad_input(client):
    assert make(client, condition={"soil": 150}).status_code == 422                 # out of range
    assert make(client, condition={}).status_code == 422                            # empty condition
    assert make(client, condition={"soil": 30, "temperature": "hot"}).status_code == 422
    assert make(client, intervention="Light Irrigation!").status_code == 422        # bad name
    assert make(client, intervention="").status_code == 422
    assert make(client, outcome={"status": "GREAT"}).status_code == 422             # unknown status
    assert make(client, outcome={"status": "SUCCESSFUL", "after": {"soil": -5}}).status_code == 422
    assert make(client, source="fake").status_code == 422


def test_partial_condition_is_stored(client):
    d = make(client, condition={"soil": 30, "temperature": 28}).json()
    assert d["condition"] == {"soil": 30, "temperature": 28}
    assert set(d["condition_states"]) == {"soil_state", "temperature_state"}


def test_list_filters_and_device_scoping(client):
    make(client)
    make(client, intervention="heavy_irrigation", outcome={"status": "SUCCESSFUL"})
    make(client, device_id="other-farm")
    assert len(client.get("/api/experiences").json()) == 2                           # default device only
    assert len(client.get("/api/experiences?device_id=other-farm").json()) == 1
    assert len(client.get("/api/experiences?intervention=heavy_irrigation").json()) == 1
    assert len(client.get("/api/experiences?has_outcome=true").json()) == 1
    assert len(client.get("/api/experiences?has_outcome=false").json()) == 1
    assert client.get("/api/experiences?source=bogus").status_code == 422


def test_delete_seed_only_removes_seed_rows(client):
    make(client, source="seed")
    make(client, source="seed")
    make(client)                                                                     # real
    assert client.delete("/api/experiences/seed").json() == {"deleted": 2}
    left = client.get("/api/experiences").json()
    assert len(left) == 1 and left[0]["source"] == "real"


# ---------------- similarity search
def seed_three(client):
    make(client, condition=dict(COND, soil=30), intervention="light_irrigation",
         outcome={"status": "SUCCESSFUL", "after": dict(COND, soil=55)})
    make(client, condition=dict(COND, soil=32), intervention="light_irrigation",
         outcome={"status": "UNSUCCESSFUL", "after": dict(COND, soil=33)})
    make(client, condition=dict(COND, soil=85, rain=60), intervention="monitor",
         outcome={"status": "SUCCESSFUL"})


def test_search_with_no_history(client):
    d = client.post("/api/similarity/search", json={"condition": COND}).json()
    assert d["has_history"] is False and d["historical_similarity"] == 0.0
    assert d["n_experiences_searched"] == 0 and d["matches"] == [] and d["intervention_summary"] == []


def test_search_ranks_nearest_first_and_excludes_dissimilar(client):
    seed_three(client)
    d = client.post("/api/similarity/search", json={"condition": dict(COND, soil=30)}).json()
    assert d["n_experiences_searched"] == 3
    assert d["n_matches"] == 2                                                       # wet+rainy one is too different
    sims = [m["similarity"] for m in d["matches"]]
    assert sims == sorted(sims, reverse=True)
    assert d["matches"][0]["experience"]["condition"]["soil"] == 30                  # exact soil match ranks first
    assert all(0 <= s <= 1 for s in sims)


def test_search_k_and_min_similarity(client):
    seed_three(client)
    one = client.post("/api/similarity/search", json={"condition": COND, "k": 1}).json()
    assert one["n_matches"] == 1
    everything = client.post("/api/similarity/search", json={"condition": COND, "min_similarity": 0}).json()
    assert everything["n_matches"] == 3


def test_search_historical_similarity_grows_with_more_matches(client):
    make(client, condition=COND, outcome={"status": "SUCCESSFUL"})
    one = client.post("/api/similarity/search", json={"condition": COND}).json()["historical_similarity"]
    make(client, condition=COND, outcome={"status": "SUCCESSFUL"})
    make(client, condition=COND, outcome={"status": "SUCCESSFUL"})
    three = client.post("/api/similarity/search", json={"condition": COND}).json()["historical_similarity"]
    assert one < three == 1.0


def test_search_intervention_summary(client):
    seed_three(client)
    d = client.post("/api/similarity/search", json={"condition": COND}).json()
    s = {x["intervention"]: x for x in d["intervention_summary"]}
    assert set(s) == {"light_irrigation"}                                            # monitor case not similar enough
    assert s["light_irrigation"]["n"] == 2
    assert 0.4 < s["light_irrigation"]["weighted_success"] < 0.6                     # one success, one failure
    assert s["light_irrigation"]["mean_soil_change"] == 13.0                         # (25 + 1) / 2


def test_search_only_with_outcome_and_pending_not_in_summary(client):
    make(client)                                                                     # pending
    make(client, outcome={"status": "SUCCESSFUL"})
    allm = client.post("/api/similarity/search", json={"condition": COND}).json()
    assert allm["n_matches"] == 2 and allm["intervention_summary"][0]["n"] == 1
    done = client.post("/api/similarity/search", json={"condition": COND, "only_with_outcome": True}).json()
    assert done["n_experiences_searched"] == 1


def test_search_is_scoped_to_device(client):
    make(client, device_id="other-farm", outcome={"status": "SUCCESSFUL"})
    d = client.post("/api/similarity/search", json={"condition": COND}).json()
    assert d["n_experiences_searched"] == 0
    other = client.post("/api/similarity/search", json={"condition": COND, "device_id": "other-farm"}).json()
    assert other["n_matches"] == 1


def test_search_validation(client):
    assert client.post("/api/similarity/search", json={"condition": {}}).status_code == 422
    assert client.post("/api/similarity/search", json={"condition": COND, "k": 0}).status_code == 422
    assert client.post("/api/similarity/search", json={"condition": COND, "min_similarity": 2}).status_code == 422


# ---------------- similarity to the live sensor reading
def test_current_404_without_readings(client):
    assert client.get("/api/similarity/current").status_code == 404


def test_current_uses_latest_reading(client):
    make(client, condition=GOOD, outcome={"status": "SUCCESSFUL"})
    client.post("/api/sensors/readings", json=GOOD)
    d = client.get("/api/similarity/current").json()
    assert d["query"]["soil"] == 37 and d["excluded_fields"] == []
    assert d["n_matches"] == 1 and d["matches"][0]["similarity"] == 1.0


def test_current_excludes_unreliable_sensor_from_query(client):
    make(client, condition=GOOD, outcome={"status": "SUCCESSFUL"})
    for soil in (40, 41, 39, 42, 40, 41, 39, 40, 41, 40):
        client.post("/api/sensors/readings", json=dict(GOOD, soil=soil))
    client.post("/api/sensors/readings", json=dict(GOOD, soil=95))                   # spike
    d = client.get("/api/similarity/current").json()
    assert "soil" in d["excluded_fields"] and "soil" not in d["query"]
    assert {"temperature", "humidity"} <= set(d["query"])
    keep = client.get("/api/similarity/current?exclude_unreliable=false").json()
    assert keep["excluded_fields"] == [] and keep["query"]["soil"] == 95
