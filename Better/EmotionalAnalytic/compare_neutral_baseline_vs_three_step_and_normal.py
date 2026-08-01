"""
Compare alignment to Neutral baseline (run 1 only):
1) Neutral baseline vs three-step CoT (EA run1)
2) Neutral baseline vs normal CoT (from cot_prompt_normal_only_*)
3) Difference between (1) and (2)

This script does NOT call any model APIs. It only reads existing CSV files.

Default inputs:
- Neutral baseline: decisions/Neutral/Neutral_<DATASET>_1.csv
- Three-step CoT  : decisions/EmotionalAnalytic/EA_<DATASET>_1.csv
- Normal CoT      : decisions/EmotionalAnalytic/experiments/cot_prompt_normal_only_<DATASET>.csv
"""

from __future__ import annotations

import argparse
import csv
import os
from dataclasses import dataclass
from typing import Dict, Iterable, List, Sequence, Tuple


DATASETS: Tuple[str, ...] = ("CN", "CT", "R1", "V3")


@dataclass
class DatasetMetrics:
    dataset: str
    n_baseline_valid: int
    n_all3_valid: int
    n_three_valid_vs_baseline: int
    n_normal_valid_vs_baseline: int
    n_three_match_vs_baseline: int
    n_normal_match_vs_baseline: int
    n_three_strict_match_all3: int
    n_normal_strict_match_all3: int
    three_effective_pct: float
    normal_effective_pct: float
    delta_effective_pct_three_minus_normal: float
    three_conditional_pct: float
    normal_conditional_pct: float
    delta_conditional_pct_three_minus_normal: float
    three_strict_all3_pct: float
    normal_strict_all3_pct: float
    delta_strict_all3_pct_three_minus_normal: float


def _pct(num: int, den: int) -> float:
    return (100.0 * num / den) if den else 0.0


def _safe_int(raw: object) -> int | None:
    try:
        return int(str(raw).strip())
    except (TypeError, ValueError, AttributeError):
        return None


def _safe_choice(raw: object) -> int | None:
    value = _safe_int(raw)
    if value in (1, 2):
        return value
    return None


def _load_choice_map(csv_path: str, choice_col: str) -> Dict[int, int]:
    """
    Load idx -> choice_value map using only valid choices {1,2}.
    If duplicate idx appears, later row overwrites earlier row.
    """
    out: Dict[int, int] = {}
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            idx = _safe_int(row.get("idx", ""))
            if idx is None or idx < 0:
                continue
            choice = _safe_choice(row.get(choice_col, ""))
            if choice is None:
                continue
            out[idx] = choice
    return out


def _load_dataset_maps(
    neutral_path: str,
    three_step_path: str,
    normal_path: str,
) -> Tuple[Dict[int, int], Dict[int, int], Dict[int, int]]:
    baseline = _load_choice_map(neutral_path, "choice_value")
    three_step = _load_choice_map(three_step_path, "choice_value")
    normal = _load_choice_map(normal_path, "normal_cot_choice_value")
    return baseline, three_step, normal


def _compute_dataset_metrics(
    dataset: str,
    neutral_path: str,
    three_step_path: str,
    normal_path: str,
) -> DatasetMetrics:
    baseline, three_step, normal = _load_dataset_maps(neutral_path, three_step_path, normal_path)

    base_idx = set(baseline.keys())
    three_idx = set(three_step.keys())
    normal_idx = set(normal.keys())

    all3_valid_idx = base_idx & three_idx & normal_idx
    three_valid_vs_base = base_idx & three_idx
    normal_valid_vs_base = base_idx & normal_idx

    n_baseline_valid = len(base_idx)
    n_all3_valid = len(all3_valid_idx)
    n_three_valid_vs_base = len(three_valid_vs_base)
    n_normal_valid_vs_base = len(normal_valid_vs_base)

    n_three_match_vs_base = sum(1 for idx in three_valid_vs_base if three_step[idx] == baseline[idx])
    n_normal_match_vs_base = sum(1 for idx in normal_valid_vs_base if normal[idx] == baseline[idx])

    n_three_strict_all3 = sum(1 for idx in all3_valid_idx if three_step[idx] == baseline[idx])
    n_normal_strict_all3 = sum(1 for idx in all3_valid_idx if normal[idx] == baseline[idx])

    three_effective = _pct(n_three_match_vs_base, n_baseline_valid)
    normal_effective = _pct(n_normal_match_vs_base, n_baseline_valid)
    three_conditional = _pct(n_three_match_vs_base, n_three_valid_vs_base)
    normal_conditional = _pct(n_normal_match_vs_base, n_normal_valid_vs_base)
    three_strict_all3 = _pct(n_three_strict_all3, n_all3_valid)
    normal_strict_all3 = _pct(n_normal_strict_all3, n_all3_valid)

    return DatasetMetrics(
        dataset=dataset,
        n_baseline_valid=n_baseline_valid,
        n_all3_valid=n_all3_valid,
        n_three_valid_vs_baseline=n_three_valid_vs_base,
        n_normal_valid_vs_baseline=n_normal_valid_vs_base,
        n_three_match_vs_baseline=n_three_match_vs_base,
        n_normal_match_vs_baseline=n_normal_match_vs_base,
        n_three_strict_match_all3=n_three_strict_all3,
        n_normal_strict_match_all3=n_normal_strict_all3,
        three_effective_pct=three_effective,
        normal_effective_pct=normal_effective,
        delta_effective_pct_three_minus_normal=three_effective - normal_effective,
        three_conditional_pct=three_conditional,
        normal_conditional_pct=normal_conditional,
        delta_conditional_pct_three_minus_normal=three_conditional - normal_conditional,
        three_strict_all3_pct=three_strict_all3,
        normal_strict_all3_pct=normal_strict_all3,
        delta_strict_all3_pct_three_minus_normal=three_strict_all3 - normal_strict_all3,
    )


def _build_disagreement_rows(
    dataset: str,
    baseline: Dict[int, int],
    three_step: Dict[int, int],
    normal: Dict[int, int],
) -> List[Dict[str, object]]:
    """
    Build row-level cases where three-step and normal differ in alignment outcome
    against baseline (one matches baseline while the other does not).
    """
    rows: List[Dict[str, object]] = []
    all3_valid_idx = sorted(set(baseline.keys()) & set(three_step.keys()) & set(normal.keys()))
    for idx in all3_valid_idx:
        b = baseline[idx]
        t = three_step[idx]
        n = normal[idx]
        t_match = int(t == b)
        n_match = int(n == b)
        if t_match == n_match:
            continue
        if t_match == 1:
            disagreement_type = "three_step_matches_baseline_normal_does_not"
        else:
            disagreement_type = "normal_matches_baseline_three_step_does_not"
        rows.append(
            {
                "dataset": dataset,
                "idx": idx,
                "baseline_choice_value": b,
                "three_step_choice_value": t,
                "normal_cot_choice_value": n,
                "three_step_matches_baseline": t_match,
                "normal_cot_matches_baseline": n_match,
                "three_vs_normal_choice_different": int(t != n),
                "disagreement_type": disagreement_type,
            }
        )
    return rows


def _aggregate_overall(rows: Iterable[DatasetMetrics]) -> DatasetMetrics:
    rows_list = list(rows)
    base = sum(r.n_baseline_valid for r in rows_list)
    all3 = sum(r.n_all3_valid for r in rows_list)
    three_valid = sum(r.n_three_valid_vs_baseline for r in rows_list)
    normal_valid = sum(r.n_normal_valid_vs_baseline for r in rows_list)
    three_match = sum(r.n_three_match_vs_baseline for r in rows_list)
    normal_match = sum(r.n_normal_match_vs_baseline for r in rows_list)
    three_strict = sum(r.n_three_strict_match_all3 for r in rows_list)
    normal_strict = sum(r.n_normal_strict_match_all3 for r in rows_list)

    three_effective = _pct(three_match, base)
    normal_effective = _pct(normal_match, base)
    three_conditional = _pct(three_match, three_valid)
    normal_conditional = _pct(normal_match, normal_valid)
    three_strict_pct = _pct(three_strict, all3)
    normal_strict_pct = _pct(normal_strict, all3)

    return DatasetMetrics(
        dataset="OVERALL",
        n_baseline_valid=base,
        n_all3_valid=all3,
        n_three_valid_vs_baseline=three_valid,
        n_normal_valid_vs_baseline=normal_valid,
        n_three_match_vs_baseline=three_match,
        n_normal_match_vs_baseline=normal_match,
        n_three_strict_match_all3=three_strict,
        n_normal_strict_match_all3=normal_strict,
        three_effective_pct=three_effective,
        normal_effective_pct=normal_effective,
        delta_effective_pct_three_minus_normal=three_effective - normal_effective,
        three_conditional_pct=three_conditional,
        normal_conditional_pct=normal_conditional,
        delta_conditional_pct_three_minus_normal=three_conditional - normal_conditional,
        three_strict_all3_pct=three_strict_pct,
        normal_strict_all3_pct=normal_strict_pct,
        delta_strict_all3_pct_three_minus_normal=three_strict_pct - normal_strict_pct,
    )


def _ensure_file(path: str, label: str) -> None:
    if not os.path.isfile(path):
        raise FileNotFoundError(f"Missing {label}: {path}")


def _metrics_fieldnames() -> List[str]:
    return [
        "dataset",
        "n_baseline_valid",
        "n_all3_valid",
        "n_three_valid_vs_baseline",
        "n_normal_valid_vs_baseline",
        "n_three_match_vs_baseline",
        "n_normal_match_vs_baseline",
        "n_three_strict_match_all3",
        "n_normal_strict_match_all3",
        "three_effective_pct",
        "normal_effective_pct",
        "delta_effective_pct_three_minus_normal",
        "three_conditional_pct",
        "normal_conditional_pct",
        "delta_conditional_pct_three_minus_normal",
        "three_strict_all3_pct",
        "normal_strict_all3_pct",
        "delta_strict_all3_pct_three_minus_normal",
    ]


def _write_metrics_csv(path: str, rows: Sequence[DatasetMetrics]) -> None:
    out_dir = os.path.dirname(os.path.abspath(path))
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    fields = _metrics_fieldnames()
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for r in rows:
            writer.writerow(
                {
                    "dataset": r.dataset,
                    "n_baseline_valid": r.n_baseline_valid,
                    "n_all3_valid": r.n_all3_valid,
                    "n_three_valid_vs_baseline": r.n_three_valid_vs_baseline,
                    "n_normal_valid_vs_baseline": r.n_normal_valid_vs_baseline,
                    "n_three_match_vs_baseline": r.n_three_match_vs_baseline,
                    "n_normal_match_vs_baseline": r.n_normal_match_vs_baseline,
                    "n_three_strict_match_all3": r.n_three_strict_match_all3,
                    "n_normal_strict_match_all3": r.n_normal_strict_match_all3,
                    "three_effective_pct": f"{r.three_effective_pct:.6f}",
                    "normal_effective_pct": f"{r.normal_effective_pct:.6f}",
                    "delta_effective_pct_three_minus_normal": f"{r.delta_effective_pct_three_minus_normal:.6f}",
                    "three_conditional_pct": f"{r.three_conditional_pct:.6f}",
                    "normal_conditional_pct": f"{r.normal_conditional_pct:.6f}",
                    "delta_conditional_pct_three_minus_normal": f"{r.delta_conditional_pct_three_minus_normal:.6f}",
                    "three_strict_all3_pct": f"{r.three_strict_all3_pct:.6f}",
                    "normal_strict_all3_pct": f"{r.normal_strict_all3_pct:.6f}",
                    "delta_strict_all3_pct_three_minus_normal": f"{r.delta_strict_all3_pct_three_minus_normal:.6f}",
                }
            )


def _disagreement_fieldnames() -> List[str]:
    return [
        "dataset",
        "idx",
        "baseline_choice_value",
        "three_step_choice_value",
        "normal_cot_choice_value",
        "three_step_matches_baseline",
        "normal_cot_matches_baseline",
        "three_vs_normal_choice_different",
        "disagreement_type",
    ]


def _write_disagreement_csv(path: str, rows: Sequence[Dict[str, object]]) -> None:
    out_dir = os.path.dirname(os.path.abspath(path))
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=_disagreement_fieldnames())
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _print_table(rows: Sequence[DatasetMetrics]) -> None:
    print("\n" + "=" * 130)
    print("Neutral baseline alignment comparison (run 1)")
    print("=" * 130)
    print(
        "Dataset | BaseN | All3N | ThreeValid | NormValid | ThreeEff | NormEff | dEff(3-N) | "
        "ThreeCond | NormCond | dCond(3-N) | ThreeStrict | NormStrict | dStrict(3-N)"
    )
    print("-" * 130)
    for r in rows:
        print(
            f"{r.dataset:>7} | "
            f"{r.n_baseline_valid:>5} | "
            f"{r.n_all3_valid:>5} | "
            f"{r.n_three_valid_vs_baseline:>10} | "
            f"{r.n_normal_valid_vs_baseline:>9} | "
            f"{r.three_effective_pct:>7.2f}% | "
            f"{r.normal_effective_pct:>7.2f}% | "
            f"{r.delta_effective_pct_three_minus_normal:>8.2f}% | "
            f"{r.three_conditional_pct:>9.2f}% | "
            f"{r.normal_conditional_pct:>8.2f}% | "
            f"{r.delta_conditional_pct_three_minus_normal:>9.2f}% | "
            f"{r.three_strict_all3_pct:>10.2f}% | "
            f"{r.normal_strict_all3_pct:>10.2f}% | "
            f"{r.delta_strict_all3_pct_three_minus_normal:>11.2f}%"
        )
    print("=" * 130)


def _default_paths(script_dir: str) -> Tuple[str, str, str]:
    better_dir = os.path.dirname(script_dir)
    decisions_dir = os.path.join(better_dir, "decisions")
    default_metrics_out = os.path.join(
        decisions_dir,
        "EmotionalAnalytic",
        "experiments",
        "neutral_alignment_run1_three_vs_normal.csv",
    )
    default_disagreement_out = os.path.join(
        decisions_dir,
        "EmotionalAnalytic",
        "experiments",
        "neutral_alignment_run1_three_vs_normal_disagreements.csv",
    )
    return decisions_dir, default_metrics_out, default_disagreement_out


def main() -> None:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    default_decisions_dir, default_output_csv, default_disagreement_output_csv = _default_paths(script_dir)

    parser = argparse.ArgumentParser(
        description=(
            "Compare run1 alignment to Neutral baseline between three-step CoT and normal CoT "
            "for datasets CN/CT/R1/V3."
        )
    )
    parser.add_argument(
        "datasets",
        nargs="*",
        choices=list(DATASETS),
        help="Datasets to include. Default: all (CN CT R1 V3).",
    )
    parser.add_argument(
        "--decisions-dir",
        default=default_decisions_dir,
        help=f"Base decisions directory (default: {default_decisions_dir})",
    )
    parser.add_argument(
        "--output-csv",
        default=default_output_csv,
        help=f"Output CSV path (default: {default_output_csv})",
    )
    parser.add_argument(
        "--disagreement-output-csv",
        default=default_disagreement_output_csv,
        help=f"Disagreement CSV path (default: {default_disagreement_output_csv})",
    )
    args = parser.parse_args()

    selected = tuple(args.datasets) if args.datasets else DATASETS

    dataset_rows: List[DatasetMetrics] = []
    disagreement_rows: List[Dict[str, object]] = []
    for ds in selected:
        neutral_path = os.path.join(args.decisions_dir, "Neutral", f"Neutral_{ds}_1.csv")
        three_step_path = os.path.join(args.decisions_dir, "EmotionalAnalytic", f"EA_{ds}_1.csv")
        normal_path = os.path.join(
            args.decisions_dir,
            "EmotionalAnalytic",
            "experiments",
            f"cot_prompt_normal_only_{ds}.csv",
        )

        _ensure_file(neutral_path, f"Neutral baseline run1 for {ds}")
        _ensure_file(three_step_path, f"three-step EA run1 for {ds}")
        _ensure_file(normal_path, f"normal CoT cache for {ds}")

        baseline, three_step, normal = _load_dataset_maps(neutral_path, three_step_path, normal_path)
        dataset_rows.append(
            _compute_dataset_metrics(
                dataset=ds,
                neutral_path=neutral_path,
                three_step_path=three_step_path,
                normal_path=normal_path,
            )
        )
        disagreement_rows.extend(_build_disagreement_rows(ds, baseline, three_step, normal))

    overall = _aggregate_overall(dataset_rows)
    all_rows = dataset_rows + [overall]

    _print_table(all_rows)
    _write_metrics_csv(args.output_csv, all_rows)
    _write_disagreement_csv(args.disagreement_output_csv, disagreement_rows)
    print(f"\nSaved metrics CSV: {args.output_csv}")
    print(f"Saved disagreement CSV: {args.disagreement_output_csv} (rows={len(disagreement_rows)})")


if __name__ == "__main__":
    main()
