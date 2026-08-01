"""Claim 2: Reasoning stabilizes choices.

Evidence (agreement-based; action-bias swap is intentionally out of scope):

- Neutral-CoT preserves Neutral (per-model and pooled deviation).
- EA preserves more than EI ("anchoring under emotion") via:
  - pooled Dev(EI) - Dev(EA) with paired bootstrap CI;
  - paired McNemar within model (EA-disagrees vs EI-disagrees) on shared
    Neutral-valid idx.
- Cross-model agreement under reasoning-augmented modes is higher than under
  matched non-reasoning modes.
- Cross-mode within-family agreement: agree(Neutral, Neutral-CoT) vs
  agree(EI, EA) per model and pooled.

Outputs:
- 03_claim2_stabilization.csv (per-model summary).
- 03_claim2_within_family.csv (cross-mode within-family agreement).
- 03_claim2_stabilization_report.md.
"""

from __future__ import annotations

from itertools import combinations
from pathlib import Path
from typing import Dict, List

import numpy as np
import pandas as pd

from data_loader import (
    ANALYSIS_DIR,
    MODELS,
    MODES,
    df_to_md,
    load_long_frame,
    load_reference_idx,
    load_topic_map,
)
from paired_design import build_paired_tables, effective_alignment
from stats import bootstrap_ci, bootstrap_diff_ci, mcnemar_pvalue, pairwise_agreement_rate


PER_MODEL_CSV = ANALYSIS_DIR / "03_claim2_stabilization.csv"
WITHIN_FAMILY_CSV = ANALYSIS_DIR / "03_claim2_within_family.csv"
REPORT_OUT = ANALYSIS_DIR / "03_claim2_stabilization_report.md"


def _deviation_vector(table):
    """Per-idx indicator (Neutral-valid): 1 = method disagrees, 0 = agrees."""
    df = table.df[table.df["ref_valid"]]
    return np.where(df["both_valid"] & df["agree"].fillna(False), 0.0, 1.0)


def _ea_ei_anchoring(tables) -> Dict[str, object]:
    """Paired Dev(EI) - Dev(EA) on shared Neutral-valid idx (per model and pooled)."""
    rows = []
    pooled_dev_ei: List[np.ndarray] = []
    pooled_dev_ea: List[np.ndarray] = []
    for model in MODELS:
        ea = tables[(model, "EA")].df
        ei = tables[(model, "EI")].df
        # Restrict to shared neutral-valid idx (same row index).
        common = ea.index.intersection(ei.index)
        ea_sub = ea.loc[common]
        ei_sub = ei.loc[common]
        mask = ea_sub["ref_valid"] & ei_sub["ref_valid"]
        ea_sub = ea_sub[mask]
        ei_sub = ei_sub[mask]
        dev_ea = np.where(
            ea_sub["both_valid"] & ea_sub["agree"].fillna(False), 0.0, 1.0
        )
        dev_ei = np.where(
            ei_sub["both_valid"] & ei_sub["agree"].fillna(False), 0.0, 1.0
        )
        diff = bootstrap_diff_ci(dev_ei, dev_ea, paired=True)
        # McNemar on EA-disagrees vs EI-disagrees discordant cells.
        ea_dis = dev_ea.astype(bool)
        ei_dis = dev_ei.astype(bool)
        b = int(((~ea_dis) & ei_dis).sum())  # EA agrees, EI disagrees
        c = int((ea_dis & (~ei_dis)).sum())  # EA disagrees, EI agrees
        p_mc = mcnemar_pvalue(b, c)
        rows.append(
            {
                "model": model,
                "n_paired": int(dev_ea.size),
                "dev_ea": float(dev_ea.mean()),
                "dev_ei": float(dev_ei.mean()),
                "ei_minus_ea_pp": diff.point * 100,
                "diff_ci_low_pp": diff.low * 100,
                "diff_ci_high_pp": diff.high * 100,
                "mcnemar_b_ea_agrees_ei_disagrees": b,
                "mcnemar_c_ea_disagrees_ei_agrees": c,
                "mcnemar_p": p_mc,
            }
        )
        pooled_dev_ei.append(dev_ei)
        pooled_dev_ea.append(dev_ea)
    pooled = bootstrap_diff_ci(
        np.concatenate(pooled_dev_ei), np.concatenate(pooled_dev_ea), paired=True
    )
    pooled_ea = np.concatenate(pooled_dev_ea)
    pooled_ei = np.concatenate(pooled_dev_ei)
    b = int(((~pooled_ea.astype(bool)) & pooled_ei.astype(bool)).sum())
    c = int((pooled_ea.astype(bool) & (~pooled_ei.astype(bool))).sum())
    p_mc = mcnemar_pvalue(b, c)
    rows.append(
        {
            "model": "POOLED",
            "n_paired": int(pooled_ea.size),
            "dev_ea": float(pooled_ea.mean()),
            "dev_ei": float(pooled_ei.mean()),
            "ei_minus_ea_pp": pooled.point * 100,
            "diff_ci_low_pp": pooled.low * 100,
            "diff_ci_high_pp": pooled.high * 100,
            "mcnemar_b_ea_agrees_ei_disagrees": b,
            "mcnemar_c_ea_disagrees_ei_agrees": c,
            "mcnemar_p": p_mc,
        }
    )
    return pd.DataFrame(rows)


