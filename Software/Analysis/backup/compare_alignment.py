"""
Compare alignment to Neutral reference across 4 models and 4 modes.

Modes:
- Neutral (reference)
- Neutral-CoT
- EmotionalIntuitive (EI)
- EmotionalAnalytic (EA)

Metrics per method (vs Neutral):
1) strict_match_rate   : match rate on identical all-4-valid idx set (fair denominator)
2) coverage            : valid-output coverage vs Neutral-valid idx
3) effective           : end-to-end match rate vs Neutral-valid idx
4) conditional_match   : effective / coverage (behavior after technical failures removed)

Usage:
    # all models
    python compare_alignment_4mode.py

    # selected models
    python compare_alignment_4mode.py CN V3

    # optional CSV exports
    python compare_alignment_4mode.py --output-csv per_model_metrics.csv --overall-output-csv overall_metrics.csv

    # optional publication-ready markdown report
    python compare_alignment_4mode.py --report-md alignment_report.md
"""

from __future__ import annotations

import argparse
import csv
import os
from dataclasses import dataclass
from typing import Dict, Iterable, List, Tuple


MODEL_CODES: Tuple[str, ...] = ("CN", "CT", "R1", "V3")
METHODS: Tuple[str, ...] = ("EA", "EI", "Neutral-CoT")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BETTER_DIR = os.path.dirname(SCRIPT_DIR)
DEFAULT_DECISIONS_DIR = os.path.join(BETTER_DIR, "decisions")


@dataclass
class MethodMetrics:
    model: str
    method: str
    n_ref_valid: int
    n_all4_valid: int
    n_method_valid_vs_ref: int
    n_strict_match: int
    n_effective_match: int
    strict_match_rate: float
    coverage: float
    effective: float
    conditional_match: float


def _pct(numerator: int, denominator: int) -> float:
    if denominator == 0:
        return 0.0
    return 100.0 * numerator / denominator


def _safe_choice_value(raw_value: object) -> int | None:
    """Return 1 or 2 when valid; otherwise None."""
    try:
        value = int(str(raw_value).strip())
    except (TypeError, ValueError):
        return None
    return value if value in (1, 2) else None


def _load_choice_map(csv_path: str) -> Dict[int, int]:
    """Load idx -> choice_value for valid choices only (1/2)."""
    idx_to_choice: Dict[int, int] = {}
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                idx = int(str(row.get("idx", "")).strip())
            except (TypeError, ValueError):
                continue
            choice = _safe_choice_value(row.get("choice_value", ""))
            if choice is None:
                continue
            idx_to_choice[idx] = choice
    return idx_to_choice


def _file_paths_for_model(decisions_dir: str, model: str) -> Dict[str, str]:
    return {
        "Neutral": os.path.join(decisions_dir, "Neutral", f"Neutral_{model}.csv"),
        "Neutral-CoT": os.path.join(decisions_dir, "Neutral-CoT", f"Neutral-CoT_{model}.csv"),
        "EI": os.path.join(decisions_dir, "EmotionalIntuitive", f"EI_{model}.csv"),
        "EA": os.path.join(decisions_dir, "EmotionalAnalytic", f"EA_{model}.csv"),
    }


def _require_paths(paths: Dict[str, str], model: str) -> None:
    missing = [f"{name}: {path}" for name, path in paths.items() if not os.path.isfile(path)]
    if missing:
        raise FileNotFoundError(
            "Missing required file(s) for model "
            f"{model}:\n- " + "\n- ".join(missing)
        )


def _compute_model_metrics(model: str, decisions_dir: str) -> List[MethodMetrics]:
    paths = _file_paths_for_model(decisions_dir, model)
    _require_paths(paths, model)

    neutral = _load_choice_map(paths["Neutral"])
    neutral_cot = _load_choice_map(paths["Neutral-CoT"])
    ei = _load_choice_map(paths["EI"])
    ea = _load_choice_map(paths["EA"])

    maps = {
        "Neutral": neutral,
        "Neutral-CoT": neutral_cot,
        "EI": ei,
        "EA": ea,
    }

    ref_idx = set(neutral.keys())
    all4_valid_idx = set(neutral.keys()) & set(neutral_cot.keys()) & set(ei.keys()) & set(ea.keys())

    results: List[MethodMetrics] = []
    for method in METHODS:
        method_map = maps[method]
        method_idx = set(method_map.keys())

        strict_den = len(all4_valid_idx)
        strict_num = sum(1 for idx in all4_valid_idx if method_map[idx] == neutral[idx])

        valid_vs_ref_idx = method_idx & ref_idx
        coverage_den = len(ref_idx)
        coverage_num = len(valid_vs_ref_idx)
        effective_num = sum(1 for idx in valid_vs_ref_idx if method_map[idx] == neutral[idx])

        results.append(
            MethodMetrics(
                model=model,
                method=method,
                n_ref_valid=coverage_den,
                n_all4_valid=strict_den,
                n_method_valid_vs_ref=coverage_num,
                n_strict_match=strict_num,
                n_effective_match=effective_num,
                strict_match_rate=_pct(strict_num, strict_den),
                coverage=_pct(coverage_num, coverage_den),
                effective=_pct(effective_num, coverage_den),
                conditional_match=_pct(effective_num, coverage_num),
            )
        )
    return results


