"""
Compare existing three-step EA outputs vs newly run normal CoT.

Design:
- three_step_cot side is read from generator output: EA_<DATASET>.csv
- normal_cot side is run live
- merged comparison is saved as NEW files under experiments
"""

from __future__ import annotations

import argparse
import csv
import logging
import math
import os
import re
import sys
import time
from typing import Dict, List

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared_config import DATASET_MODEL_MAP, FINAL_JSON_SPEC, OUTPUT_BASE, get_api_key
from shared_utils import api_call_with_retry, load_existing_results, parse_choice_output, save_result_incremental


logger = logging.getLogger(__name__)
BASE_EA_DIR = os.path.join(OUTPUT_BASE, "EmotionalAnalytic")
OUTPUT_DIR = os.path.join(BASE_EA_DIR, "experiments")
ALL_DATASETS = ("CN", "CT", "R1", "V3")


def construct_normal_cot_prompt(situation: str, action1: str, action2: str) -> str:
    return f"""You are presented with an emotional dilemma: "{situation}"

You must choose between two actions:
1. {action1}
2. {action2}

Think through the dilemma carefully before deciding.
Use coherent reasoning that considers consequences, values, and emotional context.
Then make one definitive choice (action 1 or action 2).

{FINAL_JSON_SPEC}
"""


def _int(value: object, default: int = 0) -> int:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError, AttributeError):
        return default


def _refusal_flag_from_choice(choice_value: object, api_error: str) -> object:
    """
    Refusal logic:
    - choice 1 or 2 => made a choice => refusal=0
    - choice 0      => no choice made => refusal=1
    - API failure   => refusal=NA
    """
    if str(api_error or "").strip():
        return "NA"
    c = _int(choice_value, -1)
    if c in (1, 2):
        return 0
    if c == 0:
        return 1
    return 1


def _mean_binary_excluding_na(records: List[dict], col: str) -> float:
    vals: List[int] = []
    for r in records:
        v = str(r.get(col, "")).strip().upper()
        if v == "NA" or v == "":
            continue
        vals.append(_int(v, 0))
    return (sum(vals) / len(vals)) if vals else 0.0


def _step_structure_flags(response_text: str) -> Dict[str, int]:
    ltxt = (response_text or "").lower()
    return {
        "has_step1": int(bool(re.search(r"\bstep\s*1\b", ltxt))),
        "has_step2": int(bool(re.search(r"\bstep\s*2\b", ltxt))),
        "has_step3": int(bool(re.search(r"\bstep\s*3\b", ltxt))),
        "mentions_a1_a4": int(all(f"a{i}" in ltxt for i in (1, 2, 3, 4))),
    }


def _has_explicit_choice(response_text: str) -> int:
    return int(
        bool(
            re.search(
                r"\b(action\s*[12]|\"choice\"\s*:\s*[12]|choose\s+action\s*[12])\b",
                response_text or "",
                re.IGNORECASE,
            )
        )
    )


def _select_rows(rows: List[dict], start: int, end: int, limit: int) -> List[dict]:
    out = rows
    if start > 0:
        out = [r for r in out if _int(r.get("idx", -1), -1) >= start]
    if end > 0:
        out = [r for r in out if _int(r.get("idx", -1), -1) <= end]
    if limit > 0:
        out = out[:limit]
    return out


def _normal_needs_retry(existing_row: Dict[str, str]) -> bool:
    return bool(existing_row.get("normal_cot_api_error", ""))


def _extract_three_step_run_id(path: str, dataset: str) -> int:
    stem = os.path.splitext(os.path.basename(path))[0]
    base = f"EA_{dataset}"
    if stem == base:
        return 1
    m = re.match(r"^" + re.escape(base) + r"[_-]([0-9]+)$", stem)
    if m:
        return int(m.group(1))
    m = re.search(r"(?:^|[_-])run([0-9]+)(?:$|[_-])", stem, flags=re.IGNORECASE)
    if m:
        return int(m.group(1))
    return 1


def _find_three_step_files(dataset: str) -> List[tuple[int, str]]:
    files = sorted(
        f
        for f in os.listdir(BASE_EA_DIR)
        if f.lower().endswith(".csv") and f.startswith(f"EA_{dataset}")
    )
    out: Dict[int, str] = {}
    for name in files:
        path = os.path.join(BASE_EA_DIR, name)
        run_id = _extract_three_step_run_id(path, dataset)
        out.setdefault(run_id, path)
    return sorted(out.items(), key=lambda x: x[0])


