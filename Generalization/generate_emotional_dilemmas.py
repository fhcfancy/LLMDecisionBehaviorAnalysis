import csv
import json
import os
import time
from typing import Any

import pandas as pd
import requests


API_URL = "https://api2.aigcbest.top/v1/chat/completions"
INPUT_CSV = "/Users/carina/Documents/MyResearch/Professional/DataAnalysis/Dilemma/NeutralDilemma.csv"
OUTPUT_DIR = "/Users/carina/Documents/MyResearch/Professional/DataAnalysis/Generalization/generated_emotional_dilemmas"
MODEL_OUTPUT_NAMES = {
    "gpt-5-chat-latest": "GPT_5",
    "o4-mini": "GPT_o4",
}
MAX_RETRIES = 5


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Trim messy CSV headers and drop empty unnamed columns."""
    df.columns = [str(col).strip() for col in df.columns]
    keep_cols = [c for c in df.columns if c and not c.lower().startswith("unnamed")]
    return df[keep_cols].copy()


def extract_content(model_content: Any) -> str:
    """Handle string or list-style message content."""
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
    """Remove markdown fences and parse JSON safely."""
    cleaned = raw_output.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:].strip()
    return json.loads(cleaned)


def build_prompt(idx: Any, source_text: str) -> str:
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


def call_model(api_key: str, model_name: str, prompt: str) -> dict:
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }
    payload = {
        "model": model_name,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 1000,
        "temperature": 0.7,
    }
    response = requests.post(API_URL, headers=headers, json=payload, timeout=120)
    response.raise_for_status()
    body = response.json()
    content = body["choices"][0]["message"]["content"]
    raw_text = extract_content(content)
    return parse_json_from_model_output(raw_text)


def get_source_column(df: pd.DataFrame) -> str:
    if "dilemma_situation" in df.columns:
        return "dilemma_situation"
    if "emotional_situation" in df.columns:
        return "emotional_situation"
    raise ValueError(
        "Input CSV must include either 'dilemma_situation' or 'emotional_situation' column."
    )


def get_existing_idx(output_path: str) -> set[str]:
    if not os.path.isfile(output_path):
        return set()
    existing = set()
    with open(output_path, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if "idx" in row and row["idx"] is not None:
                existing.add(str(row["idx"]).strip())
    return existing


def run_generation(api_key: str) -> None:
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    df = pd.read_csv(INPUT_CSV)
    df = normalize_columns(df)
    if "idx" not in df.columns:
        raise ValueError("Input CSV must include an 'idx' column.")
    source_col = get_source_column(df)
    if "action1" not in df.columns or "action2" not in df.columns:
        raise ValueError("Input CSV must include 'action1' and 'action2' columns.")
    df = df.drop_duplicates(subset=["idx"]).copy()

    for model_name, output_prefix in MODEL_OUTPUT_NAMES.items():
        output_path = os.path.join(
            OUTPUT_DIR, f"{output_prefix}_emmotional_dilemma.csv"
        )
        processed_idx = get_existing_idx(output_path)
        file_exists = os.path.isfile(output_path)

        print(f"\n=== Generating with model: {model_name} ===")
        print(f"Output file: {output_path}")
        if processed_idx:
            print(f"Found {len(processed_idx)} existing rows. Will resume.")

        with open(output_path, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(["idx", "emotional_situation", "action1", "action2"])

            for _, row in df.iterrows():
                idx = str(row["idx"]).strip()
                if idx in processed_idx:
                    continue

                source_text = str(row[source_col]).strip()
                action1 = str(row["action1"]).strip()
                action2 = str(row["action2"]).strip()
                prompt = build_prompt(idx=idx, source_text=source_text)

                retries = 0
                while retries < MAX_RETRIES:
                    try:
                        result = call_model(api_key, model_name, prompt)
                        emotional_situation = result["emotional_situation"]

                        writer.writerow([idx, emotional_situation, action1, action2])
                        f.flush()

                        processed_idx.add(idx)
                        print(f"[{model_name}] Processed idx={idx}")
                        break
                    except (
                        requests.exceptions.RequestException,
                        json.JSONDecodeError,
                        KeyError,
                        ValueError,
                    ) as exc:
                        retries += 1
                        print(
                            f"[{model_name}] Error for idx={idx}, attempt "
                            f"{retries}/{MAX_RETRIES}: {exc}"
                        )
                        time.sleep(2)
                else:
                    print(f"[{model_name}] Failed idx={idx} after {MAX_RETRIES} retries.")

    print("\nAll generation jobs finished.")


if __name__ == "__main__":
    # Recommended: export AIGCBEST_API_KEY='your_key' before running.
    api_key = os.getenv("AIGCBEST_API_KEY", "")
    if not api_key:
        raise ValueError("Missing API key. Set environment variable AIGCBEST_API_KEY.")

    run_generation(api_key)
