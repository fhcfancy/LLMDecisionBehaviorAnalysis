"""
Consistency analysis aligned with formal definitions:

1) For each (mode m, model k), define:
   C_{m,k} = { i : y_{m,k,r}(i) in {1,2}, for r in {1,2,3} }
2) Item-level indicator:
   Consistent_{m,k}(i) = 1[ |{y_{m,k,r}(i)}_{r=1}^3| = 1 ]
3) Rate:
   ConsistencyRate_{m,k} =
      sum_{i in C_{m,k}} Consistent_{m,k}(i) / |C_{m,k}|
4) After filtering to perfect within-condition agreement, compute per-item
   agreement score over consensus vector:
   AgreementScore(i) = (1 / C(K,2)) * sum_{a<b} 1[c_a^{(i)} = c_b^{(i)}]

Required figures:
- Figure 1: Cross-mode agreement heatmap (overall + per-model)
- Figure 2: Standalone consistency bar chart (mode x model)
"""

from __future__ import annotations

import argparse
import itertools
import math
import re
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import matplotlib.pyplot as plt
import pandas as pd


MODES: Sequence[str] = ("Neutral", "Neutral-CoT", "EI", "EA")
MODE_SPECS = {
    "EA": ("EmotionalAnalytic", "EA"),
    "EI": ("EmotionalIntuitive", "EI"),
    "Neutral": ("Neutral", "Neutral"),
    "Neutral-CoT": ("Neutral-CoT", "Neutral-CoT"),
}
MODE_SLUG = {"EA": "EA", "EI": "EI", "Neutral": "Neutral", "Neutral-CoT": "Neutral-CoT"}
MODEL_ORDER: Sequence[str] = ("CN", "CT", "R1", "V3")
REQUIRED_RUNS: Sequence[int] = (1, 2, 3)
VALID_CHOICES = {1, 2}


def _extract_run_id(path: Path, prefix: str, model: str) -> Optional[int]:
    stem = path.stem
    base = f"{prefix}_{model}"
    if stem == base:
        return 1

    suffix_match = re.match(r"^" + re.escape(base) + r"[_-]([0-9]+)$", stem, flags=re.IGNORECASE)
    if suffix_match:
        return int(suffix_match.group(1))

    for pattern in (r"(?:^|[_-])run([0-9]+)(?:$|[_-])", r"(?:^|[_-])r([0-9]+)(?:$|[_-])"):
        match = re.search(pattern, stem, flags=re.IGNORECASE)
        if match:
            return int(match.group(1))
    return None


def _find_mode_model_files(decisions_dir: Path, mode: str, model: str) -> Dict[int, Path]:
    folder_name, prefix = MODE_SPECS[mode]
    folder = decisions_dir / folder_name
    if not folder.is_dir():
        return {}

    run_map: Dict[int, Path] = {}
    for path in sorted(folder.glob(f"{prefix}_{model}*.csv")):
        run_id = _extract_run_id(path, prefix, model)
        if run_id is not None:
            run_map.setdefault(run_id, path)
    return run_map


def _load_choice_rows(path: Path, mode: str, model: str, run_id: int) -> pd.DataFrame:
    df = pd.read_csv(path)
    if "idx" not in df.columns or "choice_value" not in df.columns:
        return pd.DataFrame(columns=["idx", "choice_value", "mode", "model", "run_id", "source_file"])

    out = df[["idx", "choice_value"]].copy()
    out["idx"] = pd.to_numeric(out["idx"], errors="coerce").astype("Int64")
    out["choice_value"] = pd.to_numeric(out["choice_value"], errors="coerce").astype("Int64")
    out["mode"] = mode
    out["model"] = model
    out["run_id"] = run_id
    out["source_file"] = str(path)
    out = out.dropna(subset=["idx"]).drop_duplicates(subset=["idx"], keep="first")
    return out