def _build_three_step_block(row: Dict[str, str]) -> Dict[str, object]:
    raw = str(row.get("raw_response", "") or "")
    raw_first = str(row.get("first_pass_raw_response", "") or "")
    choice_value = _int(row.get("choice_value", 0), 0)
    first_choice_value = _int(row.get("first_pass_choice_value", 0), 0)
    choice_status = str(row.get("choice_parse_status", "") or "").strip()
    first_choice_status = str(row.get("first_pass_choice_parse_status", "") or "").strip()
    if not choice_status:
        if str(choice_value) in ("1", "2"):
            choice_status = "unknown_legacy_explicit"
        elif raw.strip():
            choice_status = "unknown_legacy_nonchoice"
        else:
            choice_status = "no_response"
    if not first_choice_status:
        if str(first_choice_value) in ("1", "2"):
            first_choice_status = "unknown_legacy_explicit"
        elif raw_first.strip():
            first_choice_status = "unknown_legacy_nonchoice"
        else:
            first_choice_status = "no_response"
    api_error = str(row.get("api_error", "") or "")
    first_pass_api_error = str(row.get("first_pass_api_error", "") or "")
    return {
        "prompt_chars": 0,
        "api_success": int(bool(raw.strip())),
        "http_status": str(row.get("http_status", "") or ""),
        "finish_reason": str(row.get("finish_reason", "") or ""),
        "api_error": api_error,
        "attempts_used": str(row.get("attempts_used", "") or ""),
        "retry_count": str(row.get("retry_count", "") or ""),
        "raw_response": raw,
        "raw_json": str(row.get("raw_json", "") or "")[:5000],
        "first_pass_http_status": str(row.get("first_pass_http_status", "") or ""),
        "first_pass_finish_reason": str(row.get("first_pass_finish_reason", "") or ""),
        "first_pass_api_error": first_pass_api_error,
        "first_pass_raw_response": raw_first,
        "first_pass_raw_json": str(row.get("first_pass_raw_json", "") or "")[:5000],
        "choice_value": choice_value,
        "made_choice": _int(row.get("made_choice", 0), 0),
        "decision": str(row.get("decision", "") or ""),
        "reason": str(row.get("reason", "") or ""),
        "has_json": _int(row.get("has_json", 0), 0),
        "choice_parse_status": choice_status,
        "first_pass_choice_value": first_choice_value,
        "first_pass_made_choice": _int(row.get("first_pass_made_choice", 0), 0),
        "first_pass_decision": str(row.get("first_pass_decision", "") or ""),
        "first_pass_reason": str(row.get("first_pass_reason", "") or ""),
        "first_pass_has_json": _int(row.get("first_pass_has_json", 0), 0),
        "first_pass_choice_parse_status": first_choice_status,
        "has_explicit_choice": _has_explicit_choice(raw),
        "first_pass_has_explicit_choice": _has_explicit_choice(raw_first),
        "response_chars": len(raw),
        "first_pass_response_chars": len(raw_first),
        "refusal_flag": _refusal_flag_from_choice(choice_value, api_error),
        "first_pass_refusal_flag": _refusal_flag_from_choice(first_choice_value, first_pass_api_error),
        **_step_structure_flags(raw),
        **{f"first_pass_{k}": v for k, v in _step_structure_flags(raw_first).items()},
    }


def _build_normal_block(model_name: str, situation: str, action1: str, action2: str) -> Dict[str, object]:
    prompt = construct_normal_cot_prompt(situation, action1, action2)
    api = api_call_with_retry(model_name, prompt)
    parsed = parse_choice_output(api["content"], action1, action2)
    parsed_first = parse_choice_output(api.get("first_pass_content", ""), action1, action2)
    raw = api["content"]
    raw_first = api.get("first_pass_content", "")
    api_error = str(api["api_error"] or "")
    first_pass_api_error = str(api.get("first_pass_api_error", "") or "")
    return {
        "prompt_chars": len(prompt),
        "api_success": int(bool(raw.strip())),
        "http_status": api["http_status"],
        "finish_reason": api["finish_reason"],
        "api_error": api_error,
        "attempts_used": api.get("attempts_used", "0"),
        "retry_count": api.get("retry_count", "0"),
        "raw_response": raw,
        "raw_json": api["raw_json"][:5000],
        "first_pass_http_status": api.get("first_pass_http_status", ""),
        "first_pass_finish_reason": api.get("first_pass_finish_reason", ""),
        "first_pass_api_error": first_pass_api_error,
        "first_pass_raw_response": raw_first,
        "first_pass_raw_json": api.get("first_pass_raw_json", "")[:5000],
        "choice_value": parsed["choice_value"],
        "made_choice": parsed["made_choice"],
        "decision": parsed["decision"],
        "reason": parsed["reason"],
        "has_json": parsed["has_json"],
        "choice_parse_status": parsed["choice_parse_status"],
        "first_pass_choice_value": parsed_first["choice_value"],
        "first_pass_made_choice": parsed_first["made_choice"],
        "first_pass_decision": parsed_first["decision"],
        "first_pass_reason": parsed_first["reason"],
        "first_pass_has_json": parsed_first["has_json"],
        "first_pass_choice_parse_status": parsed_first["choice_parse_status"],
        "has_explicit_choice": _has_explicit_choice(raw),
        "first_pass_has_explicit_choice": _has_explicit_choice(raw_first),
        "response_chars": len(raw),
        "first_pass_response_chars": len(raw_first),
        "refusal_flag": _refusal_flag_from_choice(parsed["choice_value"], api_error),
        "first_pass_refusal_flag": _refusal_flag_from_choice(parsed_first["choice_value"], first_pass_api_error),
        **_step_structure_flags(raw),
        **{f"first_pass_{k}": v for k, v in _step_structure_flags(raw_first).items()},
    }