def _within_family_table(long_df: pd.DataFrame) -> pd.DataFrame:
    """Cross-mode within-family agreement per model and pooled."""
    wide = long_df.pivot_table(
        index=["idx", "model"], columns="mode", values="choice", aggfunc="first"
    ).reset_index()
    rows = []
    pooled_rows: Dict[str, List[float]] = {"reasoning": [], "emotional": []}
    for model in MODELS:
        sub = wide[wide["model"] == model]
        n_cot, _ = pairwise_agreement_rate(sub["Neutral"], sub["Neutral-CoT"])
        e_cot, _ = pairwise_agreement_rate(sub["EI"], sub["EA"])
        # Per-idx indicators for pooled CI
        m1 = sub["Neutral"].notna() & sub["Neutral-CoT"].notna()
        ind_r = (sub.loc[m1, "Neutral"].astype(int) == sub.loc[m1, "Neutral-CoT"].astype(int)).to_numpy(dtype=float)
        m2 = sub["EI"].notna() & sub["EA"].notna()
        ind_e = (sub.loc[m2, "EI"].astype(int) == sub.loc[m2, "EA"].astype(int)).to_numpy(dtype=float)
        rows.append(
            {
                "model": model,
                "agreement_Neutral_vs_NCoT": n_cot,
                "agreement_EI_vs_EA": e_cot,
                "n_NCoT_pair": int(ind_r.size),
                "n_EIEA_pair": int(ind_e.size),
            }
        )
        pooled_rows["reasoning"].extend(ind_r.tolist())
        pooled_rows["emotional"].extend(ind_e.tolist())
    ci_r = bootstrap_ci(np.asarray(pooled_rows["reasoning"]))
    ci_e = bootstrap_ci(np.asarray(pooled_rows["emotional"]))
    rows.append(
        {
            "model": "POOLED",
            "agreement_Neutral_vs_NCoT": ci_r.point,
            "agreement_EI_vs_EA": ci_e.point,
            "n_NCoT_pair": len(pooled_rows["reasoning"]),
            "n_EIEA_pair": len(pooled_rows["emotional"]),
            "NCoT_ci_low": ci_r.low,
            "NCoT_ci_high": ci_r.high,
            "EIEA_ci_low": ci_e.low,
            "EIEA_ci_high": ci_e.high,
        }
    )
    return pd.DataFrame(rows)


def _per_model_summary(tables) -> pd.DataFrame:
    rows = []
    for model in MODELS:
        for method in ("Neutral-CoT", "EI", "EA"):
            stats = effective_alignment(tables[(model, method)])
            rows.append(
                {
                    "model": model,
                    "mode": method,
                    "EfA": stats["EfA"],
                    "CMR": stats["CMR"],
                    "deviation_pp": (1 - stats["EfA"]) * 100 if not np.isnan(stats["EfA"]) else float("nan"),
                }
            )
    return pd.DataFrame(rows)


def _cross_model_agreement_by_mode(long_df: pd.DataFrame) -> pd.DataFrame:
    """Mean 6-pair agreement per mode, on per-mode-valid idx (not requiring all 4)."""
    rows = []
    for mode in MODES:
        sub = long_df[long_df["mode"] == mode].pivot_table(
            index="idx", columns="model", values="choice", aggfunc="first"
        )
        sub = sub.reindex(columns=list(MODELS))
        rates = []
        ns = []
        for left, right in combinations(MODELS, 2):
            rate, n = pairwise_agreement_rate(sub[left], sub[right])
            rates.append(rate)
            ns.append(n)
        rows.append(
            {
                "mode": mode,
                "mean_pair_agreement": float(np.nanmean(rates)),
                "min_pair_agreement": float(np.nanmin(rates)),
                "max_pair_agreement": float(np.nanmax(rates)),
                "n_pairs": len(rates),
                "mean_n_compared": float(np.mean(ns)),
            }
        )
    return pd.DataFrame(rows)


