import sqlite3
import json

CURRENT_DB = "agrisight.db"
BACKUP_DB = "agrisight_backup_before_experience_migration.db"

current = sqlite3.connect(CURRENT_DB)
backup = sqlite3.connect(BACKUP_DB)

rows = backup.execute("""
    SELECT id, farm_id, device_id, occurred_at, context, intervention,
           outcome, outcome_success, outcome_score, outcome_confidence,
           source, created_at
    FROM experiences
    ORDER BY id
""").fetchall()

print("Rows in backup:", len(rows))

for row in rows:
    (
        old_id,
        farm_id,
        old_device_id,
        occurred_at,
        context,
        old_intervention,
        outcome,
        outcome_success,
        outcome_score,
        outcome_confidence,
        source,
        old_created_at,
    ) = row

    # Skip row 3 because we already restored it manually.
    exists = current.execute(
        "SELECT 1 FROM experiences WHERE id = ?",
        (old_id,)
    ).fetchone()

    if exists:
        print(f"Skipping existing row {old_id}")
        continue

    condition = json.loads(context) if context else {}

    intervention_data = json.loads(old_intervention) if old_intervention else {}

    if isinstance(intervention_data, dict):
        intervention = intervention_data.get("type") or "unknown"
    else:
        intervention = str(intervention_data) if intervention_data else "unknown"

    outcome_data = json.loads(outcome) if outcome else None

    if outcome_success is None:
        outcome_status = None
    elif outcome_success:
        outcome_status = "SUCCESS"
    else:
        outcome_status = "FAILURE"

    soil_change = None

    if outcome_data and isinstance(outcome_data, dict):
        soil_before = condition.get("soil")
        soil_after = outcome_data.get("soil_after")

        if soil_before is not None and soil_after is not None:
            soil_change = round(
                float(soil_after) - float(soil_before),
                2
            )

    device_id = old_device_id or "esp32-01"

    current.execute("""
        INSERT INTO experiences (
            id,
            device_id,
            created_at,
            source,
            condition,
            condition_states,
            decision,
            intervention,
            expected_soil_change,
            outcome_status,
            outcome_condition,
            soil_change,
            outcome_recorded_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        old_id,
        device_id,
        occurred_at,
        source or "real",
        json.dumps(condition),
        json.dumps({}),
        None,
        intervention,
        None,
        outcome_status,
        json.dumps(outcome_data) if outcome_data else None,
        soil_change,
        old_created_at if outcome_data else None,
    ))

    print(f"Inserted row {old_id}")

current.commit()

count = current.execute(
    "SELECT COUNT(*) FROM experiences"
).fetchone()[0]

print()
print("Final experience count:", count)

print()
print("Experiences:")
for row in current.execute("""
    SELECT id, device_id, condition, intervention,
           outcome_status, outcome_condition, soil_change
    FROM experiences
    ORDER BY id
"""):
    print(row)

current.close()
backup.close()