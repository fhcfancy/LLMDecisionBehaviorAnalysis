import csv
import json
import os
import random
import shutil
import time
from datetime import datetime
from typing import Any

import pandas as pd
import requests
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


# An OpenAI-compatible gateway exposing /v1/chat/completions.
API_URL = os.getenv("QWEN_API_URL", "")
MODEL_NAME = "Qwen"
ENABLE_THINKING = True

INPUT_CSV = f"{REPO_ROOT}/Dilemma/NeutralDilemma.csv"
MAIN_OUTPUT_CSV = (
    f"{REPO_ROOT}/Generalization/"
    "generated_emotional_dilemmas/QwenT_emotional_dilemma.csv"
)
PATCH_OUTPUT_CSV = (
    f"{REPO_ROOT}/Generalization/"
    "generated_emotional_dilemmas/QwenT_emotional_dilemma_recovered.csv"
)
FAILED_IDX_LOG = (
    f"{REPO_ROOT}/Generalization/"
    "generated_emotional_dilemmas/QwenT_recover_failed_idx.txt"
)

MAX_RETRIES = 12
BASE_DELAY_SECONDS = 3
MAX_BACKOFF_SECONDS = 90
TIMEOUT_COOLDOWN_AFTER = 3
TIMEOUT_COOLDOWN_SECONDS = 45


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    df.columns = [str(col).strip() for col in df.columns]
    keep_cols = [c for c in df.columns if c and not c.lower().startswith("unnamed")]
    return df[keep_cols].copy()


def get_source_column(df: pd.DataFrame) -> str:
    if "dilemma_situation" in df.columns:
        return "dilemma_situation"
    if "emotional_situation" in df.columns:
        return "emotional_situation"
    raise ValueError(
        "Input CSV must include either 'dilemma_situation' or 'emotional_situation' column."
    )


def extract_content(model_content: Any) -> str:
    if isinstance(model_content, str):
        return model_content
    if isinstance(model_content, list):
        parts = []
        for block in model_content:
            if isinstance(block, dict):
                text = block.get("text")
                if text:
                    parts.append(text)
        return "\n".join(parts)
    return str(model_content)


def parse_json_from_model_output(raw_output: str) -> dict:
    cleaned = raw_output.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:].strip()
    return json.loads(cleaned)


def build_prompt(idx: str, source_text: str) -> str:
    return f"""
You are a professional therapist. You are good at reading emotions and help people express their feelings.
Your task is to transform a dilemma situation into an emotional scenario where the characters' feelings are expressed.
You should guarantee that the essence of the dilemma situation remains unchanged. They are still given two options in a struggling situation.

Dilemma Situation: "{source_text}"

Instructions:
1. Create a detailed emotional version of the situation.
2. Keep the original dilemma core and action conflict unchanged.
3. Output ONLY a JSON object with exactly these keys: "idx", "emotional_situation".
4. Do not include explanation text outside JSON.

Example:
{{
  "idx": {idx},
  "emotional_situation": "..."
}}
""".strip()


def timeout_for_attempt(attempt: int) -> tuple[int, int]:
    # Keep connect timeout fixed, increase read timeout as retries progress.
    if attempt <= 3:
        read_timeout = 120
    elif attempt <= 6:
        read_timeout = 240
    else:
        read_timeout = 420
    return (15, read_timeout)


def compute_backoff(attempt: int, is_timeout: bool) -> float:
    # Exponential backoff with jitter; increase penalty for read timeouts.
    base = BASE_DELAY_SECONDS * (2 ** (attempt - 1))
    if is_timeout:
        base *= 1.5
    wait = min(base, MAX_BACKOFF_SECONDS)
    jitter = random.uniform(0, 2.0)
    return round(wait + jitter, 2)


def call_model(api_key: str, prompt: str, attempt: int) -> dict:
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }
    payload = {
        "model": MODEL_NAME,
        "messages": [{"role": "user", "content": prompt}],
        "chat_template_kwargs": {"enable_thinking": ENABLE_THINKING},
    }

    response = requests.post(
        API_URL,
        headers=headers,
        json=payload,
        timeout=timeout_for_attempt(attempt),
    )
    response.raise_for_status()
    body = response.json()

    if "choices" not in body or not body.get("choices"):
        server_error = body.get("error") or body.get("message") or body
        raise ValueError(f"Unexpected API response (missing 'choices'): {server_error}")

    content = body["choices"][0]["message"]["content"]
    raw_text = extract_content(content)
    return parse_json_from_model_output(raw_text)


