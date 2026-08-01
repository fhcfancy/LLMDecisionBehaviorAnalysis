"""
Aggregate per-item and per-variant scores from the raw JSONL outputs.

Produces:
  results/items/<variant>_items.csv         per-idx scored rows
  results/datasets/dataset_quality.csv      one row per variant w/ grade + CI
  results/datasets/reliability.csv          test-retest stats per variant
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.metrics import cohen_kappa_score

from config import (
    BOOTSTRAP_RESAMPLES,
    DATASETS_DIR,
    DATASET_QUALITY_CSV,
    ITEMS_DIR,
    MODEL_NAME,
    RANDOM_STATE,
    RELIABILITY_CSV,
    RELIABILITY_RHO_MIN,
    SEMANTIC_PASS_THRESHOLD,
    VARIANT_KEYS,
    W_COHERENCE,
    W_NATURALNESS,
    W_SEMANTIC,
    assign_grade,
    ensure_dirs,
    items_csv_path,
    raw_jsonl_path,
)


SCALAR_FIELDS: tuple[str, ...] = (
    "semantic_sim",
    "emotion_naturalness",
    "emotion_coherence",
)


@dataclass
class DatasetSummary:
    variant: str
    n_evaluated: int
    n_failed: int
    coverage_pct: float
    mean_item_quality: float
    semantic_pass_rate: float
    mean_naturalness: float
    mean_coherence: float
    ci_lo: float
    ci_hi: float
    dataset_quality_grade: str


def _read_jsonl(path: Path) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    if not path.is_file():
        return pd.DataFrame()
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return pd.DataFrame(rows)


def _compute_item_quality(df: pd.DataFrame) -> pd.Series:
    sim = pd.to_numeric(df.get("semantic_sim"), errors="coerce")
    nat = pd.to_numeric(df.get("emotion_naturalness"), errors="coerce")
    coh = pd.to_numeric(df.get("emotion_coherence"), errors="coerce")
    return W_SEMANTIC * sim + W_NATURALNESS * (nat / 5.0) + W_COHERENCE * (coh / 5.0)


def _bootstrap_ci(values: np.ndarray, *, n_resamples: int, seed: int) -> tuple[float, float]:
    if values.size == 0:
        return float("nan"), float("nan")
    rng = np.random.default_rng(seed)
    n = values.size
    samples = rng.integers(0, n, size=(n_resamples, n))
    means = values[samples].mean(axis=1)
    lo, hi = np.percentile(means, [2.5, 97.5])
    return float(lo), float(hi)


def build_items_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Return the per-item table for one variant with item_quality + flags."""
    if df.empty:
        return pd.DataFrame(
            columns=[
                "variant",
                "idx",
                "run",
                "model",
                "prompt_hash",
                "timestamp",
                "semantic_sim",
                "emotion_naturalness",
                "emotion_coherence",
                "item_quality",
                "semantic_pass",
                "emotions",
                "semantic_justification",
                "emotion_justification",
                "qc_flag",
            ]
        )

    df = df.copy()
    df["semantic_sim"] = pd.to_numeric(df.get("semantic_sim"), errors="coerce")
    df["emotion_naturalness"] = pd.to_numeric(df.get("emotion_naturalness"), errors="coerce")
    df["emotion_coherence"] = pd.to_numeric(df.get("emotion_coherence"), errors="coerce")
    df["item_quality"] = _compute_item_quality(df)
    df["semantic_pass"] = df["semantic_sim"] >= SEMANTIC_PASS_THRESHOLD

    keep_cols = [
        "variant",
        "idx",
        "run",
        "model",
        "prompt_hash",
        "timestamp",
        "semantic_sim",
        "emotion_naturalness",
        "emotion_coherence",
        "item_quality",
        "semantic_pass",
        "emotions",
        "semantic_justification",
        "emotion_justification",
        "qc_flag",
    ]
    for col in keep_cols:
        if col not in df.columns:
            df[col] = None
    return df[keep_cols].copy()


