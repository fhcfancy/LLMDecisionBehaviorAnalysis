"""
Central configuration for the DilemmaValidation experiment.

This module is the single source of truth for paths, the dataset registry,
API parameters, scoring weights, and grade thresholds. All other modules
import from here so paths and constants stay consistent across the pipeline.

Reference plan: /Users/carina/.cursor/plans/dilemma_validation_experiment_baa1d0aa.plan.md
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


ROOT_DIR: Path = Path(__file__).resolve().parent

DILEMMA_DIR: Path = Path(
    "/Users/carina/Documents/MyResearch/Professional/DataAnalysis/Dilemma"
)
GEN_DIR: Path = Path(
    "/Users/carina/Documents/MyResearch/Professional/DataAnalysis/"
    "Generalization/generated_emotional_dilemmas"
)

NEUTRAL_CSV: Path = DILEMMA_DIR / "NeutralDilemma.csv"

VARIANT_FILES: list[tuple[str, Path]] = [
    ("CN", DILEMMA_DIR / "CN_emotional_dilemma.csv"),
    ("CT", DILEMMA_DIR / "CT_emotional_dilemma.csv"),
    ("R1", DILEMMA_DIR / "R1_emotional_dilemma.csv"),
    ("V3", DILEMMA_DIR / "V3_emotional_dilemma.csv"),
    ("GPT_5", GEN_DIR / "GPT_5_emmotional_dilemma.csv"),
    ("GPT_o4", GEN_DIR / "GPT_o4_emmotional_dilemma.csv"),
    ("QwenN", GEN_DIR / "QwenN_emotional_dilemma.csv"),
    ("QwenT", GEN_DIR / "QwenT_emotional_dilemma.csv"),
]

VARIANT_KEYS: list[str] = [k for k, _ in VARIANT_FILES]


RESULTS_DIR: Path = ROOT_DIR / "results"
RAW_DIR: Path = RESULTS_DIR / "raw"
ITEMS_DIR: Path = RESULTS_DIR / "items"
DATASETS_DIR: Path = RESULTS_DIR / "datasets"
FIGURES_DIR: Path = RESULTS_DIR / "figures"

LOGS_DIR: Path = ROOT_DIR / "logs"
REPORT_DIR: Path = ROOT_DIR / "report"

SAMPLING_DIR: Path = ROOT_DIR / "sampling"
SAMPLED_IDX_CSV: Path = SAMPLING_DIR / "sampled_idx.csv"
HUMAN_VALIDATION_PACK_CSV: Path = SAMPLING_DIR / "human_validation_pack.csv"
SAMPLING_REPORT_MD: Path = SAMPLING_DIR / "sampling_report.md"
SAMPLING_MANIFEST_JSON: Path = SAMPLING_DIR / "manifest.json"
TOPIC_REFERENCE_CSV: Path = Path(
    "/Users/carina/Documents/MyResearch/Professional/DataAnalysis/"
    "dilemmas_with_detail_by_action.csv"
)

RUN_LOG: Path = LOGS_DIR / "run_validation.log"
FAILED_ITEMS_CSV: Path = LOGS_DIR / "failed_items.csv"
RUN_STATE_JSON: Path = LOGS_DIR / "run_state.json"

DATASET_QUALITY_CSV: Path = DATASETS_DIR / "dataset_quality.csv"
RELIABILITY_CSV: Path = DATASETS_DIR / "reliability.csv"
COVERAGE_CSV: Path = DATASETS_DIR / "coverage.csv"

RANKING_SUMMARY_CSV: Path = DATASETS_DIR / "ranking_summary.csv"
RANKING_FRIEDMAN_JSON: Path = DATASETS_DIR / "ranking_friedman.json"
RANKING_NEMENYI_CSV: Path = DATASETS_DIR / "ranking_nemenyi_pmatrix.csv"
RANKING_SUBDIMENSIONS_CSV: Path = DATASETS_DIR / "ranking_subdimensions.csv"
RANKING_FIGURE_MAIN: Path = FIGURES_DIR / "figure_ranking_critical_difference.png"
RANKING_FIGURE_SUBDIM: Path = FIGURES_DIR / "figure_ranking_subdimensions.png"

REPORT_MD: Path = REPORT_DIR / "validation_report.md"
REPORT_HTML: Path = REPORT_DIR / "validation_report.html"

# Critical-difference constants follow Demšar (2006), JMLR 7, Table 5.
# Values are the Studentized range statistic at alpha=0.05 divided by sqrt(2),
# i.e. q_alpha used in CD = q_alpha * sqrt(k * (k + 1) / (6 * N)).
NEMENYI_Q_ALPHA_05: dict[int, float] = {
    2: 1.960,
    3: 2.343,
    4: 2.569,
    5: 2.728,
    6: 2.850,
    7: 2.949,
    8: 3.031,
    9: 3.102,
    10: 3.164,
}


def ensure_dirs() -> None:
    """Create all output directories if they do not already exist."""
    for d in (
        RAW_DIR,
        ITEMS_DIR,
        DATASETS_DIR,
        FIGURES_DIR,
        LOGS_DIR,
        REPORT_DIR,
        SAMPLING_DIR,
    ):
        d.mkdir(parents=True, exist_ok=True)


def raw_jsonl_path(variant: str, run: int = 1) -> Path:
    """Return the JSONL path for a variant's raw API responses.

    run=1 -> results/raw/<variant>.jsonl
    run=2 -> results/raw/<variant>_retest.jsonl
    """
    if run == 1:
        return RAW_DIR / f"{variant}.jsonl"
    if run == 2:
        return RAW_DIR / f"{variant}_retest.jsonl"
    raise ValueError(f"run must be 1 or 2, got {run}")


def items_csv_path(variant: str) -> Path:
    return ITEMS_DIR / f"{variant}_items.csv"


API_URL: str = "https://api2.aigcbest.top/v1/chat/completions"
MODEL_NAME: str = "gemini-3.1-pro-preview-low"
API_KEY_ENV: str = "AIGCBEST_API_KEY"

TEMPERATURE: float = 0.3
MAX_TOKENS: int = 4096

MAX_RETRIES: int = 8
BASE_DELAY_SECONDS: float = 3.0
MAX_BACKOFF_SECONDS: float = 90.0
CONNECT_TIMEOUT: int = 15
READ_TIMEOUT_BASE: int = 120
READ_TIMEOUT_MAX: int = 420
TIMEOUT_COOLDOWN_AFTER: int = 3
TIMEOUT_COOLDOWN_SECONDS: int = 45

DEFAULT_WORKERS: int = 8

RAW_TEXT_TRUNCATE_BYTES: int = 4096

# Circuit breaker: auto-abort a run when recent results look broken.
# Failures = qc_flag in {parse_error, refusal, network_failed, worker_exception}.
CB_WINDOW: int = 30
CB_FAILURE_RATE: float = 0.70
CB_CONSECUTIVE: int = 15
CB_MIN_SAMPLES: int = 20


def get_api_key() -> str:
    """Read the API key from the environment, raising a clear error if missing."""
    key = os.getenv(API_KEY_ENV, "").strip()
    if not key:
        raise EnvironmentError(
            f"Missing API key. Export {API_KEY_ENV} before running."
        )
    return key


W_SEMANTIC: float = 0.40
W_NATURALNESS: float = 0.35
W_COHERENCE: float = 0.25

SEMANTIC_PASS_THRESHOLD: float = 0.75


@dataclass(frozen=True)
class GradeThresholds:
    excellent: float = 0.85
    good: float = 0.70
    marginal: float = 0.55


GRADE: GradeThresholds = GradeThresholds()


def assign_grade(mean_item_quality: float) -> str:
    """Map a mean item-quality score to one of the four grade buckets."""
    if mean_item_quality >= GRADE.excellent:
        return "Excellent"
    if mean_item_quality >= GRADE.good:
        return "Good"
    if mean_item_quality >= GRADE.marginal:
        return "Marginal"
    return "Fail"


RANDOM_STATE: int = 20260519
RELIABILITY_FRACTION: float = 0.10
BOOTSTRAP_RESAMPLES: int = 1000
RELIABILITY_RHO_MIN: float = 0.60

SAMPLE_SEED: int = 20260514
PER_STRATUM_DEFAULT: int = 20