def load_master_three_runs(decisions_dir: Path, modes: Iterable[str] = MODES, models: Iterable[str] = MODEL_ORDER) -> pd.DataFrame:
    rows: List[pd.DataFrame] = []
    for mode, model in itertools.product(modes, models):
        run_map = _find_mode_model_files(decisions_dir, mode, model)
        for run_id in REQUIRED_RUNS:
            path = run_map.get(run_id)
            if path is not None:
                rows.append(_load_choice_rows(path, mode, model, run_id))

    if not rows:
        return pd.DataFrame(columns=["idx", "choice_value", "mode", "model", "run_id", "source_file"])
    out = pd.concat(rows, ignore_index=True)
    out["mode"] = out["mode"].astype(str)
    out["model"] = out["model"].astype(str)
    out["run_id"] = pd.to_numeric(out["run_id"], errors="coerce").astype("Int64")
    return out


def _pivot_mode_model_valid(df: pd.DataFrame, mode: str, model: str) -> pd.DataFrame:
    sub = df[(df["mode"] == mode) & (df["model"] == model)].copy()
    sub = sub[sub["choice_value"].isin(VALID_CHOICES)]
    if sub.empty:
        return pd.DataFrame()
    return sub.pivot_table(index="idx", columns="run_id", values="choice_value", aggfunc="first")


