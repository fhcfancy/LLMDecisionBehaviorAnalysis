"""
Analyze swap-order counterfactual outputs for action-position bias.

This script computes:
1) Mode-model metrics (technical + behavioral):
   - coverage, effective, conditional_match
   - original/swapped action2 rates and delta
   - preservation/flip rates
2) Strict cross-mode fairness metrics per model:
   - strict_match_rate on all-modes-both-valid idx (same denominator)
3) Overall pooled metrics across selected datasets.

Usage:
    python analyze_swap_counterfactual.py V3
    python analyze_swap_counterfactual.py CN CT R1 V3
    python analyze_swap_counterfactual.py --modes EA EI Neutral "Neutral-CoT"
    python analyze_swap_counterfactual.py V3 --report-md DataAnalysis/Better/Analysis/action_tendency_experiment/results/swap_bias_report_v3.md
"""

from __future__ import annotations

import argparse
import csv
import os
from dataclasses import dataclass
from typing import Dict, List, Set, Tuple


DATASETS: Tuple[str, ...] = ("CN", "CT", "R1", "V3")
MODES: Tuple[str, ...] = ("EA", "EI", "Neutral", "Neutral-CoT")

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
BETTER_DIR = os.path.dirname(os.path.dirname(THIS_DIR))
DECISIONS_BASE = os.path.join(BETTER_DIR, "decisions")
SWAP_BASE = os.path.join(DECISIONS_BASE, "ActionBiasSwap")
OUTPUT_DIR = os.path.join(THIS_DIR, "results")


@dataclass
class RowEval:
    idx: int
    original_choice: int | None
    swapped_slot_choice: int | None
    swapped_canonical_choice: int | None

    @property
    def original_valid(self) -> bool:
        return self.original_choice in (1, 2)

    @property
    def swapped_valid(self) -> bool:
        return self.swapped_canonical_choice in (1, 2)

    @property
    def both_valid(self) -> bool:
        return self.original_valid and self.swapped_valid

    @property
    def preserved(self) -> bool:
        return self.both_valid and self.original_choice == self.swapped_canonical_choice

    @property
    def flipped(self) -> bool:
        return self.both_valid and self.original_choice != self.swapped_canonical_choice


def _int_choice(raw: object) -> int | None:
    try:
        c = int(str(raw).strip())
    except (TypeError, ValueError, AttributeError):
        return None
    return c if c in (1, 2) else None


def _pct(num: int, den: int) -> float:
    return (100.0 * num / den) if den else 0.0


def _original_path(mode: str, dataset: str) -> str:
    if mode == "EA":
        return os.path.join(DECISIONS_BASE, "EmotionalAnalytic", f"EA_{dataset}.csv")
    if mode == "EI":
        return os.path.join(DECISIONS_BASE, "EmotionalIntuitive", f"EI_{dataset}.csv")
    if mode == "Neutral":
        return os.path.join(DECISIONS_BASE, "Neutral", f"Neutral_{dataset}.csv")
    if mode == "Neutral-CoT":
        return os.path.join(DECISIONS_BASE, "Neutral-CoT", f"Neutral-CoT_{dataset}.csv")
    raise ValueError(f"Unsupported mode: {mode}")


def _swap_path(mode: str, dataset: str) -> str:
    return os.path.join(SWAP_BASE, mode, f"{mode}_{dataset}_swap.csv")


def _load_original_choice_map(path: str) -> Dict[int, int | None]:
    out: Dict[int, int | None] = {}
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                idx = int(str(row.get("idx", "")).strip())
            except (TypeError, ValueError):
                continue
            out[idx] = _int_choice(row.get("choice_value", ""))
    return out


def _load_swap_map(path: str) -> Dict[int, Tuple[int | None, int | None]]:
    # idx -> (swapped_slot_choice, swapped_canonical_choice)
    out: Dict[int, Tuple[int | None, int | None]] = {}
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                idx = int(str(row.get("idx", "")).strip())
            except (TypeError, ValueError):
                continue
            out[idx] = (
                _int_choice(row.get("swapped_slot_choice_value", "")),
                _int_choice(row.get("swapped_canonical_choice_value", "")),
            )
    return out


