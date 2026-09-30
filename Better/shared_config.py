"""
Aligned configuration for Better-mode generators.

Goal: keep reasoning logic differences (EA/EI/Neutral) while removing technical confounds.
"""

import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

# Input data 
INPUT_DILEMMA = f"{REPO_ROOT}/Dilemma"
INPUT_EMOTIONAL = INPUT_DILEMMA
INPUT_NEUTRAL = INPUT_DILEMMA

# Output base 
OUTPUT_BASE = f"{REPO_ROOT}/Better/decisions"

MODEL_CONFIGS = {
    "DeepSeekV3": {
        "api_url": "https://api.deepseek.com/v1/chat/completions",
        "model_name": "deepseek-chat",
        "api_key_env": "DEEPSEEK_API_KEY",
    },
    "DeepSeekR1": {
        "api_url": "https://api.deepseek.com/v1/chat/completions",
        "model_name": "deepseek-reasoner",
        "api_key_env": "DEEPSEEK_API_KEY",
    },
    "ClaudeCN": {
        "api_url": "https://api2.aigcbest.top/v1/messages",
        "model_name": "claude-sonnet-4-6",
        "api_key_env": "CLAUDE_API_KEY",
    },
    "ClaudeCT": {
        "api_url": "https://api2.aigcbest.top/v1/messages",
        "model_name": "claude-sonnet-4-6-thinking",
        "api_key_env": "CLAUDE_API_KEY",
    },
}

DATASET_MODEL_MAP = {
    "CN": "ClaudeCN",
    "CT": "ClaudeCT",
    "R1": "DeepSeekR1",
    "V3": "DeepSeekV3",
}

# Fully aligned technical settings across EA/EI/Neutral
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