def _aggregate_overall(metrics: Iterable[MethodMetrics]) -> List[MethodMetrics]:
    grouped: Dict[str, Dict[str, int]] = {
        method: {
            "n_ref_valid": 0,
            "n_all4_valid": 0,
            "n_method_valid_vs_ref": 0,
            "n_strict_match": 0,
            "n_effective_match": 0,
        }
        for method in METHODS
    }

    for m in metrics:
        g = grouped[m.method]
        g["n_ref_valid"] += m.n_ref_valid
        g["n_all4_valid"] += m.n_all4_valid
        g["n_method_valid_vs_ref"] += m.n_method_valid_vs_ref
        g["n_strict_match"] += m.n_strict_match
        g["n_effective_match"] += m.n_effective_match

    out: List[MethodMetrics] = []
    for method in METHODS:
        g = grouped[method]
        out.append(
            MethodMetrics(
                model="OVERALL",
                method=method,
                n_ref_valid=g["n_ref_valid"],
                n_all4_valid=g["n_all4_valid"],
                n_method_valid_vs_ref=g["n_method_valid_vs_ref"],
                n_strict_match=g["n_strict_match"],
                n_effective_match=g["n_effective_match"],
                strict_match_rate=_pct(g["n_strict_match"], g["n_all4_valid"]),
                coverage=_pct(g["n_method_valid_vs_ref"], g["n_ref_valid"]),
                effective=_pct(g["n_effective_match"], g["n_ref_valid"]),
                conditional_match=_pct(g["n_effective_match"], g["n_method_valid_vs_ref"]),
            )
        )
    return out


def _print_table(title: str, rows: List[MethodMetrics]) -> None:
    print("\n" + "=" * 132)
    print(title)
    print("=" * 132)
    print(
        "Model   | Method      | RefN  | All4N | Valid(M∩Ref) | StrictMatch | StrictRate | "
        "Coverage | Effective | Conditional"
    )
    print("-" * 132)
    for r in rows:
        print(
            f"{r.model:>7} | "
            f"{r.method:>11} | "
            f"{r.n_ref_valid:>5} | "
            f"{r.n_all4_valid:>5} | "
            f"{r.n_method_valid_vs_ref:>12} | "
            f"{r.n_strict_match:>11} | "
            f"{r.strict_match_rate:>9.2f}% | "
            f"{r.coverage:>7.2f}% | "
            f"{r.effective:>8.2f}% | "
            f"{r.conditional_match:>10.2f}%"
        )


def _write_csv(path: str, rows: List[MethodMetrics]) -> None:
    if not path:
        return
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "model",
                "method",
                "n_ref_valid",
                "n_all4_valid",
                "n_method_valid_vs_ref",
                "n_strict_match",
                "n_effective_match",
                "strict_match_rate",
                "coverage",
                "effective",
                "conditional_match",
            ],
        )
        writer.writeheader()
        for r in rows:
            writer.writerow(
                {
                    "model": r.model,
                    "method": r.method,
                    "n_ref_valid": r.n_ref_valid,
                    "n_all4_valid": r.n_all4_valid,
                    "n_method_valid_vs_ref": r.n_method_valid_vs_ref,
                    "n_strict_match": r.n_strict_match,
                    "n_effective_match": r.n_effective_match,
                    "strict_match_rate": f"{r.strict_match_rate:.6f}",
                    "coverage": f"{r.coverage:.6f}",
                    "effective": f"{r.effective:.6f}",
                    "conditional_match": f"{r.conditional_match:.6f}",
                }
            )


def _fmt_pct(v: float) -> str:
    return f"{v:.2f}%"


def _metric_leader(rows: List[MethodMetrics], metric_name: str) -> str:
    if not rows:
        return "N/A"
    ordered = sorted(rows, key=lambda x: getattr(x, metric_name), reverse=True)
    top = ordered[0]
    return f"{top.method} ({getattr(top, metric_name):.2f}%)"


