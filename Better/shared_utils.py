"""
Shared utilities for Better pipeline.
- aligned API call behavior
- unified parsing
- unified retry policy
"""

from __future__ import annotations

import csv
import json
import os
import re
import time
from typing import Dict, List

import requests

from shared_config import (
    MAX_API_RETRIES,
    MAX_TOKENS_ALIGNED,
    MODEL_CONFIGS,
    RETRY_DELAY_SECONDS,
    TEMPERATURE_ALIGNED,
    TIMEOUT_ALIGNED,
    get_api_key,
)


def load_existing_results(output_file: str) -> Dict[int, Dict]:
    existing: Dict[int, Dict] = {}
    if output_file and os.path.exists(output_file):
        try:
            with open(output_file, "r", encoding="utf-8") as f:
                for row in csv.DictReader(f):
                    idx = int(row.get("idx", -1))
                    if idx >= 0:
                        existing[idx] = row
        except Exception:
            pass
    return existing


def save_result_incremental(
    output_file: str,
    result: Dict,
    fieldnames: List[str],
    overwrite_existing: bool = False,
) -> None:
    idx = result.get("idx")
    idx_int = None
    try:
        idx_int = int(idx) if idx is not None else None
    except (TypeError, ValueError):
        pass

    if overwrite_existing and output_file and os.path.exists(output_file) and idx_int is not None:
        try:
            with open(output_file, "r", encoding="utf-8", newline="") as f:
                reader = csv.DictReader(f)
                header = reader.fieldnames or fieldnames
                rows = [r for r in reader if int(r.get("idx", -1)) != idx_int]
            with open(output_file, "w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=header, quoting=csv.QUOTE_MINIMAL)
                writer.writeheader()
                writer.writerows(rows)
        except Exception:
            pass

    file_exists = os.path.exists(output_file) if output_file else False
    with open(output_file, "a", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, quoting=csv.QUOTE_MINIMAL)
        if not file_exists:
            writer.writeheader()
        writer.writerow(result)


def api_call_with_retry(model_name: str, prompt: str) -> Dict[str, str]:
    config = MODEL_CONFIGS.get(model_name)
    if not config:
        raise ValueError(f"Unknown model: {model_name}")

    api_key = get_api_key(model_name)
    api_url = str(config.get("api_url", "")).rstrip("/")
    use_anthropic_messages = api_url.endswith("/messages")

    headers = {"Content-Type": "application/json"}
    if use_anthropic_messages:
        headers["x-api-key"] = api_key
        headers["anthropic-version"] = "2023-06-01"
    else:
        headers["Authorization"] = f"Bearer {api_key}"

    if use_anthropic_messages:
        payload = {
            "model": config["model_name"],
            "messages": [{"role": "user", "content": [{"type": "text", "text": prompt}]}],
            "max_tokens": MAX_TOKENS_ALIGNED,
            "temperature": TEMPERATURE_ALIGNED,
        }
    else:
        payload = {
            "model": config["model_name"],
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": MAX_TOKENS_ALIGNED,
            "temperature": TEMPERATURE_ALIGNED,
        }

    last_error = ""
    last_status = ""
    last_finish_reason = ""
    last_raw_json = ""
    attempts_used = 0

    first_pass = {
        "content": "",
        "api_error": "",
        "http_status": "",
        "finish_reason": "",
        "raw_json": "",
    }

    for attempt in range(MAX_API_RETRIES):
        attempts_used = attempt + 1
        try:
            response = requests.post(
                config["api_url"],
                headers=headers,
                json=payload,
                timeout=TIMEOUT_ALIGNED,
            )
            last_status = str(response.status_code)
            response.raise_for_status()
            data = response.json()
            last_raw_json = json.dumps(data, ensure_ascii=False)
            first_pass["http_status"] = first_pass["http_status"] or last_status
            first_pass["raw_json"] = first_pass["raw_json"] or last_raw_json

            content = ""
            if use_anthropic_messages:
                blocks = data.get("content", [])
                if isinstance(blocks, list):
                    parts: List[str] = []
                    for block in blocks:
                        if isinstance(block, dict) and block.get("type") == "text":
                            txt = str(block.get("text", "") or "").strip()
                            if txt:
                                parts.append(txt)
                    content = "\n".join(parts).strip()
                last_finish_reason = str(data.get("stop_reason", "") or data.get("stop_sequence", "") or "")
            elif "choices" in data and data["choices"]:
                c0 = data["choices"][0]
                msg = c0.get("message", {}) or {}
                content = str(msg.get("content", "") or "").strip()
                last_finish_reason = str(c0.get("finish_reason", "") or "")

            if content:
                if not first_pass["finish_reason"]:
                    first_pass["finish_reason"] = last_finish_reason
                if not first_pass["content"]:
                    first_pass["content"] = content
                return {
                    "content": content,
                    "api_error": "",
                    "http_status": last_status,
                    "finish_reason": last_finish_reason,
                    "raw_json": last_raw_json,
                    "attempts_used": str(attempts_used),
                    "retry_count": str(max(0, attempts_used - 1)),
                    "first_pass_content": first_pass["content"],
                    "first_pass_api_error": first_pass["api_error"],
                    "first_pass_http_status": first_pass["http_status"],
                    "first_pass_finish_reason": first_pass["finish_reason"],
                    "first_pass_raw_json": first_pass["raw_json"],
                }
            last_error = "No text content in response"
            if not first_pass["api_error"]:
                first_pass["api_error"] = last_error
        except requests.exceptions.RequestException as exc:
            last_error = str(exc)
            if not first_pass["api_error"]:
                first_pass["api_error"] = last_error
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            last_error = f"Bad JSON response: {exc}"
            if not first_pass["api_error"]:
                first_pass["api_error"] = last_error

        if attempt < MAX_API_RETRIES - 1:
            time.sleep(RETRY_DELAY_SECONDS * (attempt + 1))

    return {
        "content": "",
        "api_error": last_error or "Unknown API failure",
        "http_status": last_status,
        "finish_reason": last_finish_reason,
        "raw_json": last_raw_json,
        "attempts_used": str(attempts_used),
        "retry_count": str(max(0, attempts_used - 1)),
        "first_pass_content": first_pass["content"],
        "first_pass_api_error": first_pass["api_error"],
        "first_pass_http_status": first_pass["http_status"],
        "first_pass_finish_reason": first_pass["finish_reason"],
        "first_pass_raw_json": first_pass["raw_json"],
    }


def extract_final_json(response_text: str):
    if not response_text:
        return None
    patterns = [
        r"FINAL_RESPONSE_JSON\s*=\s*(\{.*?\})",
        r"```json\s*(\{.*?\})\s*```",
        r"(\{[^{}]*\"choice\"\s*:\s*[12][^{}]*\})",
    ]
    for p in patterns:
        m = re.search(p, response_text, re.DOTALL | re.IGNORECASE)
        if not m:
            continue
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            continue
    return None


def parse_choice_output(response_text: str, action1: str, action2: str) -> Dict[str, object]:
    parsed = extract_final_json(response_text)
    choice_value: object = "NA"
    decision = ""
    reasoning = ""
    has_json = 0
    choice_parse_status = "no_response"

    if isinstance(parsed, dict):
        has_json = 1
        raw_choice = parsed.get("choice")
        try:
            c = int(str(raw_choice).strip())
            if c in (1, 2):
                choice_value = c
                choice_parse_status = "explicit_json"
        except (TypeError, ValueError):
            pass
        decision = str(parsed.get("decision", "") or "").strip()
        reasoning = str(parsed.get("reasoning", "") or parsed.get("reason", "") or "").strip()

    txt = (response_text or "").strip()
    ltxt = txt.lower()
    refusal_markers = [
        "i can't",
        "i cannot",
        "i'm unable",
        "i am unable",
        "cannot decide",
        "can't decide",
        "unable to decide",
        "refuse",
        "insufficient information",
    ]

    # Respect only explicit model choices. Do not infer by fuzzy action-text containment.
    if choice_value == 0:
        explicit_1 = bool(re.search(r"\b(action\s*1|choice\s*[:=]?\s*1|choose\s+action\s*1)\b", ltxt))
        explicit_2 = bool(re.search(r"\b(action\s*2|choice\s*[:=]?\s*2|choose\s+action\s*2)\b", ltxt))

        if explicit_1 and not explicit_2:
            choice_value = 1
            choice_parse_status = "explicit_text"
        elif explicit_2 and not explicit_1:
            choice_value = 2
            choice_parse_status = "explicit_text"
        elif txt:
            # Non-empty but not a valid explicit choice => refusal.
            # This includes explicit refusal language and any other non-choice non-empty answer.
            choice_value = 0
            choice_parse_status = "refusal"
        else:
            # Empty response.
            choice_value = "NA"
            choice_parse_status = "no_response"
    elif str(choice_value) in ("1", "2") and choice_parse_status == "no_response":
        # Safety fallback in case future edits set explicit choice before this branch.
        choice_parse_status = "explicit_text"

    if not decision:
        decision = txt[:500]
    if not reasoning:
        reasoning = decision

    return {
        "choice_value": choice_value,
        "decision": decision,
        "reason": reasoning,
        "has_json": has_json,
        "choice_parse_status": choice_parse_status,
        "made_choice": int(str(choice_value) in ("1", "2")),
    }


def should_retry_row(row: Dict) -> bool:
    """Unified retry policy across all modes: retry hard API failures only."""
    decision = str(row.get("decision", "")).lower()
    api_error = str(row.get("api_error", "")).lower()
    if "api failure" in decision or "no response" in decision:
        return True
    if api_error:
        return True
    return False
