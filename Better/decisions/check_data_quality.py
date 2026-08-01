#!/usr/bin/env python3
"""
Data quality check for Better decision datasets.
Scans EmotionalAnalytic, EmotionalIntuitive, Neutral, Neutral-CoT and produces a summary report.
"""

from __future__ import annotations

import csv
import os
from collections import defaultdict
from pathlib import Path

BASE = Path("/Users/carina/Documents/MyResearch/Professional/DataAnalysis/Better/decisions")
DIRS = ["EmotionalAnalytic", "EmotionalIntuitive", "Neutral", "Neutral-CoT"]

# Column that contains the scenario (emotional vs neutral)
SITUATION_COL_EMOTIONAL = "emotional_situation"
SITUATION_COL_NEUTRAL = "dilemma_situation"


def _normalize_choice_value(cv: str) -> str | None:
    """Return '1', '2', or None. Accepts '1', '2', '1.0', '2.0' and numeric strings."""
    if not cv:
        return None
    cv = cv.strip()
    if cv in ("1", "2"):
        return cv
    try:
        x = float(cv)
        if x == 1.0:
            return "1"
        if x == 2.0:
            return "2"
    except ValueError:
        pass
    return None


def _is_http_success(status: str | None) -> bool:
    """True if status indicates HTTP 200 (accepts '200', '200.0', 200)."""
    if not status:
        return False
    s = (status or "").strip()
    if s == "200":
        return True
    try:
        return float(s) == 200.0
    except ValueError:
        return False


def situation_col_for_dir(dirname: str) -> str:
    if dirname in ("Neutral", "Neutral-CoT"):
        return SITUATION_COL_NEUTRAL
    return SITUATION_COL_EMOTIONAL


def load_csv(path: Path) -> tuple[list[dict], list[str]]:
    rows = []
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames or [])
        for row in reader:
            rows.append(row)
    return rows, fieldnames


def analyze_file(path: Path, situation_col: str) -> dict:
    rows, fieldnames = load_csv(path)
    n = len(rows)
    idxs = []
    missing_idx = 0
    missing_situation = 0
    missing_action1 = 0
    missing_action2 = 0
    missing_decision = 0
    missing_choice_value = 0
    choice_1 = 0
    choice_2 = 0
    choice_other = 0
    choice_empty = 0
    api_error_any = 0
    http_not_200 = 0
    made_choice_true = 0
    has_json_true = 0
    parse_ok = 0

    for r in rows:
        idx_raw = r.get("idx", "").strip()
        try:
            idx = int(idx_raw) if idx_raw else None
        except ValueError:
            idx = None
        if idx is None or (isinstance(idx, int) and idx < 0):
            missing_idx += 1
        else:
            idxs.append(idx)

        sit = (r.get(situation_col) or "").strip()
        if not sit:
            missing_situation += 1
        a1 = (r.get("action1") or "").strip()
        if not a1:
            missing_action1 += 1
        a2 = (r.get("action2") or "").strip()
        if not a2:
            missing_action2 += 1
        dec = (r.get("decision") or "").strip()
        if not dec:
            missing_decision += 1
        cv = (r.get("choice_value") or "").strip()
        cv_norm = _normalize_choice_value(cv)
        if not cv:
            missing_choice_value += 1
            choice_empty += 1
        elif cv_norm == "1":
            choice_1 += 1
        elif cv_norm == "2":
            choice_2 += 1
        else:
            choice_other += 1

        if (r.get("api_error") or "").strip():
            api_error_any += 1
        if not _is_http_success(r.get("http_status")):
            http_not_200 += 1
        # Count outcome failure when decision is "API Failure" but api_error was not recorded (e.g. EI_CN_2 idx 4017)
        dec_lower = (r.get("decision") or "").strip().lower()
        if dec_lower == "api failure" and not (r.get("api_error") or "").strip():
            api_error_any += 1
        if (r.get("made_choice") or "").strip().lower() in ("1", "true", "yes"):
            made_choice_true += 1
        if (r.get("has_json") or "").strip().lower() in ("1", "true", "yes"):
            has_json_true += 1
        if (r.get("choice_parse_status") or "").strip().lower() == "explicit_json":
            parse_ok += 1

    unique_idxs = len(set(idxs))
    duplicate_idxs = len(idxs) - unique_idxs if idxs else 0

    return {
        "path": str(path),
        "name": path.name,
        "n_rows": n,
        "n_unique_idx": unique_idxs,
        "duplicate_idx": duplicate_idxs,
        "missing_idx": missing_idx,
        "missing_situation": missing_situation,
        "missing_action1": missing_action1,
        "missing_action2": missing_action2,
        "missing_decision": missing_decision,
        "missing_choice_value": missing_choice_value,
        "choice_1": choice_1,
        "choice_2": choice_2,
        "choice_other": choice_other,
        "choice_empty": choice_empty,
        "api_error_any": api_error_any,
        "http_not_200": http_not_200,
        "made_choice_true": made_choice_true,
        "has_json_true": has_json_true,
        "parse_ok": parse_ok,
        "idxs": set(idxs),
        "fieldnames": fieldnames,
    }


