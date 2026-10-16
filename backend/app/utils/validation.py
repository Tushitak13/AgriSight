from app.utils.constants import NOMINAL_RANGES, SENSOR_FIELDS


def check_reading_values(values: dict) -> tuple[list[str], list[str]]:
    """values: sensor -> number|None. Returns (missing_fields, range_flags)."""
    missing, flags = [], []
    for f in SENSOR_FIELDS:
        v = values.get(f)
        if v is None:
            missing.append(f)
            continue
        lo, hi = NOMINAL_RANGES[f]
        if not (lo <= v <= hi):
            flags.append(f"{f}_out_of_range")
    return missing, flags