def _evaluate_mode_dataset(mode: str, dataset: str) -> Dict[int, RowEval]:
    original_path = _original_path(mode, dataset)
    swap_path = _swap_path(mode, dataset)
    if not os.path.isfile(original_path):
        raise FileNotFoundError(f"Missing original decisions: {original_path}")
    if not os.path.isfile(swap_path):
        raise FileNotFoundError(f"Missing swap outputs: {swap_path}")

    original = _load_original_choice_map(original_path)
    swapped = _load_swap_map(swap_path)

    evals: Dict[int, RowEval] = {}
    for idx, orig_choice in original.items():
        if idx not in swapped:
            continue
        swap_slot, swap_canonical = swapped[idx]
        evals[idx] = RowEval(
            idx=idx,
            original_choice=orig_choice,
            swapped_slot_choice=swap_slot,
            swapped_canonical_choice=swap_canonical,
        )
    return evals


def _summarize_mode_dataset(mode: str, dataset: str, evals: Dict[int, RowEval]) -> Dict[str, object]:
    rows = list(evals.values())
    n_pairs = len(rows)
    n_original_valid = sum(int(r.original_valid) for r in rows)
    n_swapped_valid = sum(int(r.swapped_valid) for r in rows)
    n_both_valid = sum(int(r.both_valid) for r in rows)
    n_preserved = sum(int(r.preserved) for r in rows)
    n_flipped = sum(int(r.flipped) for r in rows)

    # action2 tendency metrics
    n_original_a2 = sum(int(r.original_choice == 2) for r in rows if r.original_valid)
    n_swapped_canonical_a2 = sum(int(r.swapped_canonical_choice == 2) for r in rows if r.swapped_valid)
    n_second_presented = sum(int(r.original_choice == 2) for r in rows if r.both_valid) + sum(
        int(r.swapped_slot_choice == 2) for r in rows if r.both_valid
    )
    n_second_presented_den = 2 * n_both_valid

    coverage = _pct(n_both_valid, n_original_valid)
    effective = _pct(n_preserved, n_original_valid)
    conditional_match = _pct(n_preserved, n_both_valid)

    return {
        "dataset": dataset,
        "mode": mode,
        "n_pairs_with_swap_row": n_pairs,
        "n_original_valid": n_original_valid,
        "n_swapped_valid": n_swapped_valid,
        "n_both_valid": n_both_valid,
        "coverage": coverage,
        "n_preserved": n_preserved,
        "n_flipped": n_flipped,
        "effective": effective,
        "conditional_match": conditional_match,
        "flip_rate_conditional": _pct(n_flipped, n_both_valid),
        "original_action2_rate": _pct(n_original_a2, n_original_valid),
        "swapped_canonical_action2_rate": _pct(n_swapped_canonical_a2, n_swapped_valid),
        "action2_delta_original_minus_swapped_canonical": _pct(n_original_a2, n_original_valid)
        - _pct(n_swapped_canonical_a2, n_swapped_valid),
        "second_presented_choice_rate": _pct(n_second_presented, n_second_presented_den),
    }


def _strict_fairness_rows(
    dataset: str,
    mode_to_eval: Dict[str, Dict[int, RowEval]],
) -> List[Dict[str, object]]:
    mode_sets: Dict[str, Set[int]] = {
        mode: {idx for idx, r in evals.items() if r.both_valid}
        for mode, evals in mode_to_eval.items()
    }
    if not mode_sets:
        return []
    strict_idx = set.intersection(*mode_sets.values()) if mode_sets else set()
    strict_n = len(strict_idx)

    rows: List[Dict[str, object]] = []
    for mode, evals in mode_to_eval.items():
        preserved = sum(int(evals[idx].preserved) for idx in strict_idx)
        flips = sum(int(evals[idx].flipped) for idx in strict_idx)
        second_presented = sum(int(evals[idx].original_choice == 2) for idx in strict_idx) + sum(
            int(evals[idx].swapped_slot_choice == 2) for idx in strict_idx
        )
        rows.append(
            {
                "dataset": dataset,
                "mode": mode,
                "strict_n_all_modes_both_valid": strict_n,
                "strict_preserved_count": preserved,
                "strict_flipped_count": flips,
                "strict_match_rate": _pct(preserved, strict_n),
                "strict_flip_rate": _pct(flips, strict_n),
                "strict_second_presented_choice_rate": _pct(second_presented, 2 * strict_n),
            }
        )
    return rows


