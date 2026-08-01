"""Build the paired (Neutral, method) tables that drive every claim.

For each model and each method ``m in {Neutral-CoT, EI, EA}`` we build a
DataFrame keyed by ``idx`` with columns:

- ``y_neutral``: that model's Neutral baseline choice (1 or 2)
- ``y_method``:  the method's choice (1 or 2 or NaN)
- ``method_valid``: bool
- ``ref_valid``: bool (neutral)
- ``both_valid``: bool
- ``agree``: bool (only meaningful when ``both_valid``)
- ``method_shift_to_1``: 1 if disagree and method picked 1; -1 if disagree and method picked 2; 0 otherwise
- ``topic_group``

This mirrors the §A.2 definitions of Effective Alignment, CMR, and the
directional Choice-1 asymmetry test.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List

import pandas as pd

from data_loader import MODELS, NON_NEUTRAL_MODES


@dataclass(frozen=True)
class PairedTable:
    model: str
    method: str
    df: pd.DataFrame  # indexed by idx


def build_paired_tables(long_df: pd.DataFrame) -> Dict[tuple, PairedTable]:
    """Return a dict keyed by (model, method) -> PairedTable.

    ``long_df`` is the long-format frame from ``data_loader.load_long_frame``
    with the topic_group already merged in.
    """
    wide = long_df.pivot_table(
        index=["idx", "model"], columns="mode", values="choice", aggfunc="first"
    ).reset_index()
    topic = long_df[["idx", "topic_group"]].drop_duplicates(subset=["idx"])
    wide = wide.merge(topic, on="idx", how="left")
    wide["topic_group"] = wide["topic_group"].astype("string").fillna("Unknown")

    tables: Dict[tuple, PairedTable] = {}
    for model in MODELS:
        sub = wide[wide["model"] == model].copy()
        for method in NON_NEUTRAL_MODES:
            df = pd.DataFrame(
                {
                    "idx": sub["idx"].astype(int).values,
                    "y_neutral": sub["Neutral"].astype("Int64").values,
                    "y_method": sub[method].astype("Int64").values,
                    "topic_group": sub["topic_group"].astype("string").values,
                }
            )
            df["ref_valid"] = df["y_neutral"].notna()
            df["method_valid"] = df["y_method"].notna()
            df["both_valid"] = df["ref_valid"] & df["method_valid"]
            df["agree"] = pd.Series(
                df["both_valid"]
                & (df["y_neutral"].astype("Int64") == df["y_method"].astype("Int64")),
                dtype="boolean",
            )
            # Directional shift indicator on idx where we have a disagreement.
            disagree = df["both_valid"] & ~df["agree"].fillna(False)
            shift = pd.Series(0, index=df.index, dtype="Int64")
            shift[disagree & (df["y_method"] == 1)] = 1
            shift[disagree & (df["y_method"] == 2)] = -1
            df["method_shift_to_1"] = shift
            df = df.set_index("idx", drop=True)
            tables[(model, method)] = PairedTable(model=model, method=method, df=df)
    return tables


def effective_alignment(table: PairedTable) -> Dict[str, float]:
    """Per-table EfA, CMR, Coverage, Deviation, sample sizes."""
    df = table.df
    n_ref = int(df["ref_valid"].sum())
    if n_ref == 0:
        nan = float("nan")
        return {"n_ref": 0, "n_method_valid": 0, "EfA": nan, "Coverage": nan, "CMR": nan, "Deviation": nan, "n_match": 0}
    n_method_valid = int((df["ref_valid"] & df["method_valid"]).sum())
    n_match = int(df.loc[df["both_valid"], "agree"].sum())
    efa = n_match / n_ref
    coverage = n_method_valid / n_ref
    cmr = n_match / n_method_valid if n_method_valid else float("nan")
    return {
        "n_ref": n_ref,
        "n_method_valid": n_method_valid,
        "n_match": n_match,
        "EfA": efa,
        "Coverage": coverage,
        "CMR": cmr,
        "Deviation": 1.0 - efa,
    }
