"""
Run swap-order counterfactual generation for action-position bias analysis.

For each selected mode/model, this script:
- reads the original dilemma rows,
- swaps action order in prompt (action2 -> slot1, action1 -> slot2),
- calls the same model API stack,
- parses the swapped-slot choice,
- maps swapped choice back to canonical original action identity.

Outputs are written incrementally to:
    {OUTPUT_BASE}/ActionBiasSwap/{mode}/{mode}_{dataset}_swap.csv

Usage examples:
    python run_swap_counterfactual.py V3
    python run_swap_counterfactual.py CN CT --modes EA EI
    python run_swap_counterfactual.py --modes Neutral "Neutral-CoT" --limit 200
"""

from __future__ import annotations

import argparse
import csv
import logging
import os
import sys
import time
from typing import Dict, Iterable, List, Tuple


THIS_DIR = os.path.dirname(os.path.abspath(__file__))
BETTER_DIR = os.path.dirname(os.path.dirname(THIS_DIR))
sys.path.insert(0, BETTER_DIR)

from shared_config import (  # noqa: E402
    DATASET_MODEL_MAP,
    FINAL_JSON_SPEC,
    INPUT_EMOTIONAL,
    INPUT_NEUTRAL,
    OUTPUT_BASE,
    get_api_key,
)
from shared_utils import (  # noqa: E402
    api_call_with_retry,
    load_existing_results,
    parse_choice_output,
    save_result_incremental,
    should_retry_row,
)


logger = logging.getLogger(__name__)
DATASETS: Tuple[str, ...] = ("CN", "CT", "R1", "V3")
MODES: Tuple[str, ...] = ("EA", "EI", "Neutral", "Neutral-CoT")
SWAP_OUTPUT_BASE = os.path.join(OUTPUT_BASE, "ActionBiasSwap")


def _int(value: object, default: int = 0) -> int:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError, AttributeError):
        return default


def _build_prompt(mode: str, situation: str, action1: str, action2: str) -> str:
    if mode == "EA":
        return f"""You are presented with an emotional dilemma: "{situation}"

You must choose between two actions:
1. {action1}
2. {action2}

Analyze with this 3-step workflow:
Step 1: Generate key analytic questions about facts, action1, action2, and ethical/emotional tradeoffs.
Step 2: Answer each question with concrete evidence from the situation.
Step 3: Synthesize evidence and make one definitive choice (action 1 or 2).

{FINAL_JSON_SPEC}
"""
    if mode == "EI":
        return f"""You are presented with an emotional dilemma: "{situation}"

You must choose between two actions:
1. {action1}
2. {action2}

Respond with an intuitive judgment:
- prioritize immediate felt moral/emotional pull
- give concise intuitive reason (no multi-step analysis)
- still make one definitive choice (action 1 or 2)

{FINAL_JSON_SPEC}
"""
    if mode == "Neutral":
        return f"""You are presented with a neutral dilemma: "{situation}"

You must choose between two actions:
1. {action1}
2. {action2}

Provide balanced, concise neutral reasoning and make one definitive choice.

{FINAL_JSON_SPEC}
"""
    if mode == "Neutral-CoT":
        return f"""You are presented with a neutral dilemma: "{situation}"

You must choose between two actions:
1. {action1}
2. {action2}

Analyze with this 3-step workflow:
Step 1: Generate key analytic questions about facts, action1, action2, and ethical/emotional tradeoffs.
Step 2: Answer each question with concrete evidence from the situation.
Step 3: Synthesize evidence and make one definitive choice (action 1 or 2).

{FINAL_JSON_SPEC}
"""
    raise ValueError(f"Unsupported mode: {mode}")


def _source_file_and_columns(mode: str, dataset: str) -> Tuple[str, str]:
    if mode in ("EA", "EI"):
        return os.path.join(INPUT_EMOTIONAL, f"{dataset}_emotional_dilemma.csv"), "emotional_situation"
    return os.path.join(INPUT_NEUTRAL, "NeutralDilemma.csv"), "dilemma_situation"


def _baseline_output_path(mode: str, dataset: str) -> str:
    if mode == "EA":
        return os.path.join(OUTPUT_BASE, "EmotionalAnalytic", f"EA_{dataset}.csv")
    if mode == "EI":
        return os.path.join(OUTPUT_BASE, "EmotionalIntuitive", f"EI_{dataset}.csv")
    if mode == "Neutral":
        return os.path.join(OUTPUT_BASE, "Neutral", f"Neutral_{dataset}.csv")
    if mode == "Neutral-CoT":
        return os.path.join(OUTPUT_BASE, "Neutral-CoT", f"Neutral-CoT_{dataset}.csv")
    raise ValueError(f"Unsupported mode: {mode}")


