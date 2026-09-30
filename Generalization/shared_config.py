"""
Aligned configuration for Generalization-mode generators.
"""

import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

# Input data produced by generalization dilemma builders.
INPUT_GENERALIZATION = (
    f"{REPO_ROOT}/Generalization/"
    "generated_emotional_dilemmas"
)

# Output base for generated decisions.
OUTPUT_BASE = f"{REPO_ROOT}/Generalization/decisions"

MODEL_CONFIGS = {
    "GPT_5": {
        "api_url": "https://api2.aigcbest.top/v1/chat/completions",
        "model_name": "gpt-5-chat-latest",
        "api_key_env": "AIGCBEST_API_KEY",
    },
    "GPT_o4": {
        "api_url": "https://api2.aigcbest.top/v1/chat/completions",
        "model_name": "o4-mini",
        "api_key_env": "AIGCBEST_API_KEY",
    },
    "QwenT": {
        "api_url": "https://aigc-api.hkust-gz.edu.cn/v1/chat/completions",
        "model_name": "Qwen",
        "api_key_env": "HKUST_API_KEY",
        "enable_thinking": True,
    },
    "QwenN": {
        "api_url": "https://aigc-api.hkust-gz.edu.cn/v1/chat/completions",
        "model_name": "Qwen",
        "api_key_env": "HKUST_API_KEY",
        "enable_thinking": False,
    },
}

DATASET_MODEL_MAP = {
    "GPT_5": "GPT_5",
    "GPT_o4": "GPT_o4",
    "QwenT": "QwenT",
    "QwenN": "QwenN",
}

# Aligned technical settings across EA/EI/Neutral
MAX_API_RETRIES = 5
RETRY_DELAY_SECONDS = 5
TIMEOUT_ALIGNED = (10, 300)
MAX_TOKENS_ALIGNED = 4096
TEMPERATURE_ALIGNED = 1.0

FINAL_JSON_SPEC = """Return your final answer as JSON exactly in this shape:
FINAL_RESPONSE_JSON = {
  "choice": 1 or 2,
  "decision": "concise chosen action statement",
  "reasoning": "brief reason for the choice"
}
Do not omit the JSON."""


def get_api_key(model_name: str) -> str:
    config = MODEL_CONFIGS.get(model_name)
    if not config:
        raise ValueError(f"Unknown model: {model_name}")
    api_key = os.getenv(config["api_key_env"])
    if not api_key:
        raise ValueError(f"Missing API key. Set environment variable {config['api_key_env']}")
    return api_key
