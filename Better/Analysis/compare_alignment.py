"""
Compare alignment to Neutral reference across 4 models and 4 modes.

Supports three runs of alignment analysis: each run uses each model's own Neutral
baseline (Neutral_run1, Neutral_run2, Neutral_run3). Runs are executed in parallel.

Modes:
- Neutral (reference, per-run baseline)
- Neutral-CoT
- EmotionalIntuitive (EI)
- EmotionalAnalytic (EA)

Metrics per method (vs Neutral):
1) strict_match_rate   : match rate on identical all-4-valid idx set (fair denominator)
2) coverage            : valid-output coverage vs Neutral-valid idx
3) effective           : end-to-end match rate vs Neutral-valid idx
4) conditional_match   : effective / coverage (behavior after technical failures removed)

Why some results are zero:
- RefN (or All4N) can be 0 or very small when, for that model and run, the corresponding CSV
  has few or no rows with valid choice_value (1 or 2). All4N is the count of indices where
  all four modes (Neutral, Neutral-CoT, EI, EA) have a valid choice; if any run-specific
  file is missing, empty, or uses a different index set, the intersection is empty → All4N=0
  and strict_match_rate/effective become 0%. Check that run-specific files (e.g.
  Neutral_CN_2.csv, EA_CN_2.csv) exist and contain the same idx set with valid choices.

Usage:
    # all models, three runs (run 1/2/3 each with model's Neutral baseline), parallel
    python compare_alignment.py

    # selected models
    python compare_alignment.py CN V3

    # optional CSV exports
    python compare_alignment.py --output-csv per_model_metrics.csv --overall-output-csv overall_metrics.csv

    # optional markdown report (default: Analysis/Results/alignment_report.md)
    python compare_alignment.py
    python compare_alignment.py --report-md path/to/custom_report.md
"""

from __future__ import annotations

import argparse
import csv
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Dict, Iterable, List, Set, Tuple


MODEL_CODES: Tuple[str, ...] = ("CN", "CT", "R1", "V3")
METHODS: Tuple[str, ...] = ("EA", "EI", "Neutral-CoT")
REQUIRED_RUNS: Tuple[int, ...] = (1, 2, 3)

# Mode -> (folder_name, file_prefix)
MODE_SPECS: Dict[str, Tuple[str, str]] = {
    "Neutral": ("Neutral", "Neutral"),
    "Neutral-CoT": ("Neutral-CoT", "Neutral-CoT"),
    "EI": ("EmotionalIntuitive", "EI"),
    "EA": ("EmotionalAnalytic", "EA"),
}

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BETTER_DIR = os.path.dirname(SCRIPT_DIR)
DEFAULT_DECISIONS_DIR = os.path.join(BETTER_DIR, "decisions")
DEFAULT_REPORT_MD = os.path.join(SCRIPT_DIR, "Results", "alignment_report.md")


@dataclass
class MethodMetrics:
    model: str
    method: str
    run_id: int
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
    """Return 1 or 2 when valid; None otherwise. Accepts int or float (e.g. 1.0, 2.0)."""
    if raw_value is None or (isinstance(raw_value, str) and not raw_value.strip()):
        return None
    try:
        s = str(raw_value).strip()
        value: int
        if "." in s:
            value = int(float(s))
        else:
            value = int(s)
    except (TypeError, ValueError):
        return None
    return value if value in (1, 2) else None


def _safe_idx(raw_value: object) -> int | None:
    """Parse row index; accepts int or float (e.g. 1.0)."""
    if raw_value is None or (isinstance(raw_value, str) and not str(raw_value).strip()):
        return None
    try:
        s = str(raw_value).strip()
        return int(float(s)) if "." in s else int(s)
    except (TypeError, ValueError):
        return None


def _load_choice_map(csv_path: str) -> Dict[int, int]:
    """Load idx -> choice_value for valid choices only (1/2). Accepts numeric or string columns."""
    idx_to_choice: Dict[int, int] = {}
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            idx = _safe_idx(row.get("idx", ""))
            if idx is None:
                continue
            choice = _safe_choice_value(row.get("choice_value", ""))
            if choice is None:
                continue
            idx_to_choice[idx] = choice
    return idx_to_choice


def _file_paths_for_model_run(decisions_dir: str, model: str, run_id: int) -> Dict[str, str]:
    """Paths for a given model and run. Uses suffix _1, _2, _3 for run-specific files."""
    out: Dict[str, str] = {}
    for mode, (folder, prefix) in MODE_SPECS.items():
        path_with_run = os.path.join(decisions_dir, folder, f"{prefix}_{model}_{run_id}.csv")
        path_legacy = os.path.join(decisions_dir, folder, f"{prefix}_{model}.csv")
        if run_id == 1 and not os.path.isfile(path_with_run) and os.path.isfile(path_legacy):
            out[mode] = path_legacy
        else:
            out[mode] = path_with_run
    return out