def _render_markdown_report(
    selected_models: Tuple[str, ...],
    decisions_dir: str,
    per_model_rows: List[MethodMetrics],
    overall_rows: List[MethodMetrics],
) -> str:
    lines: List[str] = []
    lines.append("# Alignment Report (Neutral Reference)")
    lines.append("")
    lines.append("## Scope")
    lines.append(f"- Models: {', '.join(selected_models)}")
    lines.append("- Modes: Neutral (reference), Neutral-CoT, EI, EA")
    lines.append(f"- Decisions directory: `{decisions_dir}`")
    lines.append("")
    lines.append("## Metrics")
    lines.append("- `strict_match_rate`: Match rate on all-4-valid idx (same denominator fairness).")
    lines.append("- `coverage`: Share of Neutral-valid idx where method has valid choice.")
    lines.append("- `effective`: Match vs Neutral over Neutral-valid idx (technical + behavior).")
    lines.append("- `conditional_match`: `effective / coverage` (behavior after removing technical failures).")
    lines.append("")

    for model in selected_models:
        rows = [r for r in per_model_rows if r.model == model]
        if not rows:
            continue
        lines.append(f"## Model `{model}`")
        lines.append("")
        lines.append("| Method | RefN | All4N | Valid(M∩Ref) | StrictMatch | StrictRate | Coverage | Effective | Conditional |")
        lines.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|")
        for r in rows:
            lines.append(
                f"| {r.method} | {r.n_ref_valid} | {r.n_all4_valid} | {r.n_method_valid_vs_ref} | "
                f"{r.n_strict_match} | {_fmt_pct(r.strict_match_rate)} | {_fmt_pct(r.coverage)} | "
                f"{_fmt_pct(r.effective)} | {_fmt_pct(r.conditional_match)} |"
            )
        lines.append("")
        lines.append("**Leaders**")
        lines.append(f"- Strict fairness: {_metric_leader(rows, 'strict_match_rate')}")
        lines.append(f"- Technical coverage: {_metric_leader(rows, 'coverage')}")
        lines.append(f"- End-to-end effective: {_metric_leader(rows, 'effective')}")
        lines.append(f"- Conditional behavior: {_metric_leader(rows, 'conditional_match')}")
        lines.append("")

    lines.append("## Overall (Pooled Across Selected Models)")
    lines.append("")
    lines.append("| Method | RefN | All4N | Valid(M∩Ref) | StrictMatch | StrictRate | Coverage | Effective | Conditional |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|")
    for r in overall_rows:
        lines.append(
            f"| {r.method} | {r.n_ref_valid} | {r.n_all4_valid} | {r.n_method_valid_vs_ref} | "
            f"{r.n_strict_match} | {_fmt_pct(r.strict_match_rate)} | {_fmt_pct(r.coverage)} | "
            f"{_fmt_pct(r.effective)} | {_fmt_pct(r.conditional_match)} |"
        )
    lines.append("")
    lines.append("**Overall leaders**")
    lines.append(f"- Strict fairness: {_metric_leader(overall_rows, 'strict_match_rate')}")
    lines.append(f"- Technical coverage: {_metric_leader(overall_rows, 'coverage')}")
    lines.append(f"- End-to-end effective: {_metric_leader(overall_rows, 'effective')}")
    lines.append(f"- Conditional behavior: {_metric_leader(overall_rows, 'conditional_match')}")
    lines.append("")
    return "\n".join(lines)


def _write_text(path: str, content: str) -> None:
    if not path:
        return
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Compare Neutral, Neutral-CoT, EI, EA by model and overall using strict/coverage/effective metrics."
        )
    )
    parser.add_argument(
        "datasets",
        nargs="*",
        choices=list(MODEL_CODES),
        help="Model codes to analyze. Default: all (CN CT R1 V3).",
    )
    parser.add_argument(
        "--decisions-dir",
        default=DEFAULT_DECISIONS_DIR,
        help=f"Decisions directory (default: {DEFAULT_DECISIONS_DIR})",
    )
    parser.add_argument(
        "--output-csv",
        default="",
        help="Optional output CSV path for per-model metrics.",
    )
    parser.add_argument(
        "--overall-output-csv",
        default="",
        help="Optional output CSV path for pooled overall metrics.",
    )
    parser.add_argument(
        "--report-md",
        default="",
        help="Optional markdown report path.",
    )
    args = parser.parse_args()

    selected_models = tuple(args.datasets) if args.datasets else MODEL_CODES
    all_rows: List[MethodMetrics] = []

    for model in selected_models:
        all_rows.extend(_compute_model_metrics(model, args.decisions_dir))

    overall_rows = _aggregate_overall(all_rows)

    _print_table("Per-model alignment metrics (Neutral reference)", all_rows)
    _print_table("Overall pooled metrics across selected models", overall_rows)

    _write_csv(args.output_csv, all_rows)
    _write_csv(args.overall_output_csv, overall_rows)
    if args.report_md:
        report = _render_markdown_report(selected_models, args.decisions_dir, all_rows, overall_rows)
        _write_text(args.report_md, report)

    if args.output_csv:
        print(f"\nSaved per-model metrics CSV: {args.output_csv}")
    if args.overall_output_csv:
        print(f"Saved overall metrics CSV: {args.overall_output_csv}")
    if args.report_md:
        print(f"Saved markdown report: {args.report_md}")


if __name__ == "__main__":
    main()