def summarize_variant(
    variant: str,
    items_df: pd.DataFrame,
    *,
    n_in_neutral: int,
    bootstrap_resamples: int,
    seed: int,
) -> DatasetSummary:
    if items_df.empty:
        return DatasetSummary(
            variant=variant,
            n_evaluated=0,
            n_failed=0,
            coverage_pct=0.0,
            mean_item_quality=float("nan"),
            semantic_pass_rate=float("nan"),
            mean_naturalness=float("nan"),
            mean_coherence=float("nan"),
            ci_lo=float("nan"),
            ci_hi=float("nan"),
            dataset_quality_grade="Fail",
        )

    valid = items_df[items_df["qc_flag"].isin(["ok", "clipped"])].copy()
    valid = valid.dropna(subset=["item_quality"])
    n_failed = int((items_df["qc_flag"].isin(["parse_error", "refusal", "network_failed"])).sum())
    n_evaluated = int(len(valid))

    if n_evaluated == 0:
        mean_iq = float("nan")
        sem_pass = float("nan")
        mean_nat = float("nan")
        mean_coh = float("nan")
        ci_lo, ci_hi = float("nan"), float("nan")
        grade = "Fail"
    else:
        values = valid["item_quality"].to_numpy(dtype=float)
        mean_iq = float(values.mean())
        sem_pass = float(valid["semantic_pass"].mean())
        mean_nat = float(valid["emotion_naturalness"].mean())
        mean_coh = float(valid["emotion_coherence"].mean())
        ci_lo, ci_hi = _bootstrap_ci(values, n_resamples=bootstrap_resamples, seed=seed)
        grade = assign_grade(mean_iq)

    coverage_pct = (
        100.0 * n_evaluated / n_in_neutral if n_in_neutral else float("nan")
    )

    return DatasetSummary(
        variant=variant,
        n_evaluated=n_evaluated,
        n_failed=n_failed,
        coverage_pct=round(coverage_pct, 3),
        mean_item_quality=round(mean_iq, 4) if mean_iq == mean_iq else mean_iq,
        semantic_pass_rate=round(sem_pass, 4) if sem_pass == sem_pass else sem_pass,
        mean_naturalness=round(mean_nat, 4) if mean_nat == mean_nat else mean_nat,
        mean_coherence=round(mean_coh, 4) if mean_coh == mean_coh else mean_coh,
        ci_lo=round(ci_lo, 4) if ci_lo == ci_lo else ci_lo,
        ci_hi=round(ci_hi, 4) if ci_hi == ci_hi else ci_hi,
        dataset_quality_grade=grade,
    )


def _jaccard(a: Iterable[str], b: Iterable[str]) -> float:
    sa = {x.lower().strip() for x in (a or []) if str(x).strip()}
    sb = {x.lower().strip() for x in (b or []) if str(x).strip()}
    if not sa and not sb:
        return float("nan")
    union = sa | sb
    if not union:
        return float("nan")
    return len(sa & sb) / len(union)


def compute_reliability(
    variant: str,
    run1: pd.DataFrame,
    run2: pd.DataFrame,
) -> dict[str, Any]:
    """Return one reliability row joining run-1 and run-2 records by idx."""
    if run1.empty or run2.empty:
        return {
            "variant": variant,
            "n_retest": 0,
            "rho_semantic_sim": float("nan"),
            "rho_emotion_naturalness": float("nan"),
            "rho_emotion_coherence": float("nan"),
            "kappa_semantic_pass": float("nan"),
            "mad_semantic_sim": float("nan"),
            "mad_emotion_naturalness": float("nan"),
            "mad_emotion_coherence": float("nan"),
            "jaccard_emotions": float("nan"),
            "low_reliability": True,
        }

    a = build_items_dataframe(run1).copy()
    b = build_items_dataframe(run2).copy()
    a["idx"] = a["idx"].astype(str)
    b["idx"] = b["idx"].astype(str)
    a = a.drop_duplicates(subset=["idx"], keep="last")
    b = b.drop_duplicates(subset=["idx"], keep="last")

    merged = a.merge(b, on="idx", suffixes=("_1", "_2"), how="inner")
    if merged.empty:
        return {
            "variant": variant,
            "n_retest": 0,
            "rho_semantic_sim": float("nan"),
            "rho_emotion_naturalness": float("nan"),
            "rho_emotion_coherence": float("nan"),
            "kappa_semantic_pass": float("nan"),
            "mad_semantic_sim": float("nan"),
            "mad_emotion_naturalness": float("nan"),
            "mad_emotion_coherence": float("nan"),
            "jaccard_emotions": float("nan"),
            "low_reliability": True,
        }

    row: dict[str, Any] = {"variant": variant, "n_retest": int(len(merged))}

    rhos: dict[str, float] = {}
    mads: dict[str, float] = {}
    for field in SCALAR_FIELDS:
        col1 = pd.to_numeric(merged[f"{field}_1"], errors="coerce")
        col2 = pd.to_numeric(merged[f"{field}_2"], errors="coerce")
        mask = col1.notna() & col2.notna()
        if mask.sum() < 3 or col1[mask].nunique() < 2 or col2[mask].nunique() < 2:
            rhos[field] = float("nan")
        else:
            rho, _p = spearmanr(col1[mask], col2[mask])
            rhos[field] = float(rho) if rho == rho else float("nan")
        mads[field] = float((col1 - col2).abs().mean()) if mask.any() else float("nan")

    pass1 = merged["semantic_pass_1"].fillna(False).astype(bool).astype(int).to_numpy()
    pass2 = merged["semantic_pass_2"].fillna(False).astype(bool).astype(int).to_numpy()
    if pass1.size and (pass1.tolist() != pass2.tolist() or set(pass1.tolist()) | set(pass2.tolist()) == {0, 1}):
        try:
            kappa = float(cohen_kappa_score(pass1, pass2))
        except Exception:
            kappa = float("nan")
    else:
        kappa = float("nan")

    jaccards: list[float] = []
    for _, r in merged.iterrows():
        j = _jaccard(r.get("emotions_1") or [], r.get("emotions_2") or [])
        if j == j:
            jaccards.append(j)
    jaccard_mean = float(np.mean(jaccards)) if jaccards else float("nan")

    rhos_scalar = [v for v in rhos.values() if v == v]
    low = bool(any(v < RELIABILITY_RHO_MIN for v in rhos_scalar))

    row.update(
        {
            "rho_semantic_sim": round(rhos["semantic_sim"], 4) if rhos["semantic_sim"] == rhos["semantic_sim"] else rhos["semantic_sim"],
            "rho_emotion_naturalness": round(rhos["emotion_naturalness"], 4) if rhos["emotion_naturalness"] == rhos["emotion_naturalness"] else rhos["emotion_naturalness"],
            "rho_emotion_coherence": round(rhos["emotion_coherence"], 4) if rhos["emotion_coherence"] == rhos["emotion_coherence"] else rhos["emotion_coherence"],
            "kappa_semantic_pass": round(kappa, 4) if kappa == kappa else kappa,
            "mad_semantic_sim": round(mads["semantic_sim"], 4) if mads["semantic_sim"] == mads["semantic_sim"] else mads["semantic_sim"],
            "mad_emotion_naturalness": round(mads["emotion_naturalness"], 4) if mads["emotion_naturalness"] == mads["emotion_naturalness"] else mads["emotion_naturalness"],
            "mad_emotion_coherence": round(mads["emotion_coherence"], 4) if mads["emotion_coherence"] == mads["emotion_coherence"] else mads["emotion_coherence"],
            "jaccard_emotions": round(jaccard_mean, 4) if jaccard_mean == jaccard_mean else jaccard_mean,
            "low_reliability": low,
        }
    )
    return row


