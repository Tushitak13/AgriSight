"""Cross-sensor consistency. A conflict does NOT prove a sensor is wrong
(irrigation can make soil wet while rain is 0) so it only lowers confidence."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Rule:
    name: str
    sensors: tuple[str, ...]
    penalty: float
    message: str
    test: callable


RULES = [
    Rule("wet_soil_but_no_rain", ("soil", "rain"), 0.10,
         "Soil very wet while rain sensor reads dry",
         lambda r: r["soil"] >= 85 and r["rain"] <= 5),
    Rule("dry_soil_but_heavy_rain", ("soil", "rain"), 0.15,
         "Soil very dry while rain sensor reads heavy rain",
         lambda r: r["soil"] <= 15 and r["rain"] >= 60),
    Rule("heavy_rain_but_dry_air", ("humidity", "rain"), 0.15,
         "Very low humidity during heavy rain",
         lambda r: r["humidity"] <= 20 and r["rain"] >= 60),
    Rule("heavy_rain_but_bright_sun", ("light", "rain"), 0.10,
         "Very bright light during heavy rain",
         lambda r: r["light"] >= 20000 and r["rain"] >= 60),
    Rule("hot_and_saturated_air", ("temperature", "humidity"), 0.10,
         "Very hot temperature with near-saturated humidity",
         lambda r: r["temperature"] >= 40 and r["humidity"] >= 95),
]


def check_consistency(latest: dict) -> list[dict]:
    """latest: sensor -> value (None if missing). Rules whose sensors are
    missing are skipped (missingness is already penalised elsewhere)."""
    findings = []
    for rule in RULES:
        if any(latest.get(s) is None for s in rule.sensors):
            continue
        if rule.test(latest):
            findings.append(dict(rule=rule.name, sensors=list(rule.sensors),
                                 penalty=rule.penalty, message=rule.message))
    return findings
