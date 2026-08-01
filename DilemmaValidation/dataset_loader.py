"""
Dataset loader for the DilemmaValidation experiment.

Loads the neutral baseline plus all 8 emotional variants, normalizes
columns, dedupes idx, and reports a per-variant coverage table.

The 8 variant keys are exactly: CN, CT, R1, V3, GPT_5, GPT_o4, QwenN, QwenT.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from config import NEUTRAL_CSV, VARIANT_FILES, VARIANT_KEYS, COVERAGE_CSV, ensure_dirs


SITUATION_COL: str = "situation"
RENAME_MAP: dict[str, str] = {
    "dilemma_situation": SITUATION_COL,
    "emotional_situation": SITUATION_COL,
}


@dataclass(frozen=True)
class CoverageRow:
    """Per-CSV coverage record for the coverage report."""

    variant: str
    n_in_file: int
    n_with_text: int
    n_matched_to_neutral: int


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Drop stray 'Unnamed:' columns and strip whitespace from column names."""
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]
    keep = [c for c in df.columns if c and not c.lower().startswith("unnamed")]
    return df[keep]


def _rename_situation(df: pd.DataFrame) -> pd.DataFrame:
    cols = {c: RENAME_MAP[c] for c in df.columns if c in RENAME_MAP}
    if cols:
        df = df.rename(columns=cols)
    return df


def _load_csv(path: Path, variant: str) -> pd.DataFrame:
    """Load and normalize one CSV: cast idx to str, dedupe, drop empties."""
    if not path.is_file():
        raise FileNotFoundError(f"[{variant}] CSV not found: {path}")
    df = pd.read_csv(path)
    df = _normalize_columns(df)
    df = _rename_situation(df)

    if "idx" not in df.columns:
        raise ValueError(f"[{variant}] missing 'idx' column in {path}")
    if SITUATION_COL not in df.columns:
        raise ValueError(
            f"[{variant}] missing '{SITUATION_COL}' (dilemma_situation/emotional_situation) "
            f"in {path}"
        )

    df["idx"] = df["idx"].astype(str).str.strip()
    if "action1" in df.columns:
        df["action1"] = df["action1"].astype(str).str.strip()
    if "action2" in df.columns:
        df["action2"] = df["action2"].astype(str).str.strip()
    df[SITUATION_COL] = df[SITUATION_COL].astype(str).str.strip()

    df = df[df["idx"].astype(bool) & (df["idx"].str.lower() != "nan")]

    df["_has_text"] = df[SITUATION_COL].astype(bool) & (
        df[SITUATION_COL].str.lower() != "nan"
    )
    df = df.sort_values(by=["idx", "_has_text"], ascending=[True, False], kind="stable")
    df = df.drop_duplicates(subset=["idx"], keep="first")
    df = df.drop(columns=["_has_text"])
    return df.reset_index(drop=True)