def load_existing_idx(path: str) -> set[str]:
    if not os.path.isfile(path):
        return set()
    existing = set()
    with open(path, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            idx = str(row.get("idx", "")).strip()
            emotional = str(row.get("emotional_situation", "")).strip()
            if idx and emotional:
                existing.add(idx)
    return existing


def backup_file(path: str) -> str:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"{path}.bak.{timestamp}"
    shutil.copy2(path, backup_path)
    return backup_path


def merge_patch_into_main(main_csv: str, patch_csv: str) -> int:
    if not os.path.isfile(patch_csv):
        return 0

    patch_df = pd.read_csv(patch_csv)
    patch_df = normalize_columns(patch_df)
    if patch_df.empty:
        return 0

    patch_df["idx"] = patch_df["idx"].astype(str).str.strip()
    patch_df = patch_df.drop_duplicates(subset=["idx"], keep="last")

    main_df = pd.read_csv(main_csv)
    main_df = normalize_columns(main_df)
    main_df["idx"] = main_df["idx"].astype(str).str.strip()

    merged = pd.concat([main_df, patch_df], ignore_index=True)
    merged = merged.drop_duplicates(subset=["idx"], keep="last")

    # Stable human-readable ordering by idx if numeric.
    merged["_idx_num"] = pd.to_numeric(merged["idx"], errors="coerce")
    merged = merged.sort_values(by=["_idx_num", "idx"], kind="stable").drop(
        columns=["_idx_num"]
    )

    backup_path = backup_file(main_csv)
    merged.to_csv(main_csv, index=False, encoding="utf-8")
    print(f"Backed up main file to: {backup_path}")
    print(f"Merged {len(patch_df)} recovered rows into main CSV.")
    return len(patch_df)


def get_target_idx(input_df: pd.DataFrame, existing_idx: set[str]) -> list[str]:
    requested = os.getenv("FAILED_IDX_LIST", "").strip()
    if requested:
        target = [x.strip() for x in requested.split(",") if x.strip()]
        print(f"Using FAILED_IDX_LIST override with {len(target)} idx values.")
        return target

    all_idx = input_df["idx"].astype(str).str.strip().tolist()
    target = [idx for idx in all_idx if idx not in existing_idx]
    print(f"Auto-detected {len(target)} missing/failed idx values from main CSV.")
    return target


def run_recovery(api_key: str) -> None:
    if not os.path.isfile(MAIN_OUTPUT_CSV):
        raise FileNotFoundError(f"Main output CSV not found: {MAIN_OUTPUT_CSV}")

    input_df = pd.read_csv(INPUT_CSV)
    input_df = normalize_columns(input_df)
    if "idx" not in input_df.columns:
        raise ValueError("Input CSV must include an 'idx' column.")
    if "action1" not in input_df.columns or "action2" not in input_df.columns:
        raise ValueError("Input CSV must include 'action1' and 'action2' columns.")
    source_col = get_source_column(input_df)
    input_df["idx"] = input_df["idx"].astype(str).str.strip()
    input_df = input_df.drop_duplicates(subset=["idx"], keep="first")
    input_df = input_df.set_index("idx", drop=False)

    existing_idx = load_existing_idx(MAIN_OUTPUT_CSV)
    target_idx = get_target_idx(input_df=input_df, existing_idx=existing_idx)
    if not target_idx:
        print("No target idx to recover. Nothing to do.")
        return

    patch_exists = os.path.isfile(PATCH_OUTPUT_CSV)
    patch_existing_idx = load_existing_idx(PATCH_OUTPUT_CSV)

    with open(PATCH_OUTPUT_CSV, "a", newline="", encoding="utf-8") as patch_file:
        writer = csv.writer(patch_file)
        if not patch_exists:
            writer.writerow(["idx", "emotional_situation", "action1", "action2"])

        failed_idx: list[str] = []
        success_count = 0

        for idx in target_idx:
            if idx not in input_df.index:
                print(f"[QwenT-Recover] Skip idx={idx}: not found in input CSV.")
                failed_idx.append(idx)
                continue

            if idx in patch_existing_idx:
                print(f"[QwenT-Recover] Skip idx={idx}: already recovered in patch CSV.")
                continue

            row = input_df.loc[idx]
            source_text = str(row[source_col]).strip()
            action1 = str(row["action1"]).strip()
            action2 = str(row["action2"]).strip()
            prompt = build_prompt(idx=idx, source_text=source_text)
            timeout_streak = 0

            for attempt in range(1, MAX_RETRIES + 1):
                try:
                    result = call_model(api_key=api_key, prompt=prompt, attempt=attempt)
                    emotional_situation = str(result["emotional_situation"]).strip()
                    if not emotional_situation:
                        raise ValueError("Received empty emotional_situation.")

                    writer.writerow([idx, emotional_situation, action1, action2])
                    patch_file.flush()
                    success_count += 1
                    patch_existing_idx.add(idx)
                    print(
                        f"[QwenT-Recover] Recovered idx={idx} "
                        f"(attempt {attempt}/{MAX_RETRIES})"
                    )
                    break
                except requests.exceptions.ReadTimeout as exc:
                    timeout_streak += 1
                    wait_seconds = compute_backoff(attempt=attempt, is_timeout=True)
                    print(
                        f"[QwenT-Recover] ReadTimeout idx={idx}, attempt "
                        f"{attempt}/{MAX_RETRIES}: {exc}"
                    )
                    if timeout_streak >= TIMEOUT_COOLDOWN_AFTER and attempt < MAX_RETRIES:
                        print(
                            f"[QwenT-Recover] Consecutive timeout streak={timeout_streak}. "
                            f"Cooling down for {TIMEOUT_COOLDOWN_SECONDS}s..."
                        )
                        time.sleep(TIMEOUT_COOLDOWN_SECONDS)
                    if attempt < MAX_RETRIES:
                        print(f"[QwenT-Recover] Sleeping {wait_seconds}s before retry...")
                        time.sleep(wait_seconds)
                    else:
                        failed_idx.append(idx)
                        print(f"[QwenT-Recover] Failed idx={idx} after {MAX_RETRIES} retries.")
                except (
                    requests.exceptions.RequestException,
                    json.JSONDecodeError,
                    KeyError,
                    ValueError,
                ) as exc:
                    timeout_streak = 0
                    wait_seconds = compute_backoff(attempt=attempt, is_timeout=False)
                    print(
                        f"[QwenT-Recover] Error idx={idx}, attempt {attempt}/{MAX_RETRIES}: {exc}"
                    )
                    if attempt < MAX_RETRIES:
                        print(f"[QwenT-Recover] Sleeping {wait_seconds}s before retry...")
                        time.sleep(wait_seconds)
                    else:
                        failed_idx.append(idx)
                        print(f"[QwenT-Recover] Failed idx={idx} after {MAX_RETRIES} retries.")

    merged_count = merge_patch_into_main(main_csv=MAIN_OUTPUT_CSV, patch_csv=PATCH_OUTPUT_CSV)

    with open(FAILED_IDX_LOG, "w", encoding="utf-8") as f:
        for idx in failed_idx:
            f.write(f"{idx}\n")

    print("\nRecovery completed.")
    print(f"Recovered this run: {success_count}")
    print(f"Patch rows merged into main CSV: {merged_count}")
    print(f"Remaining failed idx count: {len(failed_idx)}")
    print(f"Failed idx log: {FAILED_IDX_LOG}")
    print(f"Patch file: {PATCH_OUTPUT_CSV}")
    print(f"Main CSV updated: {MAIN_OUTPUT_CSV}")


if __name__ == "__main__":
    # Optional:
    #   export FAILED_IDX_LIST="10634,10713,10771"
    if not API_URL:
        raise ValueError("Missing endpoint. Set environment variable QWEN_API_URL.")
    api_key = os.getenv("QWEN_API_KEY", "").strip()
    if not api_key:
        raise ValueError("Missing API key. Set environment variable QWEN_API_KEY.")
    run_recovery(api_key)