def _aggregate(rows: List[Dict[str, object]], keys: Tuple[str, ...], level_name: str) -> List[Dict[str, object]]:
    # Weighted aggregation by summing numerators/denominators.
    grouped: Dict[Tuple[str, ...], Dict[str, float]] = {}

    for r in rows:
        gk = tuple(str(r[k]) for k in keys)
        g = grouped.setdefault(
            gk,
            {
                "n_pairs_with_swap_row": 0.0,
                "n_original_valid": 0.0,
                "n_swapped_valid": 0.0,
                "n_both_valid": 0.0,
                "n_preserved": 0.0,
                "n_flipped": 0.0,
                "n_original_a2_num": 0.0,
                "n_swapped_a2_num": 0.0,
                "n_second_presented_num": 0.0,
            },
        )
        g["n_pairs_with_swap_row"] += float(r["n_pairs_with_swap_row"])
        g["n_original_valid"] += float(r["n_original_valid"])
        g["n_swapped_valid"] += float(r["n_swapped_valid"])
        g["n_both_valid"] += float(r["n_both_valid"])
        g["n_preserved"] += float(r["n_preserved"])
        g["n_flipped"] += float(r["n_flipped"])
        g["n_original_a2_num"] += float(r["original_action2_rate"]) * float(r["n_original_valid"]) / 100.0
        g["n_swapped_a2_num"] += float(r["swapped_canonical_action2_rate"]) * float(r["n_swapped_valid"]) / 100.0
        g["n_second_presented_num"] += (
            float(r["second_presented_choice_rate"]) * (2.0 * float(r["n_both_valid"])) / 100.0
        )

    out: List[Dict[str, object]] = []
    for gk, g in grouped.items():
        n_original_valid = int(g["n_original_valid"])
        n_swapped_valid = int(g["n_swapped_valid"])
        n_both_valid = int(g["n_both_valid"])
        n_preserved = int(g["n_preserved"])
        n_flipped = int(g["n_flipped"])
        original_a2_rate = _pct(int(round(g["n_original_a2_num"])), n_original_valid)
        swapped_a2_rate = _pct(int(round(g["n_swapped_a2_num"])), n_swapped_valid)
        out_row = {keys[i]: gk[i] for i in range(len(keys))}
        out_row.update(
            {
                "level": level_name,
                "n_pairs_with_swap_row": int(g["n_pairs_with_swap_row"]),
                "n_original_valid": n_original_valid,
                "n_swapped_valid": n_swapped_valid,
                "n_both_valid": n_both_valid,
                "coverage": _pct(n_both_valid, n_original_valid),
                "n_preserved": n_preserved,
                "n_flipped": n_flipped,
                "effective": _pct(n_preserved, n_original_valid),
                "conditional_match": _pct(n_preserved, n_both_valid),
                "flip_rate_conditional": _pct(n_flipped, n_both_valid),
                "original_action2_rate": original_a2_rate,
                "swapped_canonical_action2_rate": swapped_a2_rate,
                "action2_delta_original_minus_swapped_canonical": original_a2_rate - swapped_a2_rate,
                "second_presented_choice_rate": _pct(int(round(g["n_second_presented_num"])), 2 * n_both_valid),
            }
        )
        out.append(out_row)
    return out


def _aggregate_strict(rows: List[Dict[str, object]], key: str) -> List[Dict[str, object]]:
    grouped: Dict[str, Dict[str, int]] = {}
    for r in rows:
        g = grouped.setdefault(
            str(r[key]),
            {
                "strict_n_all_modes_both_valid": 0,
                "strict_preserved_count": 0,
                "strict_flipped_count": 0,
                "strict_second_presented_num": 0,
            },
        )
        n = int(r["strict_n_all_modes_both_valid"])
        g["strict_n_all_modes_both_valid"] += n
        g["strict_preserved_count"] += int(r["strict_preserved_count"])
        g["strict_flipped_count"] += int(r["strict_flipped_count"])
        g["strict_second_presented_num"] += int(round(float(r["strict_second_presented_choice_rate"]) * (2 * n) / 100.0))

    out = []
    for group_val, g in grouped.items():
        n = g["strict_n_all_modes_both_valid"]
        out.append(
            {
                key: group_val,
                "level": f"overall_by_{key}",
                "strict_n_all_modes_both_valid": n,
                "strict_preserved_count": g["strict_preserved_count"],
                "strict_flipped_count": g["strict_flipped_count"],
                "strict_match_rate": _pct(g["strict_preserved_count"], n),
                "strict_flip_rate": _pct(g["strict_flipped_count"], n),
                "strict_second_presented_choice_rate": _pct(g["strict_second_presented_num"], 2 * n),
            }
        )
    return out


def _write_csv(path: str, rows: List[Dict[str, object]], fieldnames: List[str]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)


def _fmt_pct(v: object) -> str:
    try:
        return f"{float(v):.2f}%"
    except (TypeError, ValueError):
        return "NA"


def _leader(rows: List[Dict[str, object]], metric: str, label_key: str = "mode") -> str:
    if not rows:
        return "N/A"
    ordered = sorted(rows, key=lambda x: float(x.get(metric, 0.0)), reverse=True)
    top = ordered[0]
    return f"{top.get(label_key, 'N/A')} ({_fmt_pct(top.get(metric, 0.0))})"