def standalone_consistency_equation(df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
    summary_rows: List[Dict[str, object]] = []
    case_rows: List[pd.DataFrame] = []

    for mode, model in itertools.product(MODES, MODEL_ORDER):
        pivot = _pivot_mode_model_valid(df, mode, model)
        available_runs = sorted([int(c) for c in pivot.columns.tolist()]) if not pivot.empty else []
        has_required = set(REQUIRED_RUNS).issubset(set(available_runs))

        if not has_required:
            summary_rows.append(
                {
                    "mode": mode,
                    "model": model,
                    "n_valid_items_C_mk": 0,
                    "n_consistent": 0,
                    "consistency_rate": pd.NA,
                    "required_runs": ",".join(str(r) for r in REQUIRED_RUNS),
                    "available_runs": ",".join(str(r) for r in available_runs),
                    "missing_required_runs": True,
                }
            )
            continue

        p = pivot[list(REQUIRED_RUNS)].dropna(how="any")
        if p.empty:
            summary_rows.append(
                {
                    "mode": mode,
                    "model": model,
                    "n_valid_items_C_mk": 0,
                    "n_consistent": 0,
                    "consistency_rate": pd.NA,
                    "required_runs": ",".join(str(r) for r in REQUIRED_RUNS),
                    "available_runs": ",".join(str(r) for r in available_runs),
                    "missing_required_runs": False,
                }
            )
            continue

        consistent_indicator = (p.nunique(axis=1) == 1).astype(int)
        total_valid = int(len(p))
        consistent_count = int(consistent_indicator.sum())
        consistency_rate = consistent_count / total_valid if total_valid else pd.NA

        c = p.reset_index().rename(columns={1: "run1_choice", 2: "run2_choice", 3: "run3_choice"})
        c["mode"] = mode
        c["model"] = model
        c["consistent_indicator"] = consistent_indicator.values
        c["is_consistent"] = c["consistent_indicator"] == 1
        c["consensus_choice"] = c["run1_choice"]
        case_rows.append(c)

        summary_rows.append(
            {
                "mode": mode,
                "model": model,
                "n_valid_items_C_mk": total_valid,
                "n_consistent": consistent_count,
                "consistency_rate": consistency_rate,
                "required_runs": ",".join(str(r) for r in REQUIRED_RUNS),
                "available_runs": ",".join(str(r) for r in available_runs),
                "missing_required_runs": False,
            }
        )

    summary = pd.DataFrame(summary_rows)
    cases = pd.concat(case_rows, ignore_index=True) if case_rows else pd.DataFrame()
    return summary, cases


def build_filtered_consensus(standalone_cases: pd.DataFrame) -> pd.DataFrame:
    if standalone_cases.empty:
        return pd.DataFrame(columns=["idx", "mode", "model", "consensus_choice"])
    out = standalone_cases[standalone_cases["is_consistent"]].copy()
    out = out[["idx", "mode", "model", "consensus_choice"]].drop_duplicates()
    out["idx"] = pd.to_numeric(out["idx"], errors="coerce").astype("Int64")
    out["consensus_choice"] = pd.to_numeric(out["consensus_choice"], errors="coerce").astype("Int64")
    return out


def write_united_files(filtered: pd.DataFrame, output_dir: Path) -> None:
    for mode in MODES:
        part = filtered[filtered["mode"] == mode].copy().sort_values(["idx", "model"])
        part.to_csv(output_dir / f"{MODE_SLUG[mode]}_united.csv", index=False)


def _pairwise_agreement_score(values: List[int]) -> float:
    n = len(values)
    if n < 2:
        return float("nan")
    total_pairs = n * (n - 1) // 2
    equal_pairs = 0
    for i in range(n):
        for j in range(i + 1, n):
            if values[i] == values[j]:
                equal_pairs += 1
    return equal_pairs / total_pairs


def item_agreement_scores(filtered: pd.DataFrame) -> pd.DataFrame:
    if filtered.empty:
        return pd.DataFrame(columns=["idx", "K", "agreement_score", "n_unique_choices", "full_coverage"])

    full_mode_model = [f"{m}|{md}" for m, md in itertools.product(MODES, MODEL_ORDER)]
    work = filtered.copy()
    work["mode_model"] = work["mode"] + "|" + work["model"]
    piv = work.pivot_table(index="idx", columns="mode_model", values="consensus_choice", aggfunc="first")
    piv = piv.reindex(columns=full_mode_model)

    rows: List[Dict[str, object]] = []
    for idx, row in piv.iterrows():
        vals = [int(v) for v in row.tolist() if pd.notna(v)]
        k = len(vals)
        if k < 2:
            continue
        rows.append(
            {
                "idx": int(idx),
                "K": k,
                "agreement_score": _pairwise_agreement_score(vals),
                "n_unique_choices": len(set(vals)),
                "full_coverage": k == len(full_mode_model),
            }
        )
    out = pd.DataFrame(rows)
    if not out.empty:
        out = out.sort_values(["agreement_score", "n_unique_choices", "idx"], ascending=[True, False, True]).reset_index(drop=True)
    return out


def build_cross_mode_pair_table(filtered: pd.DataFrame) -> pd.DataFrame:
    rows: List[Dict[str, object]] = []
    for model in MODEL_ORDER:
        sub = filtered[filtered["model"] == model]
        if sub.empty:
            continue
        pivot = sub.pivot_table(index="idx", columns="mode", values="consensus_choice", aggfunc="first")
        for left_mode, right_mode in itertools.combinations(MODES, 2):
            if left_mode not in pivot.columns or right_mode not in pivot.columns:
                continue
            pair = pivot[[left_mode, right_mode]].dropna(how="any")
            if pair.empty:
                continue
            agree = (pair[left_mode] == pair[right_mode]).astype(int)
            rows.append(
                {
                    "model": model,
                    "left_mode": left_mode,
                    "right_mode": right_mode,
                    "n_compared": int(len(pair)),
                    "n_agree": int(agree.sum()),
                    "agreement_rate": float(agree.mean()),
                }
            )
    return pd.DataFrame(rows)


def _heatmap_matrix_from_pair_rows(pair_rows: pd.DataFrame) -> pd.DataFrame:
    matrix = pd.DataFrame(index=MODES, columns=MODES, dtype=float)
    for mode in MODES:
        matrix.loc[mode, mode] = 1.0

    for _, row in pair_rows.iterrows():
        lmode = row["left_mode"]
        rmode = row["right_mode"]
        matrix.loc[lmode, rmode] = row["agreement_rate"]
        matrix.loc[rmode, lmode] = row["agreement_rate"]
    return matrix


def _draw_heatmap(ax: plt.Axes, matrix: pd.DataFrame, title: str) -> None:
    v = matrix.values.astype(float)
    im = ax.imshow(v, vmin=0.0, vmax=1.0, cmap="YlGnBu")
    ax.set_xticks(range(len(MODES)))
    ax.set_xticklabels(MODES, rotation=30, ha="right")
    ax.set_yticks(range(len(MODES)))
    ax.set_yticklabels(MODES)
    ax.set_title(title, fontsize=11)

    for i in range(v.shape[0]):
        for j in range(v.shape[1]):
            if math.isnan(v[i, j]):
                label = "NA"
            else:
                label = f"{100.0 * v[i, j]:.1f}%"
            ax.text(j, i, label, ha="center", va="center", fontsize=8, color="black")
    return im


def plot_cross_mode_heatmaps(pair_table: pd.DataFrame, output_dir: Path) -> None:
    if pair_table.empty:
        return

    # Aggregated heatmap weighted by number of compared items.
    agg_rows: List[Dict[str, object]] = []
    for left_mode, right_mode in itertools.combinations(MODES, 2):
        part = pair_table[(pair_table["left_mode"] == left_mode) & (pair_table["right_mode"] == right_mode)]
        if part.empty:
            continue
        n_compared = int(part["n_compared"].sum())
        n_agree = int(part["n_agree"].sum())
        agg_rows.append(
            {
                "left_mode": left_mode,
                "right_mode": right_mode,
                "agreement_rate": (n_agree / n_compared) if n_compared else float("nan"),
            }
        )
    agg_matrix = _heatmap_matrix_from_pair_rows(pd.DataFrame(agg_rows))

    fig, ax = plt.subplots(figsize=(7.2, 6.0))
    im = _draw_heatmap(ax, agg_matrix, "Figure 1A: Cross-Mode Agreement (All Models)")
    cbar = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    cbar.set_label("Agreement")
    fig.tight_layout()
    fig.savefig(output_dir / "figure1A_cross_mode_agreement_heatmap_overall.png", dpi=300)
    plt.close(fig)

    # Per-model 2x2 heatmaps.
    fig, axes = plt.subplots(2, 2, figsize=(12, 10))
    axes = axes.flatten()
    for ax, model in zip(axes, MODEL_ORDER):
        part = pair_table[pair_table["model"] == model][["left_mode", "right_mode", "agreement_rate"]].copy()
        matrix = _heatmap_matrix_from_pair_rows(part)
        _draw_heatmap(ax, matrix, f"Figure 1B: {model}")
    fig.tight_layout()
    fig.savefig(output_dir / "figure1B_cross_mode_agreement_heatmap_by_model.png", dpi=300)
    plt.close(fig)


def plot_standalone_bar_chart(standalone_summary: pd.DataFrame, output_dir: Path) -> None:
    valid = standalone_summary[~standalone_summary["missing_required_runs"]].copy()
    valid = valid.dropna(subset=["consistency_rate"])
    if valid.empty:
        return

    valid["condition"] = valid["mode"] + "-" + valid["model"]
    valid = valid.sort_values(["mode", "model"]).reset_index(drop=True)

    fig, ax = plt.subplots(figsize=(13, 6))
    bars = ax.bar(valid["condition"], valid["consistency_rate"], color="#4C78A8")
    ax.set_ylim(0, 1.0)
    ax.set_ylabel("Consistency Rate")
    ax.set_xlabel("Mode x Model")
    ax.set_title("Figure 2: Standalone Consistency by Mode x Model")
    ax.tick_params(axis="x", rotation=45)

    for bar, rate in zip(bars, valid["consistency_rate"]):
        ax.text(bar.get_x() + bar.get_width() / 2.0, bar.get_height() + 0.01, f"{100.0 * rate:.1f}%", ha="center", va="bottom", fontsize=8)

    fig.tight_layout()
    fig.savefig(output_dir / "figure2_standalone_consistency_bar_chart.png", dpi=300)
    plt.close(fig)


def _fmt_rate(value: object) -> str:
    if pd.isna(value):
        return "NA"
    return f"{float(value):.2%}"


def run_consistency_analysis(base_dir: Path, output_dir: Path) -> None:
    decisions_dir = base_dir / "decisions"
    output_dir.mkdir(parents=True, exist_ok=True)

    master = load_master_three_runs(decisions_dir)
    master.to_csv(output_dir / "consistency_master_three_runs.csv", index=False)

    standalone_summary, standalone_cases = standalone_consistency_equation(master)
    standalone_summary.to_csv(output_dir / "standalone_consistency_summary.csv", index=False)
    standalone_cases.to_csv(output_dir / "standalone_consistency_cases.csv", index=False)

    filtered = build_filtered_consensus(standalone_cases)
    filtered.to_csv(output_dir / "filtered_consensus_cases.csv", index=False)
    write_united_files(filtered, output_dir)

    agreement = item_agreement_scores(filtered)
    agreement.to_csv(output_dir / "item_agreement_scores.csv", index=False)

    if not agreement.empty:
        full_cov = agreement[agreement["full_coverage"]].copy()
        full_cov.to_csv(output_dir / "full_coverage_item_agreement_scores.csv", index=False)
        full_cov.head(10).to_csv(output_dir / "top10_least_consistent_cases.csv", index=False)
        full_cov.sort_values(["agreement_score", "n_unique_choices", "idx"], ascending=[False, True, True]).head(10).to_csv(
            output_dir / "top10_most_consistent_cases.csv", index=False
        )
        agreement[agreement["n_unique_choices"] == 1].to_csv(output_dir / "universally_consistent_across_all_modes_models.csv", index=False)

    pair_table = build_cross_mode_pair_table(filtered)
    pair_table.to_csv(output_dir / "cross_mode_agreement_by_model.csv", index=False)

    plot_cross_mode_heatmaps(pair_table, output_dir)
    plot_standalone_bar_chart(standalone_summary, output_dir)

    standalone_valid = standalone_summary[~standalone_summary["missing_required_runs"]].copy()
    standalone_total = int(standalone_valid["n_valid_items_C_mk"].sum()) if not standalone_valid.empty else 0
    standalone_consistent = int(standalone_valid["n_consistent"].sum()) if not standalone_valid.empty else 0
    standalone_rate = (standalone_consistent / standalone_total) if standalone_total else pd.NA

    print("\n=== Consistency Summary Report ===")
    print(f"Base directory: {base_dir}")
    print(f"Master rows loaded: {len(master):,}")
    print(f"Filtered consensus rows: {len(filtered):,}")
    print(f"Standalone consistency overall: {standalone_consistent:,}/{standalone_total:,} ({_fmt_rate(standalone_rate)})")
    print("Per mode-model consistency:")
    for mode, model in itertools.product(MODES, MODEL_ORDER):
        row = standalone_summary[(standalone_summary["mode"] == mode) & (standalone_summary["model"] == model)]
        if row.empty:
            continue
        r = row.iloc[0]
        if bool(r["missing_required_runs"]):
            print(f"- {mode} | {model}: missing required runs (available: {r['available_runs']})")
        else:
            print(
                f"- {mode} | {model}: {int(r['n_consistent']):,}/{int(r['n_valid_items_C_mk']):,}"
                f" ({_fmt_rate(r['consistency_rate'])})"
            )
    print(f"Saved outputs and figures to: {output_dir}")


def parse_args() -> argparse.Namespace:
    default_base_dir = Path(__file__).resolve().parents[2]
    default_output_dir = Path(__file__).resolve().parent

    parser = argparse.ArgumentParser(description="Equation-aligned consistency analysis + required figures.")
    parser.add_argument("--base-dir", type=Path, default=default_base_dir, help="Dataset root containing decisions/")
    parser.add_argument("--output-dir", type=Path, default=default_output_dir, help="Output folder for CSVs and figures")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_consistency_analysis(args.base_dir, args.output_dir)


if __name__ == "__main__":
    main()