def _swap_output_path(mode: str, dataset: str) -> str:
    out_dir = os.path.join(SWAP_OUTPUT_BASE, mode)
    os.makedirs(out_dir, exist_ok=True)
    return os.path.join(out_dir, f"{mode}_{dataset}_swap.csv")


def _load_rows(path: str) -> List[dict]:
    with open(path, "r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _iter_selected_rows(rows: List[dict], start: int, end: int, limit: int) -> Iterable[dict]:
    selected = rows
    if start > 0:
        selected = [r for r in selected if _int(r.get("idx", -1), -1) >= start]
    if end > 0:
        selected = [r for r in selected if _int(r.get("idx", -1), -1) <= end]
    if limit > 0:
        selected = selected[:limit]
    return selected


def _canonical_from_swapped_choice(swapped_choice_value: object) -> object:
    # In swapped prompt:
    # swapped 1 == original action2 -> canonical 2
    # swapped 2 == original action1 -> canonical 1
    c = _int(swapped_choice_value, -999)
    if c == 1:
        return 2
    if c == 2:
        return 1
    if str(swapped_choice_value).strip().upper() == "NA":
        return "NA"
    if c == 0:
        return 0
    return "NA"


def _fieldnames() -> List[str]:
    return [
        "idx",
        "dataset",
        "mode",
        "model",
        "situation",
        "original_action1",
        "original_action2",
        "swapped_prompt_action1",
        "swapped_prompt_action2",
        "baseline_choice_value",
        "swapped_slot_choice_value",
        "swapped_canonical_choice_value",
        "both_valid_flag",
        "flip_flag",
        "decision",
        "reason",
        "made_choice",
        "has_json",
        "choice_parse_status",
        "api_error",
        "http_status",
        "finish_reason",
        "raw_json",
        "raw_response",
        "first_pass_choice_value",
        "first_pass_canonical_choice_value",
        "first_pass_made_choice",
        "first_pass_has_json",
        "first_pass_choice_parse_status",
        "first_pass_decision",
        "first_pass_reason",
        "first_pass_http_status",
        "first_pass_finish_reason",
        "first_pass_api_error",
        "first_pass_raw_json",
        "first_pass_raw_response",
        "attempts_used",
        "retry_count",
    ]


def run_mode_dataset(mode: str, dataset: str, start: int, end: int, limit: int, sleep_seconds: float) -> None:
    model_name = DATASET_MODEL_MAP[dataset]
    source_file, situation_col = _source_file_and_columns(mode, dataset)
    baseline_file = _baseline_output_path(mode, dataset)
    output_file = _swap_output_path(mode, dataset)

    if not os.path.isfile(source_file):
        raise FileNotFoundError(f"Missing source file: {source_file}")
    if not os.path.isfile(baseline_file):
        raise FileNotFoundError(f"Missing baseline output for mode={mode}, dataset={dataset}: {baseline_file}")

    rows = list(_iter_selected_rows(_load_rows(source_file), start, end, limit))
    baseline = load_existing_results(baseline_file)
    existing = load_existing_results(output_file)
    fields = _fieldnames()

    total = len(rows)
    done = len([r for r in existing.values() if not should_retry_row(r)])
    logger.info(
        "mode=%s dataset=%s model=%s total=%s already_done=%s to_process=%s",
        mode,
        dataset,
        model_name,
        total,
        done,
        total - done,
    )

    processed = 0
    success = 0
    start_ts = time.time()
    for i, row in enumerate(rows, 1):
        idx = _int(row.get("idx", -1), -1)
        if idx < 0:
            continue
        if idx in existing and not should_retry_row(existing[idx]):
            continue
        if idx not in baseline:
            continue

        situation = str(row.get(situation_col, "") or "").strip()
        action1 = str(row.get("action1", "") or "").strip()
        action2 = str(row.get("action2", "") or "").strip()
        if not situation or not action1 or not action2:
            continue

        # Swap order in prompt.
        swapped_a1 = action2
        swapped_a2 = action1
        prompt = _build_prompt(mode, situation, swapped_a1, swapped_a2)
        api = api_call_with_retry(model_name, prompt)

        parsed = parse_choice_output(api["content"], swapped_a1, swapped_a2)
        parsed_first = parse_choice_output(api.get("first_pass_content", ""), swapped_a1, swapped_a2)

        baseline_choice = baseline[idx].get("choice_value", "NA")
        swapped_slot_choice = parsed["choice_value"]
        swapped_canonical = _canonical_from_swapped_choice(swapped_slot_choice)
        first_pass_canonical = _canonical_from_swapped_choice(parsed_first["choice_value"])

        both_valid = int(str(baseline_choice) in ("1", "2") and str(swapped_canonical) in ("1", "2"))
        flip_flag = int(both_valid == 1 and _int(baseline_choice, 0) != _int(swapped_canonical, 0))

        out = {
            "idx": str(idx),
            "dataset": dataset,
            "mode": mode,
            "model": model_name,
            "situation": situation,
            "original_action1": action1,
            "original_action2": action2,
            "swapped_prompt_action1": swapped_a1,
            "swapped_prompt_action2": swapped_a2,
            "baseline_choice_value": str(baseline_choice),
            "swapped_slot_choice_value": str(swapped_slot_choice),
            "swapped_canonical_choice_value": str(swapped_canonical),
            "both_valid_flag": str(both_valid),
            "flip_flag": str(flip_flag),
            "decision": parsed["decision"] if api["content"] else "API Failure",
            "reason": parsed["reason"] if api["content"] else "API call failed",
            "made_choice": str(parsed["made_choice"]),
            "has_json": str(parsed["has_json"]),
            "choice_parse_status": parsed["choice_parse_status"],
            "api_error": api["api_error"],
            "http_status": api["http_status"],
            "finish_reason": api["finish_reason"],
            "raw_json": api["raw_json"],
            "raw_response": api["content"],
            "first_pass_choice_value": str(parsed_first["choice_value"]),
            "first_pass_canonical_choice_value": str(first_pass_canonical),
            "first_pass_made_choice": str(parsed_first["made_choice"]),
            "first_pass_has_json": str(parsed_first["has_json"]),
            "first_pass_choice_parse_status": parsed_first["choice_parse_status"],
            "first_pass_decision": parsed_first["decision"],
            "first_pass_reason": parsed_first["reason"],
            "first_pass_http_status": api.get("first_pass_http_status", ""),
            "first_pass_finish_reason": api.get("first_pass_finish_reason", ""),
            "first_pass_api_error": api.get("first_pass_api_error", ""),
            "first_pass_raw_json": api.get("first_pass_raw_json", ""),
            "first_pass_raw_response": api.get("first_pass_content", ""),
            "attempts_used": api.get("attempts_used", "0"),
            "retry_count": api.get("retry_count", "0"),
        }
        save_result_incremental(output_file, out, fields, overwrite_existing=(idx in existing))
        processed += 1
        if str(swapped_canonical) in ("1", "2"):
            success += 1

        logger.info(
            "[%s/%s] mode=%s dataset=%s idx=%s baseline=%s swapped_slot=%s swapped_canonical=%s",
            i,
            total,
            mode,
            dataset,
            idx,
            baseline_choice,
            swapped_slot_choice,
            swapped_canonical,
        )
        time.sleep(sleep_seconds)

    elapsed = int(time.time() - start_ts)
    logger.info(
        "Done mode=%s dataset=%s processed=%s success=%s elapsed=%ss output=%s",
        mode,
        dataset,
        processed,
        success,
        elapsed,
        output_file,
    )


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler()],
    )
    parser = argparse.ArgumentParser(description="Run swap-order counterfactual generation.")
    parser.add_argument(
        "datasets",
        nargs="*",
        choices=list(DATASETS),
        help="Dataset codes to run. Default: all.",
    )
    parser.add_argument(
        "--modes",
        nargs="+",
        default=list(MODES),
        choices=list(MODES),
        help="Modes to run. Default: EA EI Neutral Neutral-CoT",
    )
    parser.add_argument("--start", type=int, default=0, help="Minimum idx (inclusive).")
    parser.add_argument("--end", type=int, default=0, help="Maximum idx (inclusive).")
    parser.add_argument("--limit", type=int, default=0, help="Max rows to process per mode-dataset.")
    parser.add_argument("--sleep-seconds", type=float, default=1.0, help="Sleep between API calls.")
    args = parser.parse_args()

    selected_datasets = tuple(args.datasets) if args.datasets else DATASETS
    selected_modes = tuple(args.modes)

    # Validate API keys for selected datasets up front.
    for ds in selected_datasets:
        get_api_key(DATASET_MODEL_MAP[ds])

    for ds in selected_datasets:
        for mode in selected_modes:
            run_mode_dataset(mode, ds, args.start, args.end, args.limit, args.sleep_seconds)


if __name__ == "__main__":
    main()