def analyze(
    variants_to_run: list[str],
    *,
    bootstrap_resamples: int,
    seed: int,
    n_in_neutral: int,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, pd.DataFrame]]:
    """Run the analysis. Returns (dataset_quality_df, reliability_df, per-variant items)."""
    ensure_dirs()
    items_by_variant: dict[str, pd.DataFrame] = {}
    summaries: list[DatasetSummary] = []
    reliability_rows: list[dict[str, Any]] = []

    for variant in variants_to_run:
        run1_raw = _read_jsonl(raw_jsonl_path(variant, run=1))
        items_df = build_items_dataframe(run1_raw)
        items_by_variant[variant] = items_df

        out_path = items_csv_path(variant)
        if not items_df.empty:
            items_df.to_csv(out_path, index=False)

        summary = summarize_variant(
            variant=variant,
            items_df=items_df,
            n_in_neutral=n_in_neutral,
            bootstrap_resamples=bootstrap_resamples,
            seed=seed,
        )
        summaries.append(summary)

        run2_raw = _read_jsonl(raw_jsonl_path(variant, run=2))
        reliability_rows.append(compute_reliability(variant, run1_raw, run2_raw))

    dataset_quality = pd.DataFrame([s.__dict__ for s in summaries])
    reliability = pd.DataFrame(reliability_rows)

    if not reliability.empty:
        low_set = set(reliability.loc[reliability["low_reliability"], "variant"].tolist())
        dataset_quality["dataset_quality_grade"] = dataset_quality.apply(
            lambda r: f"{r['dataset_quality_grade']} (low reliability)"
            if r["variant"] in low_set and not r["dataset_quality_grade"].endswith("(low reliability)")
            else r["dataset_quality_grade"],
            axis=1,
        )

    dataset_quality.to_csv(DATASET_QUALITY_CSV, index=False)
    reliability.to_csv(RELIABILITY_CSV, index=False)
    return dataset_quality, reliability, items_by_variant


def parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Aggregate validation results.")
    parser.add_argument(
        "--variants",
        type=str,
        default=",".join(VARIANT_KEYS),
        help="Comma-separated variant keys (default all 8).",
    )
    parser.add_argument(
        "--bootstrap",
        type=int,
        default=BOOTSTRAP_RESAMPLES,
        help="Bootstrap resamples for the mean_item_quality CI.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=RANDOM_STATE,
        help="RNG seed (default %(default)s).",
    )
    parser.add_argument(
        "--n-neutral",
        type=int,
        default=1360,
        help="Total items in neutral baseline (denominator for coverage_pct).",
    )
    return parser.parse_args(list(argv) if argv is not None else None)


def main(argv: Iterable[str] | None = None) -> int:
    args = parse_args(argv)
    requested = [v.strip() for v in args.variants.split(",") if v.strip()]
    unknown = [v for v in requested if v not in VARIANT_KEYS]
    if unknown:
        print(f"ERROR: unknown variant(s) {unknown}", file=sys.stderr)
        return 2

    dataset_quality, reliability, _ = analyze(
        variants_to_run=requested,
        bootstrap_resamples=args.bootstrap,
        seed=args.seed,
        n_in_neutral=args.n_neutral,
    )
    print("Dataset quality (model:", MODEL_NAME, ")")
    print(dataset_quality.to_string(index=False))
    print()
    print("Reliability")
    print(reliability.to_string(index=False))
    print(f"\nWrote: {DATASET_QUALITY_CSV}\nWrote: {RELIABILITY_CSV}\nItems CSVs in: {ITEMS_DIR}")
    print(f"Datasets dir: {DATASETS_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