def load_neutral() -> pd.DataFrame:
    """Load the neutral baseline as a DataFrame with idx/situation/action1/action2."""
    df = _load_csv(NEUTRAL_CSV, variant="Neutral")
    required = {"idx", SITUATION_COL, "action1", "action2"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(
            f"Neutral CSV missing required columns: {sorted(missing)} ({NEUTRAL_CSV})"
        )
    return df[["idx", SITUATION_COL, "action1", "action2"]].copy()


def load_variants() -> tuple[dict[str, pd.DataFrame], pd.DataFrame, pd.DataFrame]:
    """
    Load the neutral baseline and all 8 variants.

    Returns
    -------
    variants : dict[str, DataFrame]
        Keys are the 8 variant labels. Each frame has columns
        ['idx', 'situation', 'action1', 'action2'] (actions fall back to
        the neutral row's actions when missing in the variant file).
    neutral : DataFrame
        Neutral baseline keyed by idx.
    coverage : DataFrame
        One row per variant with columns
        [variant, n_in_file, n_with_text, n_matched_to_neutral].
    """
    ensure_dirs()
    neutral = load_neutral()
    neutral_idx = set(neutral["idx"].tolist())
    neutral_actions = neutral.set_index("idx")[["action1", "action2"]]

    variants: dict[str, pd.DataFrame] = {}
    coverage_rows: list[CoverageRow] = []

    for variant_key, path in VARIANT_FILES:
        df = _load_csv(path, variant=variant_key)
        n_in_file = len(df)
        has_text_mask = df[SITUATION_COL].astype(bool) & (
            df[SITUATION_COL].str.lower() != "nan"
        )
        n_with_text = int(has_text_mask.sum())
        df = df[has_text_mask].copy()

        if "action1" not in df.columns or df["action1"].eq("").all():
            df["action1"] = df["idx"].map(neutral_actions["action1"])
        else:
            empty_a1 = df["action1"].eq("") | df["action1"].isna()
            df.loc[empty_a1, "action1"] = df.loc[empty_a1, "idx"].map(
                neutral_actions["action1"]
            )
        if "action2" not in df.columns or df["action2"].eq("").all():
            df["action2"] = df["idx"].map(neutral_actions["action2"])
        else:
            empty_a2 = df["action2"].eq("") | df["action2"].isna()
            df.loc[empty_a2, "action2"] = df.loc[empty_a2, "idx"].map(
                neutral_actions["action2"]
            )

        df = df[df["idx"].isin(neutral_idx)].copy()
        n_matched = len(df)

        variants[variant_key] = df[["idx", SITUATION_COL, "action1", "action2"]].reset_index(
            drop=True
        )
        coverage_rows.append(
            CoverageRow(
                variant=variant_key,
                n_in_file=n_in_file,
                n_with_text=n_with_text,
                n_matched_to_neutral=n_matched,
            )
        )

    coverage = pd.DataFrame([row.__dict__ for row in coverage_rows])
    return variants, neutral, coverage


def coverage_markdown(coverage: pd.DataFrame) -> str:
    """Render the coverage DataFrame as a Markdown table."""
    header = "| variant | n_in_file | n_with_text | n_matched_to_neutral |"
    sep = "|---|---:|---:|---:|"
    body_rows: list[str] = []
    for _, row in coverage.iterrows():
        body_rows.append(
            f"| {row['variant']} | {row['n_in_file']} | {row['n_with_text']} | "
            f"{row['n_matched_to_neutral']} |"
        )
    return "\n".join([header, sep, *body_rows])


def build_join_table(
    variants: dict[str, pd.DataFrame], neutral: pd.DataFrame
) -> dict[str, pd.DataFrame]:
    """
    Build per-variant join tables keyed on idx.

    Each output frame has columns:
        idx, neutral_situation, variant_situation, action1, action2
    """
    neutral_lookup = neutral.set_index("idx")[
        [SITUATION_COL, "action1", "action2"]
    ].rename(columns={SITUATION_COL: "neutral_situation"})

    joins: dict[str, pd.DataFrame] = {}
    for variant_key, df in variants.items():
        merged = df.rename(columns={SITUATION_COL: "variant_situation"}).merge(
            neutral_lookup,
            how="inner",
            left_on="idx",
            right_index=True,
            suffixes=("", "_neutral"),
        )
        if "action1_neutral" in merged.columns:
            merged["action1"] = merged["action1"].where(
                merged["action1"].astype(bool), merged["action1_neutral"]
            )
            merged["action2"] = merged["action2"].where(
                merged["action2"].astype(bool), merged["action2_neutral"]
            )
            merged = merged.drop(columns=["action1_neutral", "action2_neutral"])
        merged = merged[
            ["idx", "neutral_situation", "variant_situation", "action1", "action2"]
        ]
        merged = merged.sort_values(by="idx", kind="stable").reset_index(drop=True)
        joins[variant_key] = merged
    return joins


def main() -> None:
    """CLI entry: print coverage table and write COVERAGE_CSV."""
    variants, neutral, coverage = load_variants()
    print(f"Neutral rows: {len(neutral)}")
    print()
    print(coverage_markdown(coverage))
    coverage.to_csv(COVERAGE_CSV, index=False)
    print(f"\nWrote coverage CSV -> {COVERAGE_CSV}")
    print(f"Variant keys: {VARIANT_KEYS}")

    joins = build_join_table(variants, neutral)
    print("\nJoined rows per variant:")
    for key, df in joins.items():
        print(f"  {key}: {len(df)}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise
