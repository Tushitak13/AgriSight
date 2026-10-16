"""Phase 6 walkthrough: watch ACI, CRI and the camera trigger react as evidence changes.
Needs the server running. Uses its own device so your esp32-01 data stays untouched.
Usage: python scripts/demo_phase6.py [--no-seed]"""
import random
import sys
from pathlib import Path

import requests

BASE = "http://127.0.0.1:8000"
DEV = "demo-farm"
SAMPLES = Path(__file__).resolve().parents[2] / "data" / "sample"
rng = random.Random(1)


def get(path, **params):
    return requests.get(f"{BASE}{path}", params=dict(device_id=DEV, **params), timeout=10).json()


def post_reading(**over):
    body = dict(device_id=DEV, temperature=round(rng.gauss(29, 0.4), 1), humidity=round(rng.gauss(66, 1.5), 1),
                soil=round(rng.gauss(35, 0.8), 1), rain=0, water=1700, light=round(rng.gauss(450, 15)))
    body.update(over)
    requests.post(f"{BASE}/api/sensors/readings", json=body, timeout=10).raise_for_status()


def show(title):
    a, c, t = get("/api/aci/current"), get("/api/cri/current"), get("/api/vision/trigger")
    print(f"\n=== {title}")
    comps = {k: v["value"] for k, v in a["components"].items() if v["available"]}
    print(f"  ACI {a['aci']:.3f} [{a['level']}]  limiting: {a['limiting_factor']}  "
          f"coverage {a['evidence_coverage']:.0%}  cold_start={a['cold_start']}  novel={a['novel_condition']}")
    print(f"      components: {comps}")
    print(f"  CRI {c['cri_percent']:.1f}% [{c['level']}]  weakest: {c['weakest_component']}  "
          f"stress_severity {c['stress_severity']}  last-known-good used for: {c['substituted_fields'] or '-'}")
    print(f"  camera trigger: {t['trigger']}  {t['reasons'] or ''}")


def upload(name):
    with open(SAMPLES / f"{name}.jpg", "rb") as f:
        r = requests.post(f"{BASE}/api/vision/analyze", data={"device_id": DEV},
                          files={"file": (f"{name}.jpg", f, "image/jpeg")}, timeout=20).json()
    print(f"\n  >> uploaded {name}.jpg -> {r['prediction']} (model {r['model_confidence']}, "
          f"image reliability {r['vision_reliability']}, trusted={r['trusted']})")


if "--no-seed" not in sys.argv:
    import subprocess
    subprocess.run([sys.executable, str(Path(__file__).with_name("seed_experiences.py")), "40",
                    "--device", DEV], check=True, stdout=subprocess.DEVNULL)
    print("seeded 40 synthetic experiences for", DEV)

for _ in range(12):
    post_reading()
show("1. Calm farm, 12 normal readings, no camera")

post_reading(soil=95)
show("2. Soil suddenly reads 95 (sensor spike)")

for _ in range(3):
    post_reading()
upload("healthy")
upload("healthy")
show("3. Back to normal + two clear 'healthy' photos")

upload("dark")
show("4. Latest photo is too dark to trust")

upload("stressed")
show("5. A clear photo that looks stressed")
