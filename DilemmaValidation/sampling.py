"""
Stratified sampling for the DilemmaValidation human-review pack.

Before launching the Gemini census, this module draws a topic_group-stratified
random sample of `idx` values (equal allocation, without replacement) and
expands each idx into a 9-record review pack (1 neutral + 8 emotional variants)
for downstream human verification and to bound the API spend.

The seeding plumbing is pinned end-to-end:
- The stratum draw uses ``numpy.random.default_rng(seed)`` for the per-stratum
  child seeds, and ``DataFrame.sample(random_state=...)`` for the actual rows.
- The default seed is ``config.SAMPLE_SEED``; ``config.RANDOM_STATE`` is kept
  separate for downstream bootstraps / retest stratification.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from config import (
    NEUTRAL_CSV,
    PER_STRATUM_DEFAULT,
    SAMPLE_SEED,
    TOPIC_REFERENCE_CSV,
    VARIANT_FILES,
    VARIANT_KEYS,
)
from dataset_loader import SITUATION_COL, load_variants


NEUTRAL_MODEL_TAG: str = "NEUTRAL"
TOPIC_COL: str = "topic_group"
IDX_COL: str = "idx"
PACK_COLUMNS: list[str] = [
    "idx",
    "topic_group",
    "source_file",
    "model_tag",
    "role",
    "situation",
    "action1",
    "action2",
    "source_path",
]


@dataclass(frozen=True)
class SourceFileStat:
    """Summary statistics for one source CSV used during eligibility checks."""

    model_tag: str
    role: str
    source_file: str
    source_path: str
    n_in_file: int
    n_with_text: int
    n_idx_matched: int


def load_topic_reference(path: Path | str = TOPIC_REFERENCE_CSV) -> pd.DataFrame:
    """Return a DataFrame with unique ``idx -> topic_group`` from the reference CSV.

    The reference file lists each idx twice (once per action). We collapse on
    idx, keeping the first observed ``topic_group`` and asserting consistency.
    """
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"Topic reference CSV not found: {path}")

    df = pd.read_csv(path, usecols=[IDX_COL, TOPIC_COL])
    df[IDX_COL] = df[IDX_COL].astype(str).str.strip()
    df[TOPIC_COL] = df[TOPIC_COL].astype(str).str.strip()

    df = df[df[IDX_COL].astype(bool) & (df[IDX_COL].str.lower() != "nan")]
    df = df[df[TOPIC_COL].astype(bool) & (df[TOPIC_COL].str.lower() != "nan")]

    grouped = df.groupby(IDX_COL)[TOPIC_COL].nunique()
    inconsistent = grouped[grouped > 1].index.tolist()
    if inconsistent:
        raise ValueError(
            "Inconsistent topic_group within idx in the reference CSV: "
            f"{inconsistent[:10]} (... total {len(inconsistent)})"
        )

    unique = (
        df.drop_duplicates(subset=[IDX_COL], keep="first")
        .reset_index(drop=True)[[IDX_COL, TOPIC_COL]]
        .sort_values(by=IDX_COL, kind="stable")
        .reset_index(drop=True)
    )
    return unique


def compute_eligible_idx(
    reference: pd.DataFrame,
    variants: dict[str, pd.DataFrame],
    neutral: pd.DataFrame,
) -> pd.DataFrame:
    """Return reference rows whose idx exists in neutral and every variant.

    The intersection is taken across the neutral baseline and all 8 variant
    frames produced by :func:`dataset_loader.load_variants`. The returned
    frame is sorted by idx for determinism.
    """
    if reference.empty:
        raise ValueError("Topic reference DataFrame is empty.")

    reference_idx = set(reference[IDX_COL].astype(str))
    neutral_idx = set(neutral[IDX_COL].astype(str))

    intersection = reference_idx & neutral_idx
    for key, frame in variants.items():
        intersection &= set(frame[IDX_COL].astype(str))

    eligible = reference[reference[IDX_COL].isin(intersection)].copy()
    eligible = eligible.sort_values(by=IDX_COL, kind="stable").reset_index(drop=True)
    return eligible


def stratified_sample(
    eligible: pd.DataFrame,
    *,
    per_stratum: int = PER_STRATUM_DEFAULT,
    seed: int = SAMPLE_SEED,
) -> pd.DataFrame:
    """Equal-allocation sampling without replacement, stratified on topic_group.

    Returns a DataFrame with columns ``idx, topic_group, stratum_quota``,
    sorted by ``topic_group`` then ``idx``. Each stratum yields exactly
    ``per_stratum`` rows; a stratum smaller than ``per_stratum`` raises
    ValueError.
    """
    if per_stratum <= 0:
        raise ValueError(f"per_stratum must be positive, got {per_stratum}")

    if TOPIC_COL not in eligible.columns or IDX_COL not in eligible.columns:
        raise ValueError(
            f"eligible frame must contain '{IDX_COL}' and '{TOPIC_COL}' columns"
        )

    rng = np.random.default_rng(seed)
    parts: list[pd.DataFrame] = []
    for stratum, group in eligible.sort_values(by=IDX_COL).groupby(
        TOPIC_COL, sort=True
    ):
        if len(group) < per_stratum:
            raise ValueError(
                f"Stratum '{stratum}' has only {len(group)} idx "
                f"(need >= {per_stratum})."
            )
        child_seed = int(rng.integers(0, 2**32 - 1))
        picked = group.sample(n=per_stratum, replace=False, random_state=child_seed)
        parts.append(picked)

    sample = pd.concat(parts, ignore_index=True)
    sample["stratum_quota"] = per_stratum
    sample = sample[[IDX_COL, TOPIC_COL, "stratum_quota"]]
    sample = sample.sort_values(by=[TOPIC_COL, IDX_COL], kind="stable").reset_index(
        drop=True
    )
    return sample


def _variant_path_lookup() -> dict[str, Path]:
    return {tag: path for tag, path in VARIANT_FILES}


def build_review_pack(
    sampled: pd.DataFrame,
    neutral: pd.DataFrame,
    variants: dict[str, pd.DataFrame],
) -> pd.DataFrame:
    """Expand the sampled idx into a 9-row-per-idx long-form review pack.

    Columns: ``idx, topic_group, source_file, model_tag, role, situation,
    action1, action2, source_path``. Row order is ``(idx, role, model_tag)``
    so reviewers see the neutral row first, then the 8 emotional variants
    in the canonical ``VARIANT_KEYS`` order.
    """
    if sampled.empty:
        raise ValueError("sampled DataFrame is empty; nothing to expand.")

    needed = {IDX_COL, TOPIC_COL}
    missing = needed - set(sampled.columns)
    if missing:
        raise ValueError(f"sampled is missing required columns: {sorted(missing)}")

    sampled_ids = sampled[IDX_COL].astype(str).tolist()
    topic_lookup = dict(
        zip(sampled[IDX_COL].astype(str), sampled[TOPIC_COL].astype(str))
    )

    variant_paths = _variant_path_lookup()
    rows: list[dict[str, object]] = []

    neutral_indexed = neutral.set_index(IDX_COL)
    for idx in sampled_ids:
        if idx not in neutral_indexed.index:
            raise KeyError(f"Sampled idx {idx} missing from neutral baseline.")
        row = neutral_indexed.loc[idx]
        rows.append(
            {
                "idx": idx,
                "topic_group": topic_lookup[idx],
                "source_file": NEUTRAL_CSV.name,
                "model_tag": NEUTRAL_MODEL_TAG,
                "role": "neutral",
                "situation": row[SITUATION_COL],
                "action1": row["action1"],
                "action2": row["action2"],
                "source_path": str(NEUTRAL_CSV),
            }
        )

        for tag in VARIANT_KEYS:
            if tag not in variants:
                raise KeyError(f"Variant '{tag}' missing from variants dict.")
            vframe = variants[tag].set_index(IDX_COL)
            if idx not in vframe.index:
                raise KeyError(
                    f"Sampled idx {idx} missing from variant '{tag}'."
                )
            vrow = vframe.loc[idx]
            source_path = variant_paths[tag]
            rows.append(
                {
                    "idx": idx,
                    "topic_group": topic_lookup[idx],
                    "source_file": source_path.name,
                    "model_tag": tag,
                    "role": "emotional",
                    "situation": vrow[SITUATION_COL],
                    "action1": vrow["action1"],
                    "action2": vrow["action2"],
                    "source_path": str(source_path),
                }
            )

    pack = pd.DataFrame(rows, columns=PACK_COLUMNS)

    role_order = pd.Categorical(pack["role"], categories=["neutral", "emotional"], ordered=True)
    model_order = pd.Categorical(
        pack["model_tag"],
        categories=[NEUTRAL_MODEL_TAG, *VARIANT_KEYS],
        ordered=True,
    )
    pack = pack.assign(_role_rank=role_order, _model_rank=model_order)
    pack = pack.sort_values(
        by=["idx", "_role_rank", "_model_rank"], kind="stable"
    ).drop(columns=["_role_rank", "_model_rank"]).reset_index(drop=True)
    return pack


def collect_source_file_stats(
    variants_raw: dict[str, pd.DataFrame],
    neutral_raw: pd.DataFrame,
    eligible_idx: set[str],
) -> list[SourceFileStat]:
    """Compute per-source-file diagnostics for the report.

    ``variants_raw`` and ``neutral_raw`` are the *post-normalization* frames
    returned by :func:`dataset_loader.load_variants` (already deduped on idx).
    ``n_with_text`` is computed from these frames; ``n_in_file`` is read again
    from the raw CSV to expose any rows dropped during normalization.
    """
    stats: list[SourceFileStat] = []

    n_in_file_neutral = len(pd.read_csv(NEUTRAL_CSV))
    n_with_text_neutral = int(neutral_raw[SITUATION_COL].astype(bool).sum())
    n_matched_neutral = len(set(neutral_raw[IDX_COL].astype(str)) & eligible_idx)
    stats.append(
        SourceFileStat(
            model_tag=NEUTRAL_MODEL_TAG,
            role="neutral",
            source_file=NEUTRAL_CSV.name,
            source_path=str(NEUTRAL_CSV),
            n_in_file=n_in_file_neutral,
            n_with_text=n_with_text_neutral,
            n_idx_matched=n_matched_neutral,
        )
    )

    for tag, path in VARIANT_FILES:
        n_in_file = len(pd.read_csv(path))
        frame = variants_raw[tag]
        n_with_text = int(frame[SITUATION_COL].astype(bool).sum())
        n_matched = len(set(frame[IDX_COL].astype(str)) & eligible_idx)
        stats.append(
            SourceFileStat(
                model_tag=tag,
                role="emotional",
                source_file=path.name,
                source_path=str(path),
                n_in_file=n_in_file,
                n_with_text=n_with_text,
                n_idx_matched=n_matched,
            )
        )
    return stats


def missing_idx_by_source(
    variants: dict[str, pd.DataFrame],
    neutral: pd.DataFrame,
    reference: pd.DataFrame,
) -> dict[str, list[str]]:
    """Return a dict mapping each source tag to the reference idx it is missing."""
    ref_ids = set(reference[IDX_COL].astype(str))
    out: dict[str, list[str]] = {}
    out[NEUTRAL_MODEL_TAG] = sorted(ref_ids - set(neutral[IDX_COL].astype(str)))
    for tag, frame in variants.items():
        out[tag] = sorted(ref_ids - set(frame[IDX_COL].astype(str)))
    return out


def _self_check() -> None:
    """Quick consistency self-check used when running this file directly."""
    reference = load_topic_reference()
    variants, neutral, _coverage = load_variants()
    eligible = compute_eligible_idx(reference, variants, neutral)
    print(f"reference idx: {len(reference)}")
    print(f"neutral idx:   {len(neutral)}")
    print(f"eligible idx:  {len(eligible)}")
    print(f"topic_group strata: {eligible[TOPIC_COL].nunique()}")
    print("Per-stratum population sizes:")
    counts = eligible.groupby(TOPIC_COL).size().sort_index()
    for stratum, n in counts.items():
        print(f"  {stratum}: {n}")

    sample = stratified_sample(eligible, per_stratum=PER_STRATUM_DEFAULT, seed=SAMPLE_SEED)
    print(f"sampled idx: {len(sample)} (expect {17 * PER_STRATUM_DEFAULT})")
    assert sample[IDX_COL].is_unique, "sampled idx must be unique"

    pack = build_review_pack(sample, neutral, variants)
    print(f"review pack rows: {len(pack)} (expect {len(sample) * 9})")
    assert (pack.groupby(IDX_COL).size() == 9).all(), "every idx must have 9 rows"
    per_idx = pack.groupby(IDX_COL)["model_tag"].nunique()
    assert (per_idx == 9).all(), "model tags must be distinct within an idx"


if __name__ == "__main__":
    _self_check()