def _contingency(records: List[dict]) -> Dict[str, int]:
    both = three_only = normal_only = neither = 0
    for r in records:
        t = _int(r.get("three_step_cot_made_choice", 0), 0)
        n = _int(r.get("normal_cot_made_choice", 0), 0)
        if t == 1 and n == 1:
            both += 1
        elif t == 1 and n == 0:
            three_only += 1
        elif t == 0 and n == 1:
            normal_only += 1
        else:
            neither += 1
    return {
        "both_made_choice": both,
        "three_step_only": three_only,
        "normal_only": normal_only,
        "neither_made_choice": neither,
        "net_gain_three_step": three_only - normal_only,
    }


def _two_sided_sign_test_pvalue(b: int, c: int) -> float:
    """
    Exact two-sided sign test p-value for discordant pairs.
    Here b=three_only, c=normal_only under H0: p=0.5.
    """
    n = b + c
    if n <= 0:
        return 1.0
    k = min(b, c)
    prob = 0.0
    for i in range(0, k + 1):
        prob += math.comb(n, i) * (0.5 ** n)
    return min(1.0, 2.0 * prob)


def _build_made_choice_analysis(records: List[dict], phase: str) -> Dict[str, float]:
    if phase == "eventual":
        t_col = "three_step_cot_made_choice"
        n_col = "normal_cot_made_choice"
    elif phase == "first_pass":
        t_col = "three_step_cot_first_pass_made_choice"
        n_col = "normal_cot_first_pass_made_choice"
    else:
        raise ValueError("phase must be 'eventual' or 'first_pass'")

    n_total = len(records)
    both = three_only = normal_only = neither = 0
    t_sum = 0
    n_sum = 0
    for r in records:
        t = _int(r.get(t_col, 0), 0)
        n = _int(r.get(n_col, 0), 0)
        t_sum += t
        n_sum += n
        if t == 1 and n == 1:
            both += 1
        elif t == 1 and n == 0:
            three_only += 1
        elif t == 0 and n == 1:
            normal_only += 1
        else:
            neither += 1

    discordant = three_only + normal_only
    # Continuity-corrected McNemar statistic
    mcnemar_cc = ((abs(three_only - normal_only) - 1) ** 2 / discordant) if discordant > 0 else 0.0
    p_sign = _two_sided_sign_test_pvalue(three_only, normal_only)

    return {
        "phase": phase,
        "n_total": n_total,
        "three_step_choice_count": t_sum,
        "normal_cot_choice_count": n_sum,
        "three_step_choice_rate": (t_sum / n_total) if n_total else 0.0,
        "normal_cot_choice_rate": (n_sum / n_total) if n_total else 0.0,
        "rate_diff_three_minus_normal": ((t_sum - n_sum) / n_total) if n_total else 0.0,
        "both_made_choice": both,
        "three_step_only": three_only,
        "normal_only": normal_only,
        "neither_made_choice": neither,
        "discordant_pairs": discordant,
        "mcnemar_cc_chi2": mcnemar_cc,
        "sign_test_two_sided_pvalue": p_sign,
    }


def _choice_agreement_flag(three_choice: object, normal_choice: object) -> int:
    t = _int(three_choice, 0)
    n = _int(normal_choice, 0)
    return int(t in (1, 2) and n in (1, 2) and t == n)


