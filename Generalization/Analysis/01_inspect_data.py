"""Step 01: Load all decision CSVs, join topic labels, write validity report.

Outputs:
- ``gen_long.csv``: tidy long-format frame [idx, model, mode, choice, topic_group].
- ``01_validity_report.md``: human-readable Markdown report.
"""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pandas as pd

from data_loader import (
    ANALYSIS_DIR,
    DECISIONS_DIR,
    MODELS,
    MODES,
    NEUTRAL_REFERENCE_CSV,
    TOPIC_LABELS_CSV,
    df_to_md,
    load_long_frame,
    load_reference_idx,
    load_topic_map,
    per_cell_info,
)


GEN_LONG_CSV = ANALYSIS_DIR / "gen_long.csv"
VALIDITY_REPORT_MD = ANALYSIS_DIR / "01_validity_report.md"


def main() -> None:
    reference_idx = load_reference_idx()
    long_df = load_long_frame(reference_idx=reference_idx)
    topic_map = load_topic_map()
    long_df = long_df.merge(topic_map, on="idx", how="left")
    long_df["topic_group"] = long_df["topic_group"].astype("string").fillna("Unknown")
    long_df.to_csv(GEN_LONG_CSV, index=False)

    infos = per_cell_info()
    info_df = pd.DataFrame(
        [
            {
                "model": ci.model,
                "mode": ci.mode,
                "n_rows": ci.n_rows,
                "n_unique_idx": ci.n_unique_idx,
                "n_valid": ci.n_valid,
                "valid_rate": ci.n_valid / max(ci.n_unique_idx, 1),
                "n_invalid": ci.n_invalid,
                "n_api_error": ci.n_api_error,
                "path": str(ci.path.relative_to(DECISIONS_DIR.parent)),
            }
            for ci in infos
        ]
    )

    pivot = info_df.pivot_table(
        index="model", columns="mode", values="n_valid", aggfunc="first"
    ).reindex(index=list(MODELS), columns=list(MODES))
    valid_rate_pivot = info_df.pivot_table(
        index="model", columns="mode", values="valid_rate", aggfunc="first"
    ).reindex(index=list(MODELS), columns=list(MODES))
    coverage_pivot = info_df.pivot_table(
        index="model", columns="mode", values="n_unique_idx", aggfunc="first"
    ).reindex(index=list(MODELS), columns=list(MODES))

    # Reference idx coverage: is every reference idx present per (model, mode)?
    presence = (
        long_df.assign(present=long_df["choice"].notna())
        .groupby(["model", "mode"])["present"]
        .sum()
        .unstack("mode")
        .reindex(index=list(MODELS), columns=list(MODES))
    )

    # Choice-1 base rate per (model, mode) - useful sanity for Claim 4 audit.
    base_rate = (
        long_df.assign(is1=(long_df["choice"] == 1).astype(float))
        .where(long_df["choice"].notna())
        .groupby(["model", "mode"])["is1"]
        .mean()
        .unstack("mode")
        .reindex(index=list(MODELS), columns=list(MODES))
    )

    lines: list[str] = []
    lines.append("# Generalization Data Validity Report")
    lines.append("")
    lines.append(dedent(f"""
        - Reference dilemma set: `{NEUTRAL_REFERENCE_CSV}` (N={len(reference_idx)} idx).
        - Decision CSV root: `{DECISIONS_DIR}`.
        - Topic labels: `{TOPIC_LABELS_CSV}`.
        - Cells: {len(MODELS)} models x {len(MODES)} modes = 16; one run per cell.
        - Total rows in long frame (reference x model x mode): {len(long_df):,}.
    """).strip())
    lines.append("")
    lines.append("## Per-cell row counts (unique idx in CSV)")
    lines.append("")
    lines.append(df_to_md(coverage_pivot.rename_axis("model")))
    lines.append("")
    lines.append("## Per-cell valid decisions (choice in {1, 2})")
    lines.append("")
    lines.append(df_to_md(pivot.rename_axis("model")))
    lines.append("")
    lines.append("## Per-cell valid rate")
    lines.append("")
    lines.append(df_to_md(valid_rate_pivot.rename_axis("model")))
    lines.append("")
    lines.append("## Reference idx covered (presence in long frame after merge)")
    lines.append("")
    lines.append(df_to_md(presence.rename_axis("model")))
    lines.append("")
    lines.append("## Choice-1 base rate per cell (sanity for Claim 4)")
    lines.append("")
    lines.append(df_to_md(base_rate.rename_axis("model")))
    lines.append("")

    # Topic coverage
    n_topic = int(long_df["topic_group"].nunique())
    topic_counts = (
        long_df.drop_duplicates(subset=["idx"])  # one row per dilemma
        .groupby("topic_group")
        .size()
        .sort_values(ascending=False)
        .to_frame("n_dilemmas")
    )
    lines.append(f"## Topic coverage ({n_topic} unique topic_groups)")
    lines.append("")
    lines.append(df_to_md(topic_counts))
    lines.append("")

    # Detailed per-cell table at the bottom
    lines.append("## Detailed per-cell information")
    lines.append("")
    cols = ["model", "mode", "n_rows", "n_unique_idx", "n_valid", "valid_rate", "n_invalid", "n_api_error", "path"]
    lines.append(df_to_md(info_df[cols]))
    lines.append("")

    VALIDITY_REPORT_MD.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {GEN_LONG_CSV}")
    print(f"Wrote {VALIDITY_REPORT_MD}")


if __name__ == "__main__":
    main()
