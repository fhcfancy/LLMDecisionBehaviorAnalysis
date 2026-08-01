"""Claim 3: Emotion shifts decisions much more than reasoning.

- Pooled deviation comparison (Dev_pool(EA), Dev_pool(EI), Dev_pool(N-CoT))
  with 95% paired bootstrap CIs (resample idx across all 4 models).
- Paired McNemar(EA vs Neutral-CoT) on the discordant 2x2 cells, pooled and
  per model. Significant ``c > b`` (EA disagrees + N-CoT agrees) provides
  direct paired evidence that emotion shifts choices more than reasoning.
- Effect ratio Dev(EA)/Dev(N-CoT) and Dev(EI)/Dev(N-CoT) with bootstrap CI.

Outputs:
- 04_claim3_magnitude.csv (pooled summary rows).
- 04_claim3_per_model_mcnemar.csv (per-model McNemar 2x2 cells and p-values).
- 04_claim3_magnitude_report.md.
"""

from __future__ import annotations

from typing import Dict, List

import numpy as np
import pandas as pd

from data_loader import (
    ANALYSIS_DIR,
    MODELS,
    df_to_md,
    load_long_frame,
    load_reference_idx,
    load_topic_map,
)
from paired_design import build_paired_tables
from stats import bootstrap_ci, bootstrap_diff_ci, mcnemar_pvalue


POOLED_CSV = ANALYSIS_DIR / "04_claim3_magnitude.csv"
MCNEMAR_CSV = ANALYSIS_DIR / "04_claim3_per_model_mcnemar.csv"
REPORT_OUT = ANALYSIS_DIR / "04_claim3_magnitude_report.md"


def _deviation_vector(table) -> np.ndarray:
    df = table.df[table.df["ref_valid"]]
    return np.where(df["both_valid"] & df["agree"].fillna(False), 0.0, 1.0)


