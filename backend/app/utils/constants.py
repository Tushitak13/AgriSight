
"""Domain constants. Tune thresholds/weights here, not inside the logic."""

# field -> nominal physical (min, max). Out-of-range readings are stored + flagged, not rejected.
NOMINAL_RANGES = {
    "temperature": (-10.0, 60.0),   # deg C
    "humidity": (0.0, 100.0),       # %
    "soil": (0.0, 100.0),           # % moisture
    "rain": (0.0, 100.0),           # 0 = dry, 100 = heavy
    "water": (0.0, 5000.0),         # tank level (ml)
    "light": (0.0, 100000.0),       # lux
}
SENSOR_FIELDS = list(NOMINAL_RANGES.keys())

# ---- reliability engine
MIN_HISTORY_FOR_STATS = 4
FLATLINE_MIN_POINTS = 10
SPIKE_Z_THRESHOLD = 3.5
SPIKE_Z_ZERO = 10.0
RELIABILITY_LOW = 0.6
OUT_OF_RANGE_CAP = 0.2

# per-sensor behaviour: spike detection on/off, volatility cap, flatline check, weight
SENSOR_PROFILE = {
    "temperature": dict(spike=True, vol_cap=0.10, flatline=True, weight=0.20),
    "humidity":    dict(spike=True, vol_cap=0.15, flatline=True, weight=0.15),
    "soil":        dict(spike=True, vol_cap=0.10, flatline=True, weight=0.30),
    "rain":        dict(spike=False, vol_cap=None, flatline=False, weight=0.15),
    "water":       dict(spike=True, vol_cap=0.10, flatline=False, weight=0.10),
    "light":       dict(spike=True, vol_cap=0.30, flatline=True, weight=0.10),
}
COMPONENT_WEIGHTS = dict(range=0.30, spike=0.30, stability=0.20, completeness=0.20)

# ---- Phase 4: environmental state
STATE_THRESHOLDS = {
    "soil":        [(20, "CRITICALLY_DRY"), (40, "DRY"), (70, "OPTIMAL"), (85, "WET"), (None, "SATURATED")],
    "rain":        [(5, "NO_RAIN"), (30, "LIGHT_RAIN"), (60, "MODERATE_RAIN"), (None, "HEAVY_RAIN")],
    "temperature": [(10, "COLD"), (18, "COOL"), (32, "NORMAL"), (38, "HOT"), (None, "EXTREME_HEAT")],
    "humidity":    [(40, "LOW"), (80, "NORMAL"), (None, "HIGH")],
    "water":       [(500, "CRITICAL"), (1000, "LOW"), (None, "SUFFICIENT")],
    "light":       [(200, "DARK"), (1000, "LOW"), (50000, "NORMAL"), (None, "BRIGHT")],
}
WATER_CONSTRAINT_STATES = ("LOW", "CRITICAL")

# ---- Phase 4: event-triggered vision
TRIGGER_SENSOR_RELIABILITY_MIN = 0.70
TRIGGER_ACI_MIN = 0.60

# ---- Phase 4: image quality
MAX_IMAGE_BYTES = 8 * 1024 * 1024
ANALYSIS_MAX_SIDE = 512
IMAGE_QUALITY_WEIGHTS = dict(
    blur=0.25, brightness=0.20, contrast=0.10, exposure=0.15,
    occlusion=0.15, coverage=0.10, resolution=0.05
)
CRITICAL_QUALITY_FLOOR = 0.2
CRITICAL_QUALITY_CAP = 0.4
BLUR_VAR_RANGE = (5.0, 80.0)
CONTRAST_STD_RANGE = (5.0, 25.0)
BRIGHTNESS_OK = (90.0, 180.0)
BRIGHTNESS_LIMITS = (20.0, 240.0)
CLIP_FRAC_RANGE = (0.05, 0.50)
OCCLUSION_FRAC_RANGE = (0.10, 0.50)
COVERAGE_RANGE = (0.02, 0.15)
REQUIRE_PLANT_COVERAGE = True
RESOLUTION_RANGE = (64, 224)
ISSUE_THRESHOLD = 0.5

# ---- Phase 4: vision reliability
VISION_RELIABILITY_MIN = 0.5

