"""Shared constants. Stage probabilities are assumed CRM defaults, not measured."""
from datetime import date

SEED = 42
N_OPPS = 1800
AS_OF = date(2025, 9, 30)          # the "today" of the synthetic snapshot
DATA_START = date(2023, 10, 1)     # earliest opportunity creation date

# (stage, order, assumed win probability, is_open)
STAGES = [
    ("Qualify", 1, 0.10, True),
    ("Discovery", 2, 0.25, True),
    ("Proposal", 3, 0.50, True),
    ("Negotiation", 4, 0.75, True),
    ("Closed Won", 5, 1.00, False),
    ("Closed Lost", 6, 0.00, False),
]
OPEN_STAGES = [s for s, _, _, o in STAGES if o]
STAGE_ORDER = {s: o for s, o, _, _ in STAGES}
STAGE_PROB = {s: p for s, _, p, _ in STAGES}

CATEGORIES = ["Commit", "Best Case", "Pipeline"]

# Probability an opportunity advances out of each open stage (generator only).
ADVANCE_P = {"Qualify": 0.66, "Discovery": 0.70, "Proposal": 0.72, "Negotiation": 0.82}
SEGMENT_MOD = {"SMB": 1.00, "Mid-Market": 0.97, "Enterprise": 0.92}
SEGMENT_MEDIAN = {"SMB": 9_000, "Mid-Market": 30_000, "Enterprise": 95_000}
SEGMENT_MIX = [("SMB", 0.50), ("Mid-Market", 0.35), ("Enterprise", 0.15)]
N_REPS = 12

MIN_N_EMPIRICAL = 30   # fewer closed opps reaching a stage -> fall back to assumed prob

# Synthetic quarterly quota targets (USD). Invented for the demo.
QUOTA = {
    "2024Q1": 900_000, "2024Q2": 950_000, "2024Q3": 1_000_000, "2024Q4": 1_050_000,
    "2025Q1": 1_050_000, "2025Q2": 1_100_000, "2025Q3": 1_100_000,
    "2025Q4": 1_150_000, "2026Q1": 1_200_000,
}
COVERAGE_BENCHMARK = 3.0   # common "3x pipeline" rule of thumb, a convention not a law