def _discover_available_runs(decisions_dir: str, selected_models: Tuple[str, ...]) -> Tuple[int, ...]:
    """Discover run IDs present for Neutral baseline in all selected models. Returns (1,) if only legacy files exist."""
    neutral_dir = os.path.join(decisions_dir, "Neutral")
    if not os.path.isdir(neutral_dir):
        return (1,)
    common_runs: Set[int] = set(REQUIRED_RUNS)
    for model in selected_models:
        model_runs: Set[int] = set()
        for r in REQUIRED_RUNS:
            p = os.path.join(neutral_dir, f"Neutral_{model}_{r}.csv")
            if os.path.isfile(p):
                model_runs.add(r)
        legacy = os.path.join(neutral_dir, f"Neutral_{model}.csv")
        if os.path.isfile(legacy):
            model_runs.add(1)
        if not model_runs:
            raise FileNotFoundError(f"No Neutral files found for model {model} in {neutral_dir}")
        common_runs &= model_runs
    if not common_runs:
        raise FileNotFoundError(
            "No common run IDs found across models. Ensure Neutral_{model}_1.csv (and 2, 3) exist for each model."
        )
    return tuple(sorted(common_runs))


def _require_paths(paths: Dict[str, str], model: str, run_id: int) -> None:
    missing = [f"{name}: {path}" for name, path in paths.items() if not os.path.isfile(path)]
    if missing:
        raise FileNotFoundError(
            f"Missing required file(s) for model {model} run {run_id}:\n- " + "\n- ".join(missing)
        )


def _compute_model_metrics_for_run(model: str, decisions_dir: str, run_id: int) -> List[MethodMetrics]:
    """Compute alignment metrics for one model and one run (using that run's Neutral baseline)."""
    paths = _file_paths_for_model_run(decisions_dir, model, run_id)
    _require_paths(paths, model, run_id)

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
                run_id=run_id,
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
    """Pool counts across all runs and models; compute overall rates."""
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
                run_id=0,
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