def _render_markdown_report(
    selected_datasets: Tuple[str, ...],
    selected_modes: Tuple[str, ...],
    mode_dataset_rows: List[Dict[str, object]],
    overall_by_mode: List[Dict[str, object]],
    strict_rows: List[Dict[str, object]],
    strict_overall_by_mode: List[Dict[str, object]],
) -> str:
    lines: List[str] = []
    lines.append("# Swap-Order Counterfactual Bias Report")
    lines.append("")
    lines.append("## Scope")
    lines.append(f"- Datasets: {', '.join(selected_datasets)}")
    lines.append(f"- Modes: {', '.join(selected_modes)}")
    lines.append("")
    lines.append("## Metric definitions")
    lines.append("- `coverage`: both-valid pair rate among original-valid rows.")
    lines.append("- `effective`: preserved-canonical-choice rate among original-valid rows.")
    lines.append("- `conditional_match`: preserved-canonical-choice rate among both-valid rows.")
    lines.append("- `strict_match_rate`: preserved-canonical-choice rate on all-modes-both-valid intersection.")
    lines.append("- `action2_delta_original_minus_swapped_canonical`: positive means action2 tendency decreases after de-slotting.")
    lines.append("")

    for ds in selected_datasets:
        rows = [r for r in mode_dataset_rows if str(r.get("dataset")) == ds]
        strict_ds = [r for r in strict_rows if str(r.get("dataset")) == ds]
        if not rows:
            continue

        lines.append(f"## Dataset `{ds}`")
        lines.append("")
        lines.append("| Mode | OrigValid | BothValid | Coverage | Effective | Conditional | FlipRate | Orig A2 | Swap Canonical A2 | A2 Delta |")
        lines.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
        for r in rows:
            lines.append(
                f"| {r.get('mode')} | {int(r.get('n_original_valid', 0))} | {int(r.get('n_both_valid', 0))} | "
                f"{_fmt_pct(r.get('coverage', 0.0))} | {_fmt_pct(r.get('effective', 0.0))} | "
                f"{_fmt_pct(r.get('conditional_match', 0.0))} | {_fmt_pct(r.get('flip_rate_conditional', 0.0))} | "
                f"{_fmt_pct(r.get('original_action2_rate', 0.0))} | {_fmt_pct(r.get('swapped_canonical_action2_rate', 0.0))} | "
                f"{_fmt_pct(r.get('action2_delta_original_minus_swapped_canonical', 0.0))} |"
            )
        lines.append("")
        lines.append("**Leaders (dataset-level)**")
        lines.append(f"- Coverage: {_leader(rows, 'coverage')}")
        lines.append(f"- Effective: {_leader(rows, 'effective')}")
        lines.append(f"- Conditional match: {_leader(rows, 'conditional_match')}")
        lines.append(f"- Largest positive A2 delta: {_leader(rows, 'action2_delta_original_minus_swapped_canonical')}")
        if strict_ds:
            lines.append(f"- Strict fairness (same denominator): {_leader(strict_ds, 'strict_match_rate')}")
        lines.append("")

    lines.append("## Overall pooled by mode")
    lines.append("")
    lines.append("| Mode | Coverage | Effective | Conditional | FlipRate | Orig A2 | Swap Canonical A2 | A2 Delta |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|")
    for r in overall_by_mode:
        lines.append(
            f"| {r.get('mode')} | {_fmt_pct(r.get('coverage', 0.0))} | {_fmt_pct(r.get('effective', 0.0))} | "
            f"{_fmt_pct(r.get('conditional_match', 0.0))} | {_fmt_pct(r.get('flip_rate_conditional', 0.0))} | "
            f"{_fmt_pct(r.get('original_action2_rate', 0.0))} | {_fmt_pct(r.get('swapped_canonical_action2_rate', 0.0))} | "
            f"{_fmt_pct(r.get('action2_delta_original_minus_swapped_canonical', 0.0))} |"
        )
    lines.append("")
    lines.append("**Overall leaders**")
    lines.append(f"- Coverage: {_leader(overall_by_mode, 'coverage')}")
    lines.append(f"- Effective: {_leader(overall_by_mode, 'effective')}")
    lines.append(f"- Conditional match: {_leader(overall_by_mode, 'conditional_match')}")
    lines.append(f"- Largest positive A2 delta: {_leader(overall_by_mode, 'action2_delta_original_minus_swapped_canonical')}")
    if strict_overall_by_mode:
        lines.append(f"- Strict fairness (same denominator): {_leader(strict_overall_by_mode, 'strict_match_rate')}")
    lines.append("")
    lines.append("## Interpretation note")
    lines.append("- If a mode shows high positive `A2 Delta`, its original action2 preference is likely inflated by slot position.")
    lines.append("- If `A2 Delta` is near zero, action2 tendency is likely content-driven rather than slot-driven.")
    lines.append("- Always read `effective` together with `coverage` to separate technical failure effects from behavioral effects.")
    lines.append("")
    return "\n".join(lines)


