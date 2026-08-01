#!/usr/bin/env python3
"""
Convert ActionBiasSwap outputs into first-run-compatible CSV schema.

Input folders:
  - ActionBiasSwap/EA
  - ActionBiasSwap/EI
  - ActionBiasSwap/Neutral
  - ActionBiasSwap/Neutral-CoT

Output folders:
  - decisions/EmotionalAnalytic
  - decisions/EmotionalIntuitive
  - decisions/Neutral
  - decisions/Neutral-CoT

Output filename format:
  Mode_Model_Number.csv
  e.g. EA_CN_2.csv
"""

from __future__ import annotations

import argparse
from pathlib import Path
import pandas as pd


ROOT = Path("/Users/carina/Documents/MyResearch/Professional/DataAnalysis/Better/decisions")
SOURCE_ROOT = ROOT / "ActionBiasSwap"

FOLDER_MAP = {
    "EA": {
        "target_dir": "EmotionalAnalytic",
        "mode_prefix": "EA",
        "situation_target_col": "emotional_situation",
        "prompt_type": "three_step_cot",
    },
    "EI": {
        "target_dir": "EmotionalIntuitive",
        "mode_prefix": "EI",
        "situation_target_col": "emotional_situation",
        "prompt_type": "intuitive",
    },
    "Neutral": {
        "target_dir": "Neutral",
        "mode_prefix": "Neutral",
        "situation_target_col": "dilemma_situation",
        "prompt_type": "neutral",
    },
    "Neutral-CoT": {
        "target_dir": "Neutral-CoT",
        "mode_prefix": "Neutral-CoT",
        "situation_target_col": "dilemma_situation",
        "prompt_type": "three_step_cot",
    },
}

# First-run-compatible column order.
OUTPUT_COLUMNS = [
    "idx",
    "SITUATION_COL_PLACEHOLDER",
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


def build_output_name(mode_prefix: str, model: str, run_number: int) -> str:
    return f"{mode_prefix}_{model}_{run_number}.csv"


def convert_one_file(
    source_csv: Path,
    mode_key: str,
    target_dir: Path,
    run_number: int,
) -> Path:
    cfg = FOLDER_MAP[mode_key]
    df = pd.read_csv(source_csv)

    # Core field mapping requested by user.
    df["action1"] = df["original_action1"]
    df["action2"] = df["original_action2"]
    df["choice_value"] = df["swapped_canonical_choice_value"]
    df[cfg["situation_target_col"]] = df["situation"]
    df["prompt_type"] = cfg["prompt_type"]

    # Ensure first-pass choice value is canonical if the canonical column exists.
    if "first_pass_canonical_choice_value" in df.columns:
        df["first_pass_choice_value"] = df["first_pass_canonical_choice_value"]

    # Keep only first-run-style columns in the expected order.
    final_cols = [
        c if c != "SITUATION_COL_PLACEHOLDER" else cfg["situation_target_col"]
        for c in OUTPUT_COLUMNS
    ]
    out_df = df.reindex(columns=final_cols)

    model = str(df["dataset"].iloc[0]).strip()
    out_name = build_output_name(cfg["mode_prefix"], model, run_number)
    out_path = target_dir / out_name
    out_df.to_csv(out_path, index=False)
    return out_path


def run_conversion(run_number: int) -> list[Path]:
    outputs: list[Path] = []
    for mode_key, cfg in FOLDER_MAP.items():
        source_dir = SOURCE_ROOT / mode_key
        target_dir = ROOT / cfg["target_dir"]
        if not source_dir.exists():
            continue
        for source_csv in sorted(source_dir.glob("*_swap.csv")):
            out_path = convert_one_file(
                source_csv=source_csv,
                mode_key=mode_key,
                target_dir=target_dir,
                run_number=run_number,
            )
            outputs.append(out_path)
    return outputs


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert ActionBiasSwap files into first-run-compatible second-run CSVs."
    )
    parser.add_argument(
        "--run-number",
        type=int,
        default=2,
        help="Number suffix for output files (default: 2).",
    )
    args = parser.parse_args()

    outputs = run_conversion(run_number=args.run_number)
    if not outputs:
        print("No swap files found. Nothing was written.")
        return

    print(f"Wrote {len(outputs)} files:")
    for p in outputs:
        print(f"- {p}")


if __name__ == "__main__":
    main()