# ---- Phase 5: experience memory
OUTCOME_STATUSES = ("SUCCESSFUL", "PARTIALLY_SUCCESSFUL", "UNSUCCESSFUL")
OUTCOME_SCORES = {
    "SUCCESSFUL": 1.0,
    "PARTIALLY_SUCCESSFUL": 0.5,
    "UNSUCCESSFUL": 0.0,
}
MAX_EXPERIENCES_SCANNED = 5000

# ---- Phase 5: similarity engine
SIMILARITY_WEIGHTS = dict(
    soil=0.30, temperature=0.20, humidity=0.15,
    rain=0.15, water=0.10, light=0.10
)
SIMILARITY_SCALES = dict(
    soil=40.0, temperature=15.0, humidity=40.0,
    rain=50.0, water=2500.0, light=4.6
)
SIMILARITY_LOG_FIELDS = ("light",)
SIMILARITY_MIN_COMMON_WEIGHT = 0.4
SIMILARITY_DEFAULT_K = 5
SIMILARITY_MIN_SCORE = 0.75
HISTORY_FULL_CONFIDENCE_MATCHES = 3

# ---- Phase 6: ACI (Adaptive Confidence Index)
ACI_WEIGHTS = dict(
    sensor_reliability=0.30,
    vision_reliability=0.20,
    prediction_confidence=0.15,
    historical_similarity=0.20,
    recent_behaviour=0.15,
)
ACI_HIGH = 0.75
ACI_LOW = TRIGGER_ACI_MIN
ACI_VISION_MAX_AGE_MINUTES = 60
ACI_COLD_START_CAP = 0.70
ACI_BEHAVIOUR_WINDOW = 5
ACI_SIMILARITY_K = 5
UNEXPLAINED_MIN_EXPERIENCES = 5

# New: minimum evidence coverage required before ACI can be HIGH.
# Coverage is the sum of available, freshness-adjusted nominal weights.
ACI_MIN_COVERAGE_FOR_HIGH = 0.45

# New: if evidence coverage is too low, prevent an unjustified HIGH score.
ACI_LOW_COVERAGE_CAP = 0.70

# ---- Phase 6: CRI (Crop Resilience Index)
CRI_WEIGHTS = dict(
    environmental_stability=0.30,
    stress_tolerance=0.30,
    historical_recovery=0.20,
    recent_response=0.20,
)
CRI_LOW, CRI_HIGH = 0.4, 0.7
CRI_NEUTRAL = 0.5
CRI_WINDOW = 20
CRI_RECENT_OUTCOMES = 5
CRI_RECENCY_DECAY = 0.7
CRI_SEVERITY_MAX_SHARE = 0.7
CRI_FIELD_WEIGHTS = dict(
    soil=0.30, temperature=0.20, humidity=0.10,
    rain=0.10, water=0.20, light=0.10
)

# how good each state is for the crop (1 = ideal).
STATE_FAVOURABILITY = {
    "soil": {
        "CRITICALLY_DRY": 0.1, "DRY": 0.5, "OPTIMAL": 1.0,
        "WET": 0.6, "SATURATED": 0.2,
    },
    "rain": {
        "NO_RAIN": 1.0, "LIGHT_RAIN": 1.0,
        "MODERATE_RAIN": 0.7, "HEAVY_RAIN": 0.3,
    },
    "temperature": {
        "COLD": 0.2, "COOL": 0.7, "NORMAL": 1.0,
        "HOT": 0.6, "EXTREME_HEAT": 0.1,
    },
    "humidity": {"LOW": 0.6, "NORMAL": 1.0, "HIGH": 0.6},
    "water": {"CRITICAL": 0.1, "LOW": 0.5, "SUFFICIENT": 1.0},
    "light": {"DARK": 0.3, "LOW": 0.7, "NORMAL": 1.0, "BRIGHT": 0.8},
}

# visual_state -> stress severity 0..1.
VISION_STRESS_SEVERITY = {
    "healthy_appearance": 0.0,
    "possible_stress": 0.6,
}

# ---- Phase 6.1: Evidence Decay Logic (EDL) + multivariate novelty
EDL_SENSOR_HALF_LIFE_HOURS = 6.0
EDL_VISION_HALF_LIFE_HOURS = 2.0
EDL_HISTORY_HALF_LIFE_HOURS = 24.0 * 30.0
EDL_FRESHNESS_FLOOR = 0.05
MAHALANOBIS_NOVELTY_THRESHOLD = 0.65
