"""Shared loader for the Cross-Family Generalization analysis.

Loads the 16 decision CSVs under ``Generalization/decisions``, joins the
DAILYDILEMMAS topic_group labels, and exposes:

- ``load_long_frame()``: long-format dataframe with one row per
  (idx, model, mode) carrying the parsed choice (or NaN if invalid).
- ``load_topic_map()``: idx -> topic_group dictionary.
- ``valid_pair(...)`` helper to build the paired (Neutral, method) subset
  used by all four claims.

The module is intentionally dependency-light: only ``pandas`` and the
standard library.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

import pandas as pd


HERE = Path(__file__).resolve().parent
GEN_ROOT = HERE.parent
DECISIONS_DIR = GEN_ROOT / "decisions"
ANALYSIS_DIR = HERE
FIGURES_DIR = ANALYSIS_DIR / "figures"

TOPIC_LABELS_CSV = (
    GEN_ROOT.parent / "dilemmas_with_detail_by_action.csv"
)
NEUTRAL_REFERENCE_CSV = GEN_ROOT.parent / "Dilemma" / "NeutralDilemma.csv"


MODELS: Tuple[str, ...] = ("GPT_5", "GPT_o4", "QwenN", "QwenT")
MODES: Tuple[str, ...] = ("Neutral", "Neutral-CoT", "EI", "EA")
NON_NEUTRAL_MODES: Tuple[str, ...] = ("Neutral-CoT", "EI", "EA")

# Folder name + file prefix for each mode
MODE_SPECS: Dict[str, Tuple[str, str]] = {
    "Neutral": ("Neutral", "Neutral"),
    "Neutral-CoT": ("Neutral-CoT", "Neutral-CoT"),
    "EI": ("EmotionalIntuitive", "EI"),
    "EA": ("EmotionalAnalytic", "EA"),
}

# Architecture grouping used in the per-architecture analyses (Claim 1)
THINKING_MODELS: Tuple[str, ...] = ("GPT_o4", "QwenT")
NON_THINKING_MODELS: Tuple[str, ...] = ("GPT_5", "QwenN")
GPT_MODELS: Tuple[str, ...] = ("GPT_5", "GPT_o4")
QWEN_MODELS: Tuple[str, ...] = ("QwenN", "QwenT")


@dataclass(frozen=True)
class CellInfo:
    """Per-cell load info used by the validity report."""

    model: str
    mode: str
    path: Path
    n_rows: int
    n_unique_idx: int
    n_valid: int
    n_invalid: int
    n_missing: int
    n_api_error: int


def _csv_path(mode: str, model: str) -> Path:
    folder, prefix = MODE_SPECS[mode]
    return DECISIONS_DIR / folder / f"{prefix}_{model}.csv"


def _coerce_choice(series: pd.Series) -> pd.Series:
    """Coerce choice_value to {1, 2, NaN} integers (Int64)."""
    numeric = pd.to_numeric(series, errors="coerce")
    masked = numeric.where(numeric.isin([1, 2]))
    return masked.astype("Int64")


def load_cell(model: str, mode: str) -> Tuple[pd.DataFrame, CellInfo]:
    """Load one (model, mode) CSV and return (rows, info)."""
    path = _csv_path(mode, model)
    df = pd.read_csv(path)
    df["idx"] = pd.to_numeric(df["idx"], errors="coerce").astype("Int64")
    df = df.dropna(subset=["idx"]).copy()
    # Drop duplicated idx (keep first); the generation pipeline writes once per
    # idx but recovered Qwen runs occasionally append, so dedupe defensively.
    df = df.drop_duplicates(subset=["idx"], keep="first")

    choice = _coerce_choice(df.get("choice_value"))
    df["choice"] = choice
    df["model"] = model
    df["mode"] = mode

    api_err = df.get("api_error")
    n_api_error = int(api_err.notna().sum()) if api_err is not None else 0

    info = CellInfo(
        model=model,
        mode=mode,
        path=path,
        n_rows=len(df),
        n_unique_idx=int(df["idx"].nunique()),
        n_valid=int(choice.notna().sum()),
        n_invalid=int(choice.isna().sum()),
        n_missing=0,
        n_api_error=n_api_error,
    )
    return df[["idx", "model", "mode", "choice"]], info


def load_long_frame(reference_idx: Optional[Iterable[int]] = None) -> pd.DataFrame:
    """Return a long-format dataframe with one row per (idx, model, mode).

    Choices outside {1, 2} are encoded as ``<NA>`` in the ``choice`` Int64
    column. When ``reference_idx`` is provided, the frame is reindexed to that
    full set per (model, mode) so missing rows become explicit ``<NA>`` cells.
    """
    frames: List[pd.DataFrame] = []
    for model in MODELS:
        for mode in MODES:
            df, _ = load_cell(model, mode)
            frames.append(df)
    long_df = pd.concat(frames, ignore_index=True)

    if reference_idx is not None:
        ref = pd.Index(sorted({int(i) for i in reference_idx}), name="idx")
        full = (
            pd.MultiIndex.from_product(
                [ref, MODELS, MODES], names=["idx", "model", "mode"]
            )
            .to_frame(index=False)
        )
        long_df = full.merge(long_df, on=["idx", "model", "mode"], how="left")
        long_df["choice"] = long_df["choice"].astype("Int64")
    return long_df


def load_topic_map(labels_csv: Path = TOPIC_LABELS_CSV) -> pd.DataFrame:
    """idx -> topic_group, deduplicated by idx (first observed wins)."""
    if not labels_csv.is_file():
        return pd.DataFrame(columns=["idx", "topic_group"])
    df = pd.read_csv(labels_csv, usecols=["idx", "topic_group"])
    df["idx"] = pd.to_numeric(df["idx"], errors="coerce").astype("Int64")
    df = df.dropna(subset=["idx"])
    df["topic_group"] = df["topic_group"].astype("string").fillna("Unknown").str.strip()
    df.loc[df["topic_group"].isin(["", "nan", "None"]), "topic_group"] = "Unknown"
    df = df.drop_duplicates(subset=["idx"], keep="first")
    return df.reset_index(drop=True)


def load_reference_idx() -> List[int]:
    """Return the canonical 1,360-item idx set from NeutralDilemma.csv."""
    df = pd.read_csv(NEUTRAL_REFERENCE_CSV, usecols=["idx"])
    return sorted(set(pd.to_numeric(df["idx"], errors="coerce").dropna().astype(int)))


def per_cell_info() -> List[CellInfo]:
    infos: List[CellInfo] = []
    for model in MODELS:
        for mode in MODES:
            _, info = load_cell(model, mode)
            infos.append(info)
    return infos


def wide_choices(long_df: pd.DataFrame) -> pd.DataFrame:
    """Pivot the long frame to wide: rows = (idx, model), columns = mode."""
    wide = long_df.pivot_table(
        index=["idx", "model"], columns="mode", values="choice", aggfunc="first"
    )
    return wide.reindex(columns=list(MODES))


def df_to_md(df: pd.DataFrame, float_fmt: str = "{:.4f}", int_fmt: str = "{:d}") -> str:
    """Render a DataFrame as a Markdown pipe table.

    Avoids the optional ``tabulate`` dependency. Numeric values use
    ``float_fmt`` / ``int_fmt``; missing values render as empty cells.
    """
    df = df.copy()
    if df.index.name is not None or isinstance(df.index, pd.MultiIndex):
        df = df.reset_index()

    def _fmt(value: object) -> str:
        if pd.isna(value):
            return ""
        if isinstance(value, (bool,)):
            return str(value)
        if isinstance(value, (int,)):
            return int_fmt.format(value)
        if isinstance(value, float):
            if value.is_integer():
                return int_fmt.format(int(value))
            return float_fmt.format(value)
        return str(value)

    header = "| " + " | ".join(str(c) for c in df.columns) + " |"
    sep = "| " + " | ".join(["---"] * len(df.columns)) + " |"
    rows = ["| " + " | ".join(_fmt(v) for v in row) + " |" for row in df.itertuples(index=False, name=None)]
    return "\n".join([header, sep] + rows)