def _print_table(title: str, rows: List[MethodMetrics], show_run: bool = True) -> None:
    run_header = "Run | " if show_run else ""
    run_width = 4 if show_run else 0
    sep_len = 132 + (6 if show_run else 0)
    print("\n" + "=" * sep_len)
    print(title)
    print("=" * sep_len)
    print(
        f"{'Run | ' if show_run else ''}"
        "Model   | Method      | RefN  | All4N | Valid(M∩Ref) | StrictMatch | StrictRate | "
        "Coverage | Effective | Conditional"
    )
    print("-" * sep_len)
    for r in rows:
        run_str = f"{r.run_id:>3} | " if show_run else ""
        if r.model == "OVERALL" and show_run:
            run_str = " all | "
        print(
            f"{run_str}"
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
    base = os.path.dirname(os.path.abspath(path))
    if base:
        os.makedirs(base, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "model",
                "method",
                "run_id",
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
                    "run_id": r.run_id,
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
    run_ids: Tuple[int, ...],
    decisions_dir: str,
    per_model_rows: List[MethodMetrics],
    overall_rows: List[MethodMetrics],
) -> str:
    lines: List[str] = []
    lines.append("# Alignment Report (Neutral Reference)")
    lines.append("")
    lines.append("## Scope")
    lines.append(f"- Models: {', '.join(selected_models)}")
    lines.append(f"- Runs: {', '.join(str(r) for r in run_ids)} (each run uses each model's Neutral baseline)")
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
        lines.append(f"## Model `{model}` (by run)")
        lines.append("")
        lines.append("| Run | Method | RefN | All4N | Valid(M∩Ref) | StrictMatch | StrictRate | Coverage | Effective | Conditional |")
        lines.append("|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
        for r in sorted(rows, key=lambda x: (x.run_id, x.method)):
            lines.append(
                f"| {r.run_id} | {r.method} | {r.n_ref_valid} | {r.n_all4_valid} | {r.n_method_valid_vs_ref} | "
                f"{r.n_strict_match} | {_fmt_pct(r.strict_match_rate)} | {_fmt_pct(r.coverage)} | "
                f"{_fmt_pct(r.effective)} | {_fmt_pct(r.conditional_match)} |"
            )
        lines.append("")
        lines.append("**Leaders (across runs)**")
        lines.append(f"- Strict fairness: {_metric_leader(rows, 'strict_match_rate')}")
        lines.append(f"- Technical coverage: {_metric_leader(rows, 'coverage')}")
        lines.append(f"- End-to-end effective: {_metric_leader(rows, 'effective')}")
        lines.append(f"- Conditional behavior: {_metric_leader(rows, 'conditional_match')}")
        lines.append("")

    lines.append("## Overall rate (pooled across runs and models)")
    lines.append("")
    for r in overall_rows:
        lines.append(f"### {r.method}")
        lines.append(f"- **Strict match rate:** {_fmt_pct(r.strict_match_rate)} (n = {r.n_strict_match} / {r.n_all4_valid})")
        lines.append(f"- **Coverage:** {_fmt_pct(r.coverage)} | **Effective:** {_fmt_pct(r.effective)} | **Conditional:** {_fmt_pct(r.conditional_match)}")
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
    base = os.path.dirname(os.path.abspath(path))
    if base:
        os.makedirs(base, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def _print_overall_rate(overall_rows: List[MethodMetrics]) -> None:
    """Print a clear overall alignment rate summary."""
    print("\n" + "=" * 80)
    print("OVERALL ALIGNMENT RATE (pooled across all runs and models)")
    print("=" * 80)
    for r in overall_rows:
        print(
            f"  {r.method:11} | Strict: {r.strict_match_rate:6.2f}% (n={r.n_strict_match}/{r.n_all4_valid}) | "
            f"Coverage: {r.coverage:6.2f}% | Effective: {r.effective:6.2f}% | Conditional: {r.conditional_match:6.2f}%"
        )
    print("=" * 80)


def _warn_incomplete_runs(all_rows: List[MethodMetrics], min_ref_valid: int = 500) -> None:
    """Print a note when some (model, run) have no or very few valid indices (explains zeros)."""
    # One row per (model, run_id) is enough; use first method's counts for that cell
    seen: Set[Tuple[str, int]] = set()
    incomplete: List[Tuple[str, int, int, int]] = []  # model, run_id, n_ref_valid, n_all4_valid
    for r in all_rows:
        if r.model == "OVERALL":
            continue
        key = (r.model, r.run_id)
        if key in seen:
            continue
        seen.add(key)
        if r.n_all4_valid == 0 or r.n_ref_valid < min_ref_valid:
            incomplete.append((r.model, r.run_id, r.n_ref_valid, r.n_all4_valid))
    if not incomplete:
        return
    print("\nNote: Some (model, run) have zero or very small valid counts → 0%% rates above.")
    print("  Cause: for that run, at least one of [Neutral, Neutral-CoT, EI, EA] has few or no")
    print("  valid choice_value (1/2) or a different index set, so the intersection is empty.")
    print("  Affected (model, run): RefN, All4N")
    for model, run_id, ref_n, all4_n in sorted(incomplete):
        print(f"    {model} run {run_id}: RefN={ref_n}, All4N={all4_n}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Compare Neutral, Neutral-CoT, EI, EA by model and overall (three runs, parallel, each run uses model Neutral baseline)."
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
        default=DEFAULT_REPORT_MD,
        help=f"Markdown report path (default: {DEFAULT_REPORT_MD}).",
    )
    parser.add_argument(
        "--max-workers",
        type=int,
        default=6,
        help="Max parallel workers for run-wise computation (default: 6).",
    )
    args = parser.parse_args()

    selected_models = tuple(args.datasets) if args.datasets else MODEL_CODES
    run_ids = _discover_available_runs(args.decisions_dir, selected_models)

    # Run alignment for each (model, run_id) in parallel; each run uses that model's Neutral baseline
    all_rows: List[MethodMetrics] = []
    tasks = [(model, run_id) for model in selected_models for run_id in run_ids]
    with ThreadPoolExecutor(max_workers=min(args.max_workers, len(tasks))) as executor:
        futures = {
            executor.submit(_compute_model_metrics_for_run, model, args.decisions_dir, run_id): (model, run_id)
            for model, run_id in tasks
        }
        for future in as_completed(futures):
            model, run_id = futures[future]
            try:
                all_rows.extend(future.result())
            except FileNotFoundError as e:
                raise SystemExit(f"Alignment run failed for model={model} run={run_id}: {e}") from e

    overall_rows = _aggregate_overall(all_rows)

    _print_table("Per-model, per-run alignment metrics (Neutral reference)", all_rows, show_run=True)
    _warn_incomplete_runs(all_rows)
    _print_table("Overall pooled metrics (all runs, all models)", overall_rows, show_run=False)
    _print_overall_rate(overall_rows)

    _write_csv(args.output_csv, all_rows)
    _write_csv(args.overall_output_csv, overall_rows)
    if args.report_md:
        report = _render_markdown_report(
            selected_models, run_ids, args.decisions_dir, all_rows, overall_rows
        )
        _write_text(args.report_md, report)

    if args.output_csv:
        print(f"\nSaved per-model metrics CSV: {args.output_csv}")
    if args.overall_output_csv:
        print(f"Saved overall metrics CSV: {args.overall_output_csv}")
    if args.report_md:
        print(f"Saved markdown report: {args.report_md}")


if __name__ == "__main__":
    main()
