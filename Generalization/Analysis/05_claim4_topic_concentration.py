"""Claim 4: shifts are systematic and topic-concentrated.

- Directional Choice-1 asymmetry per method (per-model and pooled), with
  exact binomial p vs 0.5 on the disagree subset.
- Topic-group drift heatmap data: per (method, topic_group) drift rate
  defined as Pr(method disagrees with Neutral | both valid).
- Per-model worst topic: for each (model, method) report the topic with the
  highest drift rate.
- Concentration metrics on per-topic pooled drift rates (under EA and EI):
  - top-3 topic share of total drift events
  - Gini coefficient over per-topic drift rates
- Cramer's V between {mode, model, topic_group} and disagree_with_neutral.

Outputs:
- 05_claim4_directional_shift.csv
- 05_claim4_topic_drift.csv
- 05_claim4_worst_topic_per_model.csv
- 05_claim4_concentration.csv
- 05_claim4_cramers_v.csv
- 05_claim4_topic_concentration_report.md
"""

from __future__ import annotations

from typing import Dict, List

import numpy as np
import pandas as pd

from data_loader import (
    ANALYSIS_DIR,
    MODELS,
    NON_NEUTRAL_MODES,
    df_to_md,
    load_long_frame,
    load_reference_idx,
    load_topic_map,
)
from paired_design import build_paired_tables
from stats import binomial_test_two_sided, cramers_v, gini_coefficient, topk_share


DIRECTIONAL_CSV = ANALYSIS_DIR / "05_claim4_directional_shift.csv"
TOPIC_DRIFT_CSV = ANALYSIS_DIR / "05_claim4_topic_drift.csv"
WORST_TOPIC_CSV = ANALYSIS_DIR / "05_claim4_worst_topic_per_model.csv"
CONCENTRATION_CSV = ANALYSIS_DIR / "05_claim4_concentration.csv"
CRAMERS_CSV = ANALYSIS_DIR / "05_claim4_cramers_v.csv"
REPORT_OUT = ANALYSIS_DIR / "05_claim4_topic_concentration_report.md"


def _directional_shift_table(tables) -> pd.DataFrame:
    rows = []
    pooled: Dict[str, List[int]] = {m: [] for m in NON_NEUTRAL_MODES}
    for method in NON_NEUTRAL_MODES:
        for model in MODELS:
            df = tables[(model, method)].df
            disagree = df[df["both_valid"] & ~df["agree"].fillna(False)]
            n_to_1 = int((disagree["y_method"] == 1).sum())
            n_to_2 = int((disagree["y_method"] == 2).sum())
            n = n_to_1 + n_to_2
            if n == 0:
                p = float("nan")
                share = float("nan")
                net = 0
            else:
                p = binomial_test_two_sided(n_to_1, n, 0.5)
                share = n_to_1 / n
                net = n_to_1 - n_to_2
            rows.append(
                {
                    "model": model,
                    "mode": method,
                    "n_disagree": n,
                    "n_to_1": n_to_1,
                    "n_to_2": n_to_2,
                    "choice1_share": share,
                    "net_shift_to_1": net,
                    "binomial_p_two_sided": p,
                }
            )
            pooled[method].extend(
                [1] * n_to_1 + [0] * n_to_2
            )
        # Pooled row
        vec = pooled[method]
        n = len(vec)
        n_to_1 = sum(vec)
        n_to_2 = n - n_to_1
        rows.append(
            {
                "model": "POOLED",
                "mode": method,
                "n_disagree": n,
                "n_to_1": n_to_1,
                "n_to_2": n_to_2,
                "choice1_share": (n_to_1 / n) if n else float("nan"),
                "net_shift_to_1": n_to_1 - n_to_2,
                "binomial_p_two_sided": binomial_test_two_sided(n_to_1, n, 0.5) if n else float("nan"),
            }
        )
    return pd.DataFrame(rows)


def _topic_drift_table(tables) -> pd.DataFrame:
    """Per (method, topic_group) drift rate, pooled across models."""
    rows = []
    for method in NON_NEUTRAL_MODES:
        all_records = []
        for model in MODELS:
            df = tables[(model, method)].df.reset_index()
            sub = df[df["both_valid"]].copy()
            sub["disagree"] = (~sub["agree"].fillna(False)).astype(int)
            all_records.append(sub[["idx", "topic_group", "disagree"]])
        joined = pd.concat(all_records, ignore_index=True)
        agg = (
            joined.groupby("topic_group", observed=True)
            .agg(n=("disagree", "size"), n_disagree=("disagree", "sum"))
            .reset_index()
        )
        agg["drift_rate"] = agg["n_disagree"] / agg["n"]
        agg["mode"] = method
        rows.append(agg)
    return pd.concat(rows, ignore_index=True)


def _worst_topic_per_model(tables) -> pd.DataFrame:
    rows = []
    for method in NON_NEUTRAL_MODES:
        for model in MODELS:
            df = tables[(model, method)].df.reset_index()
            sub = df[df["both_valid"]].copy()
            sub["disagree"] = (~sub["agree"].fillna(False)).astype(int)
            agg = (
                sub.groupby("topic_group", observed=True)
                .agg(n=("disagree", "size"), n_disagree=("disagree", "sum"))
                .reset_index()
            )
            # Require at least 30 paired idx in a topic for meaningfulness.
            agg = agg[agg["n"] >= 30].copy()
            if agg.empty:
                continue
            agg["drift_rate"] = agg["n_disagree"] / agg["n"]
            top = agg.sort_values("drift_rate", ascending=False).iloc[0]
            rows.append(
                {
                    "model": model,
                    "mode": method,
                    "worst_topic_group": top["topic_group"],
                    "drift_rate": float(top["drift_rate"]),
                    "n": int(top["n"]),
                    "n_disagree": int(top["n_disagree"]),
                }
            )
    return pd.DataFrame(rows)


