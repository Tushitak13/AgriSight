"""Creates synthetic past experiences so the memory/similarity engine has history to search.
They are tagged source="seed" and can be removed with DELETE /api/experiences/seed.
Usage: python scripts/seed_experiences.py [count] [--device esp32-01] [--seed 42]
The server must be running."""
import random
import sys

import requests

BASE = "http://127.0.0.1:8000"


def arg(name, default):
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else default


count = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 40
device = arg("--device", "esp32-01")
rng = random.Random(int(arg("--seed", 42)))

# intervention -> typical soil gain (percentage points) when conditions are average
EXPECTED_GAIN = {"monitor": 0.0, "light_irrigation": 12.0, "heavy_irrigation": 30.0}


def clip(v, lo, hi):
    return max(lo, min(hi, v))


def make_condition():
    raining = rng.random() < 0.25
    return {
        "soil": round(rng.uniform(15, 90), 1),
        "temperature": round(clip(rng.gauss(29, 4), 5, 45), 1),
        "humidity": round(clip(rng.gauss(65, 10), 20, 100), 1),
        "rain": round(rng.uniform(10, 70), 1) if raining else 0.0,
        "water": round(rng.uniform(600, 2500)),
        "light": round(clip(rng.lognormvariate(6.1, 0.5), 20, 90000)),
    }


def decide(c):
    if c["rain"] >= 5 or c["soil"] >= 40:
        return "no_action_needed", "monitor"
    if c["soil"] < 20:
        return "irrigation_needed", "heavy_irrigation"
    return "irrigation_needed", "light_irrigation"


def simulate(c, intervention):
    """Fake physics: hot weather loses water, rain adds a little, results are noisy."""
    expected = EXPECTED_GAIN[intervention]
    if intervention == "monitor":
        gain = rng.gauss(-1.0, 1.0) + c["rain"] * 0.1
    else:
        gain = expected * rng.uniform(0.4, 1.1) * (0.75 if c["temperature"] > 33 else 1.0)
    after_soil = round(clip(c["soil"] + gain, 0, 100), 1)
    after = dict(c, soil=after_soil)
    if intervention == "monitor":
        status = "SUCCESSFUL" if after_soil >= 40 else "UNSUCCESSFUL"
    else:
        ratio = (after_soil - c["soil"]) / expected
        status = "SUCCESSFUL" if ratio >= 0.8 else "PARTIALLY_SUCCESSFUL" if ratio >= 0.4 else "UNSUCCESSFUL"
    return expected, after, status


ok = 0
for i in range(count):
    cond = make_condition()
    decision, intervention = decide(cond)
    expected, after, status = simulate(cond, intervention)
    body = dict(device_id=device, condition=cond, decision=decision, intervention=intervention,
                expected_soil_change=expected, source="seed",
                outcome=dict(status=status, after=after))
    r = requests.post(f"{BASE}/api/experiences", json=body, timeout=5)
    ok += r.status_code == 201
    print(i, r.status_code, intervention, status, f"soil {cond['soil']} -> {after['soil']}")
print(f"\n{ok}/{count} seed experiences created for {device}")
