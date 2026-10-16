"""Fake ESP32: posts readings so you can test without hardware.
Usage: python scripts/simulate_esp32.py [count] [--spike]"""
import random, sys, time
import requests

URL = "http://127.0.0.1:8000/api/sensors/readings"
count = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 20
spike = "--spike" in sys.argv

soil = 40.0
for i in range(count):
    soil = min(100, max(0, soil + random.uniform(-1.5, 1.0)))
    body = {
        "temperature": round(random.gauss(29, 0.5), 1),
        "humidity": round(random.gauss(66, 2), 1),
        "soil": round(soil, 1),
        "rain": 0,
        "water": 1700,
        "light": round(random.gauss(450, 20)),
    }
    if spike and i == count - 1:
        body["soil"] = 95  # sudden jump, for Phase 3 spike detection
    if random.random() < 0.05:
        del body["rain"]   # simulate dropped sensor
    r = requests.post(URL, json=body, timeout=5)
    print(i, r.status_code, body)
    time.sleep(0.2)
