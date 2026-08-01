"""
EA generator:
- keeps 3-step reasoning logic
- uses aligned technical stack from Better/shared_*
"""

from __future__ import annotations

import argparse
import csv
import logging
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared_config import DATASET_MODEL_MAP, FINAL_JSON_SPEC, INPUT_EMOTIONAL, OUTPUT_BASE, get_api_key
from shared_utils import (
    api_call_with_retry,
    load_existing_results,
    parse_choice_output,
    save_result_incremental,
    should_retry_row,
)


logger = logging.getLogger(__name__)
OUTPUT_DIR = os.path.join(OUTPUT_BASE, "EmotionalAnalytic")


def construct_prompt(situation: str, action1: str, action2: str) -> str:
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


def process_file(dataset: str, input_file: str, output_file: str) -> None:
    model_name = DATASET_MODEL_MAP[dataset]
    with open(input_file, "r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    fieldnames = [
        "idx",
        "emotional_situation",
        "action1",
        "action2",
        "decision",
        "choice_value",
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
        "prompt_type",
    ]
    existing = load_existing_results(output_file)
    total = len(rows)
    done = len([r for r in existing.values() if not should_retry_row(r)])
    logger.info(f"Total: {total} | Already processed: {done} | To process: {total - done}")

    processed = 0
    success = 0
    start = time.time()
    for i, row in enumerate(rows, 1):
        idx = int(row.get("idx", -1))
        if idx < 0:
            continue
        if idx in existing and not should_retry_row(existing[idx]):
            continue

        situation = row.get("emotional_situation", "")
        action1 = row.get("action1", "")
        action2 = row.get("action2", "")
        if not situation or not action1 or not action2:
            continue

        to_do = total - done
        logger.info(f"[{processed + 1}/{to_do}] idx={idx} with {model_name} (EA)...")
        prompt = construct_prompt(situation, action1, action2)
        api = api_call_with_retry(model_name, prompt)
        parsed = parse_choice_output(api["content"], action1, action2)
        first_pass_parsed = parse_choice_output(api.get("first_pass_content", ""), action1, action2)

        if api["content"] and str(parsed["choice_value"]) in ("1", "2"):
            logger.info(f"  -> OK (choice={parsed['choice_value']})")
        else:
            attempts = api.get("attempts_used", "?")
            err = (api.get("api_error") or "API failure")[:60]
            logger.warning(f"  -> FAIL (attempts={attempts}) {err}")

        out = {
            "idx": str(idx),
            "emotional_situation": situation,
            "action1": action1,
            "action2": action2,
            "decision": parsed["decision"] if api["content"] else "API Failure",
            "choice_value": str(parsed["choice_value"]),
            "reason": parsed["reason"] if api["content"] else "API call failed",
            "made_choice": str(parsed["made_choice"]),
            "has_json": str(parsed["has_json"]),
            "choice_parse_status": parsed["choice_parse_status"],
            "api_error": api["api_error"],
            "http_status": api["http_status"],
            "finish_reason": api["finish_reason"],
            "raw_json": api["raw_json"],
            "raw_response": api["content"],
            "first_pass_choice_value": str(first_pass_parsed["choice_value"]),
            "first_pass_made_choice": str(first_pass_parsed["made_choice"]),
            "first_pass_has_json": str(first_pass_parsed["has_json"]),
            "first_pass_choice_parse_status": first_pass_parsed["choice_parse_status"],
            "first_pass_decision": first_pass_parsed["decision"],
            "first_pass_reason": first_pass_parsed["reason"],
            "first_pass_http_status": api.get("first_pass_http_status", ""),
            "first_pass_finish_reason": api.get("first_pass_finish_reason", ""),
            "first_pass_api_error": api.get("first_pass_api_error", ""),
            "first_pass_raw_json": api.get("first_pass_raw_json", ""),
            "first_pass_raw_response": api.get("first_pass_content", ""),
            "attempts_used": api.get("attempts_used", "0"),
            "retry_count": api.get("retry_count", "0"),
            "prompt_type": "three_step_cot",
        }
        save_result_incremental(output_file, out, fieldnames, overwrite_existing=(idx in existing))
        processed += 1
        if str(parsed["choice_value"]) in ("1", "2"):
            success += 1
        if processed % 25 == 0 and processed > 0:
            elapsed = int(time.time() - start)
            fail = processed - success
            logger.info(f"  --- Progress: {processed} done | {success} ok, {fail} fail | {elapsed}s elapsed")
        time.sleep(1)

    elapsed = int(time.time() - start)
    logger.info(f"Done. Processed: {processed}, Success: {success}, Fail: {processed - success}, Time: {elapsed}s")


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler()],
    )
    parser = argparse.ArgumentParser(description="Emotional Analytic decision generator")
    parser.add_argument("dataset", choices=["CN", "CT", "R1", "V3"])
    args = parser.parse_args()

    input_file = os.path.join(INPUT_EMOTIONAL, f"{args.dataset}_emotional_dilemma.csv")
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    output_file = os.path.join(OUTPUT_DIR, f"EA_{args.dataset}.csv")

    get_api_key(DATASET_MODEL_MAP[args.dataset])
    process_file(args.dataset, input_file, output_file)
    logger.info(f"Output: {output_file}")


if __name__ == "__main__":
    main()