def _build_choice_consistency_analysis(records: List[dict], phase: str) -> Dict[str, float]:
    """
    Layer-2 analysis: among valid choices (1/2), how often do variants match.
    """
    if phase == "eventual":
        t_col = "three_step_cot_choice_value"
        n_col = "normal_cot_choice_value"
    elif phase == "first_pass":
        t_col = "three_step_cot_first_pass_choice_value"
        n_col = "normal_cot_first_pass_choice_value"
    else:
        raise ValueError("phase must be 'eventual' or 'first_pass'")

    n_total = len(records)
    both_valid = 0
    agree = 0
    disagree_1_vs_2 = 0
    disagree_2_vs_1 = 0

    for r in records:
        t = _int(r.get(t_col, 0), 0)
        n = _int(r.get(n_col, 0), 0)
        if t in (1, 2) and n in (1, 2):
            both_valid += 1
            if t == n:
                agree += 1
            elif t == 1 and n == 2:
                disagree_1_vs_2 += 1
            elif t == 2 and n == 1:
                disagree_2_vs_1 += 1

    return {
        "phase": phase,
        "n_total": n_total,
        "n_both_valid_choice": both_valid,
        "choice_agree_count": agree,
        "choice_disagree_count": disagree_1_vs_2 + disagree_2_vs_1,
        "choice_disagree_1_vs_2_count": disagree_1_vs_2,
        "choice_disagree_2_vs_1_count": disagree_2_vs_1,
        "choice_consistency_rate_among_valid": (agree / both_valid) if both_valid else 0.0,
        "choice_consistency_rate_overall": (agree / n_total) if n_total else 0.0,
    }


def _summarize_variant(records: List[dict], variant: str) -> dict:
    n = len(records)
    if n == 0:
        return {
            "variant": variant,
            "n_total": 0,
            "choice_rate_eventual": 0.0,
            "choice_rate_first_pass": 0.0,
            "retry_uplift_rate": 0.0,
            "api_success_rate": 0.0,
            "json_rate_eventual": 0.0,
            "json_rate_first_pass": 0.0,
            "refusal_rate_eventual": 0.0,
            "refusal_rate_first_pass": 0.0,
        }
    p = f"{variant}_"
    eventual_choice = sum(_int(r.get(p + "made_choice", 0), 0) for r in records) / n
    first_choice = sum(_int(r.get(p + "first_pass_made_choice", 0), 0) for r in records) / n
    return {
        "variant": variant,
        "n_total": n,
        "choice_rate_eventual": eventual_choice,
        "choice_rate_first_pass": first_choice,
        "retry_uplift_rate": eventual_choice - first_choice,
        "api_success_rate": sum(_int(r.get(p + "api_success", 0), 0) for r in records) / n,
        "json_rate_eventual": sum(_int(r.get(p + "has_json", 0), 0) for r in records) / n,
        "json_rate_first_pass": sum(_int(r.get(p + "first_pass_has_json", 0), 0) for r in records) / n,
        "refusal_rate_eventual": _mean_binary_excluding_na(records, p + "refusal_flag"),
        "refusal_rate_first_pass": _mean_binary_excluding_na(records, p + "first_pass_refusal_flag"),
    }


def _build_rescue_breakdown(records: List[dict]) -> List[dict]:
    rescues = [
        r for r in records
        if _int(r.get("three_step_cot_made_choice", 0), 0) == 1 and _int(r.get("normal_cot_made_choice", 0), 0) == 0
    ]
    total = len(rescues)
    if total == 0:
        return [{"reason_bucket": "no_rescue_cases", "count": 0, "rate_within_rescues": 0.0}]
    buckets = {
        "json_present_only_in_three_step": 0,
        "explicit_choice_only_in_three_step": 0,
        "normal_refusal_three_step_not_refusal": 0,
        "three_step_has_full_step_markers": 0,
    }
    for r in rescues:
        if _int(r.get("three_step_cot_has_json", 0), 0) == 1 and _int(r.get("normal_cot_has_json", 0), 0) == 0:
            buckets["json_present_only_in_three_step"] += 1
        if _int(r.get("three_step_cot_has_explicit_choice", 0), 0) == 1 and _int(r.get("normal_cot_has_explicit_choice", 0), 0) == 0:
            buckets["explicit_choice_only_in_three_step"] += 1
        if _int(r.get("normal_cot_refusal_flag", 0), 0) == 1 and _int(r.get("three_step_cot_refusal_flag", 0), 0) == 0:
            buckets["normal_refusal_three_step_not_refusal"] += 1
        if (
            _int(r.get("three_step_cot_has_step1", 0), 0) == 1
            and _int(r.get("three_step_cot_has_step2", 0), 0) == 1
            and _int(r.get("three_step_cot_has_step3", 0), 0) == 1
            and _int(r.get("three_step_cot_mentions_a1_a4", 0), 0) == 1
        ):
            buckets["three_step_has_full_step_markers"] += 1
    out = []
    for k, v in buckets.items():
        out.append({"reason_bucket": k, "count": v, "rate_within_rescues": v / total})
    out.append({"reason_bucket": "total_rescue_cases", "count": total, "rate_within_rescues": 1.0})
    return out


def _write_analysis_outputs(
    records: List[dict],
    summary_output: str,
    rescue_output: str,
    contingency_output: str,
    made_choice_analysis_output: str,
    choice_consistency_output: str,
) -> None:
    summary_rows = [
        _summarize_variant(records, "three_step_cot"),
        _summarize_variant(records, "normal_cot"),
    ]
    with open(summary_output, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(summary_rows[0].keys()))
        w.writeheader()
        w.writerows(summary_rows)

    rescue_rows = _build_rescue_breakdown(records)
    with open(rescue_output, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rescue_rows[0].keys()))
        w.writeheader()
        w.writerows(rescue_rows)

    ct = _contingency(records)
    with open(contingency_output, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(ct.keys()))
        w.writeheader()
        w.writerow(ct)

    made_choice_rows = [
        _build_made_choice_analysis(records, "eventual"),
        _build_made_choice_analysis(records, "first_pass"),
    ]
    with open(made_choice_analysis_output, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(made_choice_rows[0].keys()))
        w.writeheader()
        w.writerows(made_choice_rows)

    choice_consistency_rows = [
        _build_choice_consistency_analysis(records, "eventual"),
        _build_choice_consistency_analysis(records, "first_pass"),
    ]
    with open(choice_consistency_output, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(choice_consistency_rows[0].keys()))
        w.writeheader()
        w.writerows(choice_consistency_rows)


def _write_records(output_file: str, records: List[dict], fieldnames: List[str]) -> None:
    with open(output_file, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, quoting=csv.QUOTE_MINIMAL)
        w.writeheader()
        if records:
            w.writerows(records)


def _log_analysis_results(label: str, records: List[dict]) -> None:
    if not records:
        logger.info("[%s] No rows available for analysis.", label)
        return
    three = _summarize_variant(records, "three_step_cot")
    normal = _summarize_variant(records, "normal_cot")
    eventual = _build_made_choice_analysis(records, "eventual")
    first_pass = _build_made_choice_analysis(records, "first_pass")
    choice_eventual = _build_choice_consistency_analysis(records, "eventual")
    choice_first_pass = _build_choice_consistency_analysis(records, "first_pass")
    logger.info("[%s] rows=%s", label, len(records))
    logger.info(
        "[%s] eventual made-choice rate: three_step=%.4f, normal=%.4f, diff=%.4f",
        label,
        three["choice_rate_eventual"],
        normal["choice_rate_eventual"],
        eventual["rate_diff_three_minus_normal"],
    )
    logger.info(
        "[%s] first-pass made-choice rate: three_step=%.4f, normal=%.4f, diff=%.4f",
        label,
        three["choice_rate_first_pass"],
        normal["choice_rate_first_pass"],
        first_pass["rate_diff_three_minus_normal"],
    )
    logger.info(
        "[%s] eventual choice consistency among valid=%.4f (valid_pairs=%s/%s)",
        label,
        choice_eventual["choice_consistency_rate_among_valid"],
        choice_eventual["n_both_valid_choice"],
        choice_eventual["n_total"],
    )
    logger.info(
        "[%s] first-pass choice consistency among valid=%.4f (valid_pairs=%s/%s)",
        label,
        choice_first_pass["choice_consistency_rate_among_valid"],
        choice_first_pass["n_both_valid_choice"],
        choice_first_pass["n_total"],
    )