def _write_text(path: str, content: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze swap-order counterfactual bias metrics.")
    parser.add_argument("datasets", nargs="*", choices=list(DATASETS), help="Datasets to analyze. Default: all.")
    parser.add_argument(
        "--modes",
        nargs="+",
        default=list(MODES),
        choices=list(MODES),
        help="Modes to include. Default: EA EI Neutral Neutral-CoT",
    )
    parser.add_argument(
        "--report-md",
        default="",
        help="Optional markdown report path.",
    )
    args = parser.parse_args()

    selected_datasets = tuple(args.datasets) if args.datasets else DATASETS
    selected_modes = tuple(args.modes)
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    mode_dataset_rows: List[Dict[str, object]] = []
    strict_rows: List[Dict[str, object]] = []

    for ds in selected_datasets:
        mode_to_eval: Dict[str, Dict[int, RowEval]] = {}
        for mode in selected_modes:
            evals = _evaluate_mode_dataset(mode, ds)
            mode_to_eval[mode] = evals
            mode_dataset_rows.append(_summarize_mode_dataset(mode, ds, evals))
        strict_rows.extend(_strict_fairness_rows(ds, mode_to_eval))

    overall_by_mode = _aggregate(mode_dataset_rows, ("mode",), "overall_by_mode")
    overall_by_dataset = _aggregate(mode_dataset_rows, ("dataset",), "overall_by_dataset")
    strict_overall_by_mode = _aggregate_strict(strict_rows, "mode")

    detailed_path = os.path.join(OUTPUT_DIR, "swap_bias_mode_dataset_metrics.csv")
    overall_mode_path = os.path.join(OUTPUT_DIR, "swap_bias_overall_by_mode.csv")
    overall_dataset_path = os.path.join(OUTPUT_DIR, "swap_bias_overall_by_dataset.csv")
    strict_path = os.path.join(OUTPUT_DIR, "swap_bias_strict_mode_dataset.csv")
    strict_overall_path = os.path.join(OUTPUT_DIR, "swap_bias_strict_overall_by_mode.csv")

    metric_fields = [
        "dataset",
        "mode",
        "n_pairs_with_swap_row",
        "n_original_valid",
        "n_swapped_valid",
        "n_both_valid",
        "coverage",
        "n_preserved",
        "n_flipped",
        "effective",
        "conditional_match",
        "flip_rate_conditional",
        "original_action2_rate",
        "swapped_canonical_action2_rate",
        "action2_delta_original_minus_swapped_canonical",
        "second_presented_choice_rate",
    ]
    _write_csv(detailed_path, mode_dataset_rows, metric_fields)

    overall_fields = ["level", "mode"] + [f for f in metric_fields if f not in ("dataset", "mode")]
    _write_csv(overall_mode_path, overall_by_mode, overall_fields)

    overall_ds_fields = ["level", "dataset"] + [f for f in metric_fields if f not in ("dataset", "mode")]
    _write_csv(overall_dataset_path, overall_by_dataset, overall_ds_fields)

    strict_fields = [
        "dataset",
        "mode",
        "strict_n_all_modes_both_valid",
        "strict_preserved_count",
        "strict_flipped_count",
        "strict_match_rate",
        "strict_flip_rate",
        "strict_second_presented_choice_rate",
    ]
    _write_csv(strict_path, strict_rows, strict_fields)
    _write_csv(strict_overall_path, strict_overall_by_mode, ["level", "mode"] + strict_fields[2:])

    if args.report_md:
        report = _render_markdown_report(
            selected_datasets,
            selected_modes,
            mode_dataset_rows,
            overall_by_mode,
            strict_rows,
            strict_overall_by_mode,
        )
        _write_text(args.report_md, report)

    print(f"Saved: {detailed_path}")
    print(f"Saved: {overall_mode_path}")
    print(f"Saved: {overall_dataset_path}")
    print(f"Saved: {strict_path}")
    print(f"Saved: {strict_overall_path}")
    if args.report_md:
        print(f"Saved: {args.report_md}")


if __name__ == "__main__":
    main()