def analyze_dir(dir_path: Path, dirname: str) -> dict:
    situation_col = situation_col_for_dir(dirname)
    csv_files = sorted(dir_path.glob("*.csv"))
    # Exclude swap files if any ended up here
    csv_files = [f for f in csv_files if "swap" not in f.name.lower()]
    if not csv_files:
        return {"dirname": dirname, "files": [], "by_file": [], "aggregate": {}}

    by_file = []
    all_idxs_by_run = defaultdict(set)
    for f in csv_files:
        a = analyze_file(f, situation_col)
        by_file.append(a)
        run = f.stem.split("_")[-1]  # e.g. 1, 2, 3, CN_1 -> 1
        all_idxs_by_run[run].update(a["idxs"])

    # Aggregate
    total_rows = sum(x["n_rows"] for x in by_file)
    all_idxs = set()
    for x in by_file:
        all_idxs.update(x["idxs"])
    total_unique = len(all_idxs)
    total_missing_cv = sum(x["missing_choice_value"] for x in by_file)
    total_choice_1 = sum(x["choice_1"] for x in by_file)
    total_choice_2 = sum(x["choice_2"] for x in by_file)
    total_choice_other = sum(x["choice_other"] for x in by_file)
    total_api_error = sum(x["api_error_any"] for x in by_file)
    total_http_bad = sum(x["http_not_200"] for x in by_file)
    total_parse_ok = sum(x["parse_ok"] for x in by_file)

    return {
        "dirname": dirname,
        "dir_path": str(dir_path),
        "files": [f.name for f in csv_files],
        "n_files": len(csv_files),
        "by_file": by_file,
        "all_idxs_by_run": dict(all_idxs_by_run),
        "aggregate": {
            "total_rows": total_rows,
            "total_unique_idx": total_unique,
            "total_missing_choice_value": total_missing_cv,
            "total_choice_1": total_choice_1,
            "total_choice_2": total_choice_2,
            "total_choice_other": total_choice_other,
            "total_api_error": total_api_error,
            "total_http_bad": total_http_bad,
            "total_parse_ok": total_parse_ok,
        },
    }


def run_checks() -> list[dict]:
    results = []
    for dirname in DIRS:
        dir_path = BASE / dirname
        if not dir_path.is_dir():
            results.append({"dirname": dirname, "error": "directory not found"})
            continue
        results.append(analyze_dir(dir_path, dirname))
    return results