def main() -> None:
    reference_idx = load_reference_idx()
    long_df = load_long_frame(reference_idx=reference_idx)
    long_df = long_df.merge(load_topic_map(), on="idx", how="left")
    tables = build_paired_tables(long_df)

    pooled_ea = np.concatenate([_deviation_vector(tables[(m, "EA")]) for m in MODELS])
    pooled_ei = np.concatenate([_deviation_vector(tables[(m, "EI")]) for m in MODELS])
    pooled_nc = np.concatenate(
        [_deviation_vector(tables[(m, "Neutral-CoT")]) for m in MODELS]
    )

    ci_ea = bootstrap_ci(pooled_ea)
    ci_ei = bootstrap_ci(pooled_ei)
    ci_nc = bootstrap_ci(pooled_nc)

    diff_ea_nc = bootstrap_diff_ci(pooled_ea, pooled_nc, paired=True)
    diff_ei_nc = bootstrap_diff_ci(pooled_ei, pooled_nc, paired=True)

    # Effect ratio via bootstrap of the indicator means.
    rng = np.random.default_rng(42)
    n = pooled_ea.size
    samples_idx = rng.integers(0, n, size=(2000, n))
    ea_samples = pooled_ea[samples_idx].mean(axis=1)
    ei_samples = pooled_ei[samples_idx].mean(axis=1)
    nc_samples = pooled_nc[samples_idx].mean(axis=1)
    eps = 1e-12
    ratio_ea = ea_samples / np.maximum(nc_samples, eps)
    ratio_ei = ei_samples / np.maximum(nc_samples, eps)
    ratio_ea_ci = (
        float(ci_ea.point / max(ci_nc.point, eps)),
        float(np.quantile(ratio_ea, 0.025)),
        float(np.quantile(ratio_ea, 0.975)),
    )
    ratio_ei_ci = (
        float(ci_ei.point / max(ci_nc.point, eps)),
        float(np.quantile(ratio_ei, 0.025)),
        float(np.quantile(ratio_ei, 0.975)),
    )

    # Paired McNemar(EA vs N-CoT) pooled across models on shared Neutral-valid idx.
    pooled_b = pooled_c = 0
    per_model_rows = []
    for model in MODELS:
        ea = tables[(model, "EA")].df
        nc = tables[(model, "Neutral-CoT")].df
        common = ea.index.intersection(nc.index)
        ea_sub = ea.loc[common]
        nc_sub = nc.loc[common]
        mask = ea_sub["ref_valid"] & nc_sub["ref_valid"]
        ea_sub = ea_sub[mask]
        nc_sub = nc_sub[mask]
        ea_dis = np.where(
            ea_sub["both_valid"] & ea_sub["agree"].fillna(False), 0.0, 1.0
        ).astype(bool)
        nc_dis = np.where(
            nc_sub["both_valid"] & nc_sub["agree"].fillna(False), 0.0, 1.0
        ).astype(bool)
        b = int(((~ea_dis) & nc_dis).sum())  # EA agrees, NCoT disagrees
        c = int((ea_dis & (~nc_dis)).sum())  # EA disagrees, NCoT agrees
        p_mc = mcnemar_pvalue(b, c)
        per_model_rows.append(
            {
                "model": model,
                "n_paired": int(len(ea_sub)),
                "dev_ea_pp": float(ea_dis.mean() * 100),
                "dev_ncot_pp": float(nc_dis.mean() * 100),
                "b_ea_agrees_ncot_disagrees": b,
                "c_ea_disagrees_ncot_agrees": c,
                "mcnemar_p": p_mc,
            }
        )
        pooled_b += b
        pooled_c += c
    pooled_p = mcnemar_pvalue(pooled_b, pooled_c)

    # EI vs N-CoT (for the second magnitude claim).
    pooled_b_ei = pooled_c_ei = 0
    per_model_ei_rows = []
    for model in MODELS:
        ei = tables[(model, "EI")].df
        nc = tables[(model, "Neutral-CoT")].df
        common = ei.index.intersection(nc.index)
        ei_sub = ei.loc[common]
        nc_sub = nc.loc[common]
        mask = ei_sub["ref_valid"] & nc_sub["ref_valid"]
        ei_sub = ei_sub[mask]
        nc_sub = nc_sub[mask]
        ei_dis = np.where(
            ei_sub["both_valid"] & ei_sub["agree"].fillna(False), 0.0, 1.0
        ).astype(bool)
        nc_dis = np.where(
            nc_sub["both_valid"] & nc_sub["agree"].fillna(False), 0.0, 1.0
        ).astype(bool)
        b = int(((~ei_dis) & nc_dis).sum())
        c = int((ei_dis & (~nc_dis)).sum())
        p_mc = mcnemar_pvalue(b, c)
        per_model_ei_rows.append(
            {
                "model": model,
                "n_paired": int(len(ei_sub)),
                "dev_ei_pp": float(ei_dis.mean() * 100),
                "dev_ncot_pp": float(nc_dis.mean() * 100),
                "b_ei_agrees_ncot_disagrees": b,
                "c_ei_disagrees_ncot_agrees": c,
                "mcnemar_p": p_mc,
            }
        )
        pooled_b_ei += b
        pooled_c_ei += c
    pooled_p_ei = mcnemar_pvalue(pooled_b_ei, pooled_c_ei)

    pooled_df = pd.DataFrame(
        [
            {
                "metric": "Pooled deviation EA (pp)",
                "value": ci_ea.point * 100,
                "ci_low_pp": ci_ea.low * 100,
                "ci_high_pp": ci_ea.high * 100,
                "n": int(pooled_ea.size),
            },
            {
                "metric": "Pooled deviation EI (pp)",
                "value": ci_ei.point * 100,
                "ci_low_pp": ci_ei.low * 100,
                "ci_high_pp": ci_ei.high * 100,
                "n": int(pooled_ei.size),
            },
            {
                "metric": "Pooled deviation Neutral-CoT (pp)",
                "value": ci_nc.point * 100,
                "ci_low_pp": ci_nc.low * 100,
                "ci_high_pp": ci_nc.high * 100,
                "n": int(pooled_nc.size),
            },
            {
                "metric": "EA - Neutral-CoT (pp, paired)",
                "value": diff_ea_nc.point * 100,
                "ci_low_pp": diff_ea_nc.low * 100,
                "ci_high_pp": diff_ea_nc.high * 100,
                "n": int(pooled_ea.size),
            },
            {
                "metric": "EI - Neutral-CoT (pp, paired)",
                "value": diff_ei_nc.point * 100,
                "ci_low_pp": diff_ei_nc.low * 100,
                "ci_high_pp": diff_ei_nc.high * 100,
                "n": int(pooled_ei.size),
            },
            {
                "metric": "Effect ratio EA/Neutral-CoT",
                "value": ratio_ea_ci[0],
                "ci_low_pp": ratio_ea_ci[1],
                "ci_high_pp": ratio_ea_ci[2],
                "n": int(pooled_ea.size),
            },
            {
                "metric": "Effect ratio EI/Neutral-CoT",
                "value": ratio_ei_ci[0],
                "ci_low_pp": ratio_ei_ci[1],
                "ci_high_pp": ratio_ei_ci[2],
                "n": int(pooled_ei.size),
            },
            {
                "metric": "Paired McNemar (EA vs Neutral-CoT) pooled: b",
                "value": pooled_b,
                "ci_low_pp": np.nan,
                "ci_high_pp": np.nan,
                "n": int(pooled_b + pooled_c),
            },
            {
                "metric": "Paired McNemar (EA vs Neutral-CoT) pooled: c",
                "value": pooled_c,
                "ci_low_pp": np.nan,
                "ci_high_pp": np.nan,
                "n": int(pooled_b + pooled_c),
            },
            {
                "metric": "Paired McNemar (EA vs Neutral-CoT) pooled: p",
                "value": pooled_p,
                "ci_low_pp": np.nan,
                "ci_high_pp": np.nan,
                "n": int(pooled_b + pooled_c),
            },
            {
                "metric": "Paired McNemar (EI vs Neutral-CoT) pooled: b",
                "value": pooled_b_ei,
                "ci_low_pp": np.nan,
                "ci_high_pp": np.nan,
                "n": int(pooled_b_ei + pooled_c_ei),
            },
            {
                "metric": "Paired McNemar (EI vs Neutral-CoT) pooled: c",
                "value": pooled_c_ei,
                "ci_low_pp": np.nan,
                "ci_high_pp": np.nan,
                "n": int(pooled_b_ei + pooled_c_ei),
            },
            {
                "metric": "Paired McNemar (EI vs Neutral-CoT) pooled: p",
                "value": pooled_p_ei,
                "ci_low_pp": np.nan,
                "ci_high_pp": np.nan,
                "n": int(pooled_b_ei + pooled_c_ei),
            },
        ]
    )
    pooled_df.to_csv(POOLED_CSV, index=False)

    per_model_df = pd.concat(
        [pd.DataFrame(per_model_rows).assign(comparison="EA_vs_NCoT"),
         pd.DataFrame(per_model_ei_rows).assign(comparison="EI_vs_NCoT")],
        ignore_index=True,
    )
    per_model_df.to_csv(MCNEMAR_CSV, index=False)

    lines: List[str] = ["# Claim 3 - Emotion shifts decisions much more than reasoning", ""]
    lines.append("## Pooled summary")
    lines.append("")
    lines.append(df_to_md(pooled_df, float_fmt="{:.4f}"))
    lines.append("")
    lines.append("## Per-model McNemar 2x2 (EA vs Neutral-CoT)")
    lines.append("")
    ea_df = (
        per_model_df[per_model_df["comparison"] == "EA_vs_NCoT"]
        .drop(columns=["comparison"])
        .dropna(axis=1, how="all")
        .reset_index(drop=True)
    )
    lines.append(df_to_md(ea_df, float_fmt="{:.4f}"))
    lines.append("")
    lines.append("## Per-model McNemar 2x2 (EI vs Neutral-CoT)")
    lines.append("")
    ei_df = (
        per_model_df[per_model_df["comparison"] == "EI_vs_NCoT"]
        .drop(columns=["comparison"])
        .dropna(axis=1, how="all")
        .reset_index(drop=True)
    )
    lines.append(df_to_md(ei_df, float_fmt="{:.4f}"))
    lines.append("")
    lines.append("## Paper anchors")
    lines.append("")
    lines.append("- Pooled deviation in paper: EA 14.51 pp, EI 15.64 pp, Neutral-CoT 6.50 pp.")
    lines.append("- Paper paired McNemar p (EA vs Neutral): 1.18e-33; (EI vs Neutral): 1.78e-24.")
    lines.append("- Effect ratio EA/Neutral-CoT in paper: ~2.23; EI/Neutral-CoT: ~2.41.")
    lines.append("")
    REPORT_OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {POOLED_CSV}")
    print(f"Wrote {MCNEMAR_CSV}")
    print(f"Wrote {REPORT_OUT}")


if __name__ == "__main__":
    main()