def _concentration_table(topic_drift_df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for method in NON_NEUTRAL_MODES:
        sub = topic_drift_df[topic_drift_df["mode"] == method].copy()
        if sub.empty:
            continue
        # Use total disagreement counts per topic for top-K share / Gini.
        counts = sub["n_disagree"].to_numpy(dtype=float)
        rows.append(
            {
                "mode": method,
                "n_topics": int(len(sub)),
                "n_total_disagreements": int(counts.sum()),
                "top3_topic_share_of_disagreements": topk_share(counts, k=3),
                "gini_over_drift_rates": gini_coefficient(sub["drift_rate"].to_numpy()),
                "max_topic_drift_rate": float(sub["drift_rate"].max()),
                "max_topic_group": str(
                    sub.loc[sub["drift_rate"].idxmax(), "topic_group"]
                ),
            }
        )
    return pd.DataFrame(rows)


def _cramers_table(long_df: pd.DataFrame) -> pd.DataFrame:
    """Cramer's V (model, mode, topic) -> disagree_with_neutral.

    Restricts to (model, mode) rows where mode != Neutral and both Neutral and
    the row's mode are valid.
    """
    wide = long_df.pivot_table(
        index=["idx", "model"], columns="mode", values="choice", aggfunc="first"
    ).reset_index()
    records = []
    for method in NON_NEUTRAL_MODES:
        sub = wide[["idx", "model", "Neutral", method]].dropna(subset=["Neutral", method])
        sub = sub.rename(columns={method: "y_method"})
        sub["disagree"] = (
            sub["y_method"].astype("Int64") != sub["Neutral"].astype("Int64")
        ).astype(int)
        sub["mode"] = method
        records.append(sub[["idx", "model", "mode", "disagree"]])
    panel = pd.concat(records, ignore_index=True)
    panel = panel.merge(load_topic_map(), on="idx", how="left")
    panel["topic_group"] = panel["topic_group"].astype("string").fillna("Unknown")

    rows = []
    for col in ("mode", "model", "topic_group"):
        ct = pd.crosstab(panel[col], panel["disagree"]).to_numpy()
        v, p = cramers_v(ct)
        rows.append({"factor": col, "cramers_v": v, "chi2_p_value": p})
    return pd.DataFrame(rows)


def main() -> None:
    reference_idx = load_reference_idx()
    long_df = load_long_frame(reference_idx=reference_idx)
    long_df = long_df.merge(load_topic_map(), on="idx", how="left")
    tables = build_paired_tables(long_df)

    direction = _directional_shift_table(tables)
    direction.to_csv(DIRECTIONAL_CSV, index=False)

    topic_drift = _topic_drift_table(tables)
    topic_drift.to_csv(TOPIC_DRIFT_CSV, index=False)

    worst = _worst_topic_per_model(tables)
    worst.to_csv(WORST_TOPIC_CSV, index=False)

    concentration = _concentration_table(topic_drift)
    concentration.to_csv(CONCENTRATION_CSV, index=False)

    cramers = _cramers_table(long_df)
    cramers.to_csv(CRAMERS_CSV, index=False)

    lines: List[str] = ["# Claim 4 - Systematic, topic-concentrated drift", ""]
    lines.append("## A. Directional Choice-1 asymmetry on disagree-with-Neutral subset")
    lines.append("")
    lines.append(df_to_md(direction, float_fmt="{:.4f}"))
    lines.append("Paper anchor: EA = 62.45% toward Choice 1 (n=2,365, p<.001).")
    lines.append("")
    lines.append("## B. Topic-group drift rate per method (pooled across 4 models)")
    lines.append("")
    pivot = (
        topic_drift.pivot_table(
            index="topic_group", columns="mode", values="drift_rate", aggfunc="first"
        )
        .reindex(columns=list(NON_NEUTRAL_MODES))
        .sort_values(by="EA", ascending=False)
    )
    pivot_disp = pivot.copy() * 100
    lines.append(df_to_md(pivot_disp.rename_axis("topic_group"), float_fmt="{:.2f}"))
    lines.append("Cells in % (drift = disagrees-with-Neutral / both-valid).")
    lines.append("")
    lines.append("## C. Per-model worst topic")
    lines.append("")
    worst_disp = worst.copy()
    worst_disp["drift_rate_pct"] = worst_disp["drift_rate"] * 100
    lines.append(
        df_to_md(
            worst_disp[
                ["model", "mode", "worst_topic_group", "n", "n_disagree", "drift_rate_pct"]
            ].rename(columns={"drift_rate_pct": "worst drift rate (%)"}),
            float_fmt="{:.2f}",
        )
    )
    lines.append("Paper anchor (Fig. 11): R1 + EI + business_organization = 33.75%.")
    lines.append("")
    lines.append("## D. Concentration metrics (per topic-group pooled across models)")
    lines.append("")
    lines.append(df_to_md(concentration, float_fmt="{:.4f}"))
    lines.append("")
    lines.append("## E. Cramer's V (mode / model / topic_group -> disagree)")
    lines.append("")
    lines.append(df_to_md(cramers, float_fmt="{:.4f}"))
    lines.append("Paper anchor (Fig. 7 left, on flip rate not disagreement): topic_group > model > mode in marginal strength.")
    lines.append("")
    REPORT_OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {DIRECTIONAL_CSV}")
    print(f"Wrote {TOPIC_DRIFT_CSV}")
    print(f"Wrote {WORST_TOPIC_CSV}")
    print(f"Wrote {CONCENTRATION_CSV}")
    print(f"Wrote {CRAMERS_CSV}")
    print(f"Wrote {REPORT_OUT}")


if __name__ == "__main__":
    main()