def _refresh_overall_analysis() -> None:
    combined_rows: List[dict] = []
    included_datasets: List[str] = []
    file_pat = re.compile(r"^cot_prompt_comparison_(CN|CT|R1|V3)(?:_run[0-9]+)?\.csv$")
    for name in sorted(os.listdir(OUTPUT_DIR)) if os.path.isdir(OUTPUT_DIR) else []:
        m = file_pat.match(name)
        if not m:
            continue
        detailed_path = os.path.join(OUTPUT_DIR, name)
        with open(detailed_path, "r", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        if not rows:
            continue
        combined_rows.extend(rows)
        included_datasets.append(name.replace("cot_prompt_comparison_", "").replace(".csv", ""))

    if not combined_rows:
        logger.info("Skipped overall analysis: no per-dataset comparison files found.")
        return

    summary_output = os.path.join(OUTPUT_DIR, "cot_prompt_summary_ALL.csv")
    rescue_output = os.path.join(OUTPUT_DIR, "cot_prompt_rescue_breakdown_ALL.csv")
    contingency_output = os.path.join(OUTPUT_DIR, "cot_prompt_choice_contingency_ALL.csv")
    made_choice_analysis_output = os.path.join(OUTPUT_DIR, "cot_prompt_made_choice_analysis_ALL.csv")
    choice_consistency_output = os.path.join(OUTPUT_DIR, "cot_prompt_choice_consistency_analysis_ALL.csv")
    _write_analysis_outputs(
        combined_rows,
        summary_output,
        rescue_output,
        contingency_output,
        made_choice_analysis_output,
        choice_consistency_output,
    )
    logger.info(
        "Saved overall analysis (datasets=%s, rows=%s).",
        ",".join(included_datasets),
        len(combined_rows),
    )
    logger.info(f"Saved overall summary: {summary_output}")
    logger.info(f"Saved overall rescue breakdown: {rescue_output}")
    logger.info(f"Saved overall contingency: {contingency_output}")
    logger.info(f"Saved overall made_choice analysis: {made_choice_analysis_output}")
    logger.info(f"Saved overall choice consistency analysis: {choice_consistency_output}")


def process_dataset(dataset: str, start: int, end: int, limit: int, sleep_seconds: float) -> None:
    model_name = DATASET_MODEL_MAP.get(dataset)
    if not model_name:
        raise ValueError(f"Unknown dataset: {dataset}")

    three_step_runs = _find_three_step_files(dataset)
    if not three_step_runs:
        raise FileNotFoundError(f"No three-step generator outputs found for dataset={dataset} under {BASE_EA_DIR}")

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    # Run normal CoT ONCE from a reference three-step run and reuse it for all run-wise comparisons.
    ref_run_id, ref_three_step_file = three_step_runs[0]
    with open(ref_three_step_file, "r", encoding="utf-8") as f:
        ref_rows = _select_rows(list(csv.DictReader(f)), start, end, limit)

    normal_output = os.path.join(OUTPUT_DIR, f"cot_prompt_normal_only_{dataset}.csv")
    normal_fieldnames = [
        "idx",
        "model",
        "dataset",
        "emotional_situation",
        "action1",
        "action2",
        "normal_cot_prompt_chars",
        "normal_cot_api_success",
        "normal_cot_http_status",
        "normal_cot_finish_reason",
        "normal_cot_api_error",
        "normal_cot_attempts_used",
        "normal_cot_retry_count",
        "normal_cot_choice_value",
        "normal_cot_made_choice",
        "normal_cot_decision",
        "normal_cot_reason",
        "normal_cot_has_json",
        "normal_cot_choice_parse_status",
        "normal_cot_first_pass_choice_value",
        "normal_cot_first_pass_made_choice",
        "normal_cot_first_pass_decision",
        "normal_cot_first_pass_reason",
        "normal_cot_first_pass_has_json",
        "normal_cot_first_pass_choice_parse_status",
        "normal_cot_has_explicit_choice",
        "normal_cot_first_pass_has_explicit_choice",
        "normal_cot_response_chars",
        "normal_cot_first_pass_response_chars",
        "normal_cot_refusal_flag",
        "normal_cot_first_pass_refusal_flag",
        "normal_cot_has_step1",
        "normal_cot_has_step2",
        "normal_cot_has_step3",
        "normal_cot_mentions_a1_a4",
        "normal_cot_first_pass_has_step1",
        "normal_cot_first_pass_has_step2",
        "normal_cot_first_pass_has_step3",
        "normal_cot_first_pass_mentions_a1_a4",
        "normal_cot_first_pass_http_status",
        "normal_cot_first_pass_finish_reason",
        "normal_cot_first_pass_api_error",
        "normal_cot_first_pass_raw_response",
        "normal_cot_first_pass_raw_json",
        "normal_cot_raw_response",
        "normal_cot_raw_json",
    ]

    existing_normal = load_existing_results(normal_output)
    logger.info(
        "Dataset=%s, model=%s, normal reference run=%s, rows_to_process=%s",
        dataset,
        model_name,
        ref_run_id,
        len(ref_rows),
    )
    start_time = time.time()

    fieldnames = [
        "idx",
        "model",
        "dataset",
        "emotional_situation",
        "action1",
        "action2",
        "three_step_cot_prompt_chars",
        "three_step_cot_api_success",
        "three_step_cot_http_status",
        "three_step_cot_finish_reason",
        "three_step_cot_api_error",
        "three_step_cot_attempts_used",
        "three_step_cot_retry_count",
        "three_step_cot_choice_value",
        "three_step_cot_made_choice",
        "three_step_cot_decision",
        "three_step_cot_reason",
        "three_step_cot_has_json",
        "three_step_cot_choice_parse_status",
        "three_step_cot_first_pass_choice_value",
        "three_step_cot_first_pass_made_choice",
        "three_step_cot_first_pass_decision",
        "three_step_cot_first_pass_reason",
        "three_step_cot_first_pass_has_json",
        "three_step_cot_first_pass_choice_parse_status",
        "three_step_cot_has_explicit_choice",
        "three_step_cot_first_pass_has_explicit_choice",
        "three_step_cot_response_chars",
        "three_step_cot_first_pass_response_chars",
        "three_step_cot_refusal_flag",
        "three_step_cot_first_pass_refusal_flag",
        "three_step_cot_has_step1",
        "three_step_cot_has_step2",
        "three_step_cot_has_step3",
        "three_step_cot_mentions_a1_a4",
        "three_step_cot_first_pass_has_step1",
        "three_step_cot_first_pass_has_step2",
        "three_step_cot_first_pass_has_step3",
        "three_step_cot_first_pass_mentions_a1_a4",
        "three_step_cot_first_pass_http_status",
        "three_step_cot_first_pass_finish_reason",
        "three_step_cot_first_pass_api_error",
        "three_step_cot_first_pass_raw_response",
        "three_step_cot_first_pass_raw_json",
        "three_step_cot_raw_response",
        "three_step_cot_raw_json",
        "normal_cot_prompt_chars",
        "normal_cot_api_success",
        "normal_cot_http_status",
        "normal_cot_finish_reason",
        "normal_cot_api_error",
        "normal_cot_attempts_used",
        "normal_cot_retry_count",
        "normal_cot_choice_value",
        "normal_cot_made_choice",
        "normal_cot_decision",
        "normal_cot_reason",
        "normal_cot_has_json",
        "normal_cot_choice_parse_status",
        "normal_cot_first_pass_choice_value",
        "normal_cot_first_pass_made_choice",
        "normal_cot_first_pass_decision",
        "normal_cot_first_pass_reason",
        "normal_cot_first_pass_has_json",
        "normal_cot_first_pass_choice_parse_status",
        "normal_cot_has_explicit_choice",
        "normal_cot_first_pass_has_explicit_choice",
        "normal_cot_response_chars",
        "normal_cot_first_pass_response_chars",
        "normal_cot_refusal_flag",
        "normal_cot_first_pass_refusal_flag",
        "normal_cot_has_step1",
        "normal_cot_has_step2",
        "normal_cot_has_step3",
        "normal_cot_mentions_a1_a4",
        "normal_cot_first_pass_has_step1",
        "normal_cot_first_pass_has_step2",
        "normal_cot_first_pass_has_step3",
        "normal_cot_first_pass_mentions_a1_a4",
        "normal_cot_first_pass_http_status",
        "normal_cot_first_pass_finish_reason",
        "normal_cot_first_pass_api_error",
        "normal_cot_first_pass_raw_response",
        "normal_cot_first_pass_raw_json",
        "normal_cot_raw_response",
        "normal_cot_raw_json",
        "choice_agree_between_variants",
        "first_pass_choice_agree_between_variants",
    ]

    processed_normal = 0
    skipped = 0
    for i, row in enumerate(ref_rows, 1):
        idx = _int(row.get("idx", -1), -1)
        if idx < 0:
            continue

        if idx in existing_normal and not _normal_needs_retry(existing_normal[idx]):
            skipped += 1
            continue

        situation = str(row.get("emotional_situation", "") or "")
        action1 = str(row.get("action1", "") or "")
        action2 = str(row.get("action2", "") or "")
        if not situation or not action1 or not action2:
            continue

        logger.info(f"[{i}/{len(ref_rows)}] idx={idx} running normal CoT once...")
        normal = _build_normal_block(model_name, situation, action1, action2)

        normal_rec = {
            "idx": str(idx),
            "model": model_name,
            "dataset": dataset,
            "emotional_situation": situation,
            "action1": action1,
            "action2": action2,
        }
        for k, v in normal.items():
            normal_rec["normal_cot_" + k] = v
        save_result_incremental(
            normal_output,
            normal_rec,
            normal_fieldnames,
            overwrite_existing=(idx in existing_normal),
        )
        processed_normal += 1
        time.sleep(sleep_seconds)

    normal_cache = load_existing_results(normal_output)
    ref_idx_set = {_int(r.get("idx", -1), -1) for r in ref_rows}
    run_outputs: List[str] = []
    for run_id, three_step_file in three_step_runs:
        with open(three_step_file, "r", encoding="utf-8") as f:
            run_rows = _select_rows(list(csv.DictReader(f)), start, end, limit)
        run_rows = [r for r in run_rows if _int(r.get("idx", -1), -1) in ref_idx_set]

        merged_rows: List[dict] = []
        missing_normal = 0
        for row in run_rows:
            idx = _int(row.get("idx", -1), -1)
            if idx < 0:
                continue
            normal_row = normal_cache.get(idx)
            if not normal_row:
                missing_normal += 1
                continue

            three = _build_three_step_block(row)
            rec = {
                "idx": str(idx),
                "model": model_name,
                "dataset": dataset,
                "emotional_situation": str(row.get("emotional_situation", "") or ""),
                "action1": str(row.get("action1", "") or ""),
                "action2": str(row.get("action2", "") or ""),
            }
            for k, v in three.items():
                rec["three_step_cot_" + k] = v
            for k in normal_fieldnames:
                if k.startswith("normal_cot_"):
                    rec[k] = normal_row.get(k, "")
            rec["choice_agree_between_variants"] = _choice_agreement_flag(
                rec["three_step_cot_choice_value"],
                rec["normal_cot_choice_value"],
            )
            rec["first_pass_choice_agree_between_variants"] = _choice_agreement_flag(
                rec["three_step_cot_first_pass_choice_value"],
                rec["normal_cot_first_pass_choice_value"],
            )
            merged_rows.append(rec)

        suffix = f"{dataset}_run{run_id}"
        detailed_output = os.path.join(OUTPUT_DIR, f"cot_prompt_comparison_{suffix}.csv")
        summary_output = os.path.join(OUTPUT_DIR, f"cot_prompt_summary_{suffix}.csv")
        rescue_output = os.path.join(OUTPUT_DIR, f"cot_prompt_rescue_breakdown_{suffix}.csv")
        contingency_output = os.path.join(OUTPUT_DIR, f"cot_prompt_choice_contingency_{suffix}.csv")
        made_choice_analysis_output = os.path.join(OUTPUT_DIR, f"cot_prompt_made_choice_analysis_{suffix}.csv")
        choice_consistency_output = os.path.join(OUTPUT_DIR, f"cot_prompt_choice_consistency_analysis_{suffix}.csv")

        _write_records(detailed_output, merged_rows, fieldnames)
        _write_analysis_outputs(
            merged_rows,
            summary_output,
            rescue_output,
            contingency_output,
            made_choice_analysis_output,
            choice_consistency_output,
        )
        _log_analysis_results(f"{dataset} run{run_id}", merged_rows)
        logger.info(
            "[%s run%s] merged_rows=%s, missing_normal_rows=%s",
            dataset,
            run_id,
            len(merged_rows),
            missing_normal,
        )
        run_outputs.append(detailed_output)

    # Backward-compatible combined file for this dataset (concat run-wise records).
    combined_detailed = os.path.join(OUTPUT_DIR, f"cot_prompt_comparison_{dataset}.csv")
    combined_rows: List[dict] = []
    for path in run_outputs:
        if not os.path.isfile(path):
            continue
        with open(path, "r", encoding="utf-8") as f:
            combined_rows.extend(list(csv.DictReader(f)))
    _write_records(combined_detailed, combined_rows, fieldnames)

    summary_output = os.path.join(OUTPUT_DIR, f"cot_prompt_summary_{dataset}.csv")
    rescue_output = os.path.join(OUTPUT_DIR, f"cot_prompt_rescue_breakdown_{dataset}.csv")
    contingency_output = os.path.join(OUTPUT_DIR, f"cot_prompt_choice_contingency_{dataset}.csv")
    made_choice_analysis_output = os.path.join(OUTPUT_DIR, f"cot_prompt_made_choice_analysis_{dataset}.csv")
    choice_consistency_output = os.path.join(OUTPUT_DIR, f"cot_prompt_choice_consistency_analysis_{dataset}.csv")
    _write_analysis_outputs(
        combined_rows,
        summary_output,
        rescue_output,
        contingency_output,
        made_choice_analysis_output,
        choice_consistency_output,
    )
    _log_analysis_results(f"{dataset} combined", combined_rows)
    _refresh_overall_analysis()

    elapsed = int(time.time() - start_time)
    logger.info(
        "Done. Processed normal rows=%s, skipped_existing=%s, three_step_runs=%s, elapsed=%ss",
        processed_normal,
        skipped,
        len(three_step_runs),
        elapsed,
    )
    logger.info(f"Saved normal-only cache: {normal_output}")
    logger.info(f"Saved combined merged detailed: {combined_detailed}")
    logger.info(f"Saved summary: {summary_output}")
    logger.info(f"Saved rescue breakdown: {rescue_output}")
    logger.info(f"Saved contingency: {contingency_output}")
    logger.info(f"Saved made_choice analysis: {made_choice_analysis_output}")
    logger.info(f"Saved choice consistency analysis: {choice_consistency_output}")


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler()],
    )
    parser = argparse.ArgumentParser(
        description="Run normal CoT only, compare against existing three-step EA outputs."
    )
    parser.add_argument("dataset", choices=["CN", "CT", "R1", "V3"])
    parser.add_argument("--start", type=int, default=0)
    parser.add_argument("--end", type=int, default=0)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--sleep-seconds", type=float, default=1.0)
    args = parser.parse_args()

    get_api_key(DATASET_MODEL_MAP[args.dataset])
    process_dataset(args.dataset, args.start, args.end, args.limit, args.sleep_seconds)


if __name__ == "__main__":
    main()