def main() -> None:
    reference_idx = load_reference_idx()
    long_df = load_long_frame(reference_idx=reference_idx)
    long_df = long_df.merge(load_topic_map(), on="idx", how="left")
    tables = build_paired_tables(long_df)

    per_model = _per_model_summary(tables)
    per_model.to_csv(PER_MODEL_CSV, index=False)

    within_family = _within_family_table(long_df)
    within_family.to_csv(WITHIN_FAMILY_CSV, index=False)

    anchoring = _ea_ei_anchoring(tables)
    cross_model = _cross_model_agreement_by_mode(long_df)

    pooled_dev = (
        per_model.groupby("mode")
        .apply(lambda g: g["deviation_pp"].mean(), include_groups=False)
        .to_dict()
    )

    lines: List[str] = ["# Claim 2 - Reasoning stabilizes choices", ""]
    lines.append("Action bias (the swap counterfactual) is outside the scope of this study by design.")
    lines.append("All evidence here is agreement-based.")
    lines.append("")
    lines.append("## A. Neutral-CoT preserves Neutral (per-model deviation)")
    lines.append("")
    pm = per_model.copy()
    pm["EfA"] = pm["EfA"].astype(float)
    pm["CMR"] = pm["CMR"].astype(float)
    pm["deviation_pp"] = pm["deviation_pp"].astype(float)
    lines.append(df_to_md(pm, float_fmt="{:.4f}"))
    lines.append("")
    lines.append(
        f"Mean per-model deviation (pp): Neutral-CoT = {pooled_dev.get('Neutral-CoT', float('nan')):.2f}, "
        f"EI = {pooled_dev.get('EI', float('nan')):.2f}, EA = {pooled_dev.get('EA', float('nan')):.2f}."
    )
    lines.append("Paper benchmark: Neutral-CoT 6.50 pp << EA 14.51 pp / EI 15.64 pp.")
    lines.append("")
    lines.append("## B. EA anchors EI under emotion (paired)")
    lines.append("")
    anc = anchoring.copy()
    lines.append(
        df_to_md(
            anc[
                [
                    "model",
                    "n_paired",
                    "dev_ei",
                    "dev_ea",
                    "ei_minus_ea_pp",
                    "diff_ci_low_pp",
                    "diff_ci_high_pp",
                    "mcnemar_b_ea_agrees_ei_disagrees",
                    "mcnemar_c_ea_disagrees_ei_agrees",
                    "mcnemar_p",
                ]
            ],
            float_fmt="{:.4f}",
        )
    )
    lines.append("Paper benchmark: pooled EI 15.64 pp vs EA 14.51 pp -> +1.13 pp anchoring (EI - EA).")
    lines.append("")
    lines.append("## C. Cross-mode within-family agreement (per model and pooled)")
    lines.append("")
    wf = within_family.copy()
    lines.append(df_to_md(wf, float_fmt="{:.4f}"))
    lines.append("Paper benchmark: agree(Neutral, Neutral-CoT) = 98.84%; agree(EI, EA) = 97.24%.")
    lines.append("")
    lines.append("## D. Cross-model 6-pair mean agreement per mode")
    lines.append("")
    cm = cross_model.copy()
    cm["mean_pair_agreement_pct"] = cm["mean_pair_agreement"] * 100
    cm["min_pair_agreement_pct"] = cm["min_pair_agreement"] * 100
    cm["max_pair_agreement_pct"] = cm["max_pair_agreement"] * 100
    lines.append(
        df_to_md(
            cm[
                ["mode", "n_pairs", "mean_n_compared", "mean_pair_agreement_pct", "min_pair_agreement_pct", "max_pair_agreement_pct"]
            ],
            float_fmt="{:.2f}",
        )
    )
    lines.append("Stabilization sign check: agreement(Neutral-CoT) > agreement(Neutral)?  agreement(EA) > agreement(EI)?")
    lines.append("Paper baseline: Neutral 96.99%, Neutral-CoT 95.67%, EI 90.08%, EA 90.82%.")
    lines.append("")
    REPORT_OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {PER_MODEL_CSV}")
    print(f"Wrote {WITHIN_FAMILY_CSV}")
    print(f"Wrote {REPORT_OUT}")


if __name__ == "__main__":
    main()