def write_report(results: list[dict], out_path: Path) -> None:
    lines = []
    lines.append("# Data Quality Report: Better Decision Datasets")
    lines.append("")
    lines.append("**Scope:** EmotionalAnalytic, EmotionalIntuitive, Neutral, Neutral-CoT")
    lines.append("")
    lines.append("---")
    lines.append("")

    for r in results:
        if r.get("error"):
            lines.append(f"## {r['dirname']}")
            lines.append("")
            lines.append(f"Error: {r['error']}")
            lines.append("")
            continue

        dirname = r["dirname"]
        agg = r["aggregate"]
        if not agg:
            lines.append(f"## {dirname}")
            lines.append("")
            lines.append("No CSV files found.")
            lines.append("")
            continue

        lines.append(f"## {dirname}")
        lines.append("")
        lines.append(f"- **Location:** `{r['dir_path']}`")
        lines.append(f"- **Files:** {r['n_files']} ({', '.join(r['files'])})")
        lines.append("")

        total_rows = agg["total_rows"]
        total_unique = agg["total_unique_idx"]
        total_missing_cv = agg["total_missing_choice_value"]
        total_parse_ok = agg["total_parse_ok"]
        total_api_error = agg["total_api_error"]
        total_http_bad = agg["total_http_bad"]
        c1 = agg["total_choice_1"]
        c2 = agg["total_choice_2"]
        c_other = agg["total_choice_other"]

        lines.append("### Aggregate metrics")
        lines.append("")
        lines.append("| Metric | Value |")
        lines.append("|--------|--------|")
        lines.append(f"| Total rows | {total_rows} |")
        lines.append(f"| Unique dilemma indices (idx) | {total_unique} |")
        lines.append(f"| Rows with choice_value in {{1,2}} | {c1 + c2} |")
        lines.append(f"| Choice 1 | {c1} |")
        lines.append(f"| Choice 2 | {c2} |")
        lines.append(f"| Choice value other/empty | {c_other + total_missing_cv} |")
        lines.append(f"| Rows with parse status explicit_json | {total_parse_ok} |")
        lines.append(f"| Rows with API error recorded | {total_api_error} |")
        lines.append(f"| Rows with HTTP status ≠ 200 | {total_http_bad} |")
        lines.append("")

        # Per-file summary
        lines.append("### Per-file summary")
        lines.append("")
        lines.append("| File | Rows | Unique idx | Duplicate idx | Choice 1/2 | Other/empty | API err | Parse OK |")
        lines.append("|------|------|------------|---------------|------------|-------------|--------|----------|")
        for a in r["by_file"]:
            cv_ok = a["choice_1"] + a["choice_2"]
            cv_bad = a["choice_other"] + a["choice_empty"]
            lines.append(
                f"| {a['name']} | {a['n_rows']} | {a['n_unique_idx']} | {a['duplicate_idx']} | {cv_ok} | {cv_bad} | {a['api_error_any']} | {a['parse_ok']} |"
            )
        lines.append("")

        # Completeness and consistency
        lines.append("### Completeness and consistency")
        lines.append("")
        by_file = r["by_file"]
        if by_file:
            idx_sets = [a["idxs"] for a in by_file]
            common = set.intersection(*idx_sets) if idx_sets else set()
            union = set.union(*idx_sets) if idx_sets else set()
            only_in_some = union - common
            lines.append(f"- **Indices present in every file:** {len(common)}")
            lines.append(f"- **Indices in at least one file:** {len(union)}")
            if only_in_some:
                lines.append(f"- **Indices missing in at least one run:** {len(only_in_some)} (run coverage is inconsistent)")
            else:
                lines.append("- **Run coverage:** All files cover the same set of indices.")
        lines.append("")

        # Quality verdict
        pct_ok = (c1 + c2) / total_rows * 100 if total_rows else 0
        pct_parse = total_parse_ok / total_rows * 100 if total_rows else 0
        issues = []
        if total_missing_cv + c_other > 0:
            issues.append("some rows have missing or invalid choice_value")
        if total_api_error > 0 or total_http_bad > 0:
            issues.append("some rows have API/HTTP failures")
        if by_file and any(a["duplicate_idx"] for a in by_file):
            issues.append("duplicate idx within one or more files")
        if not issues:
            issues.append("none detected")

        lines.append("### Quality assessment")
        lines.append("")
        lines.append(f"- **Valid choice rate (choice_value ∈ {{1,2}}):** {pct_ok:.1f}%")
        lines.append(f"- **Explicit JSON parse rate:** {pct_parse:.1f}%")
        lines.append(f"- **Issues:** {'; '.join(issues)}")
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    total_rows_all = 0
    total_valid = 0
    total_api_fail = 0
    for r in results:
        if r.get("error") or not r.get("aggregate"):
            continue
        agg = r["aggregate"]
        total_rows_all += agg["total_rows"]
        total_valid += agg["total_choice_1"] + agg["total_choice_2"]
        total_api_fail += agg["total_api_error"] + agg["total_http_bad"]

    lines.append(f"- **Total rows across all four datasets:** {total_rows_all}")
    lines.append(f"- **Total rows with valid choice (1 or 2):** {total_valid}")
    if total_rows_all:
        lines.append(f"- **Overall valid choice rate:** {100 * total_valid / total_rows_all:.1f}%")
    lines.append(f"- **Total rows with API/HTTP issues:** {total_api_fail}")
    lines.append("")
    lines.append("*Report generated by data quality check script.*")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def main() -> None:
    results = run_checks()
    report_path = BASE.parent / "Analysis" / "DataQualityReport.md"
    write_report(results, report_path)
    print(f"Report written to: {report_path}")
    # Also print short summary to stdout
    print("\n--- Quick summary ---")
    for r in results:
        if r.get("error"):
            print(f"{r['dirname']}: {r['error']}")
        elif r.get("aggregate"):
            agg = r["aggregate"]
            n = agg["total_rows"]
            v = agg["total_choice_1"] + agg["total_choice_2"]
            pct = 100 * v / n if n else 0
            print(f"{r['dirname']}: {n} rows, {v} valid choices ({pct:.1f}%), API/HTTP issues: {agg['total_api_error'] + agg['total_http_bad']}")


if __name__ == "__main__":
    main()
