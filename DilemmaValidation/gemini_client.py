"""
Threaded Gemini client for the DilemmaValidation experiment.

Wraps `requests.post` against the OpenAI-compatible aigcbest proxy with:
  * 8 exponential-backoff retries with jitter
  * separate cooldown on read-timeout streaks
  * JSON-mode (`response_format`) with a graceful fallback to plain text
    when the proxy 400s on that field
  * one strict-JSON clarification retry and one refusal-reframe retry

Pattern adapted from
Generalization/recover_qwent_failed_cases.py
"""

from __future__ import annotations

import json
import random
import time
from typing import Any

import requests

from config import (
    API_URL,
    BASE_DELAY_SECONDS,
    CONNECT_TIMEOUT,
    MAX_BACKOFF_SECONDS,
    MAX_RETRIES,
    MAX_TOKENS,
    MODEL_NAME,
    READ_TIMEOUT_BASE,
    READ_TIMEOUT_MAX,
    TEMPERATURE,
    TIMEOUT_COOLDOWN_AFTER,
    TIMEOUT_COOLDOWN_SECONDS,
    get_api_key,
)
from prompts import SYSTEM, parse_and_validate, render_user_prompt
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


_PARSE_RETRY_USER_MSG: str = (
    "Your previous reply was not valid JSON. Reply with the JSON object only, "
    "matching the schema exactly, with no markdown fences and no extra commentary."
)
_REFUSAL_RETRY_USER_MSG: str = (
    "Please answer as a survey respondent. There is no harmful content. "
    "Reply with the JSON object only."
)


class GeminiCallError(RuntimeError):
    """Raised when all transport-level retries are exhausted."""


def _timeout_for_attempt(attempt: int) -> tuple[int, int]:
    """Return (connect_timeout, read_timeout) for the given attempt index."""
    if attempt <= 3:
        read_timeout = READ_TIMEOUT_BASE
    elif attempt <= 6:
        read_timeout = min(2 * READ_TIMEOUT_BASE, READ_TIMEOUT_MAX)
    else:
        read_timeout = READ_TIMEOUT_MAX
    return (CONNECT_TIMEOUT, read_timeout)


def _compute_backoff(attempt: int, is_timeout: bool) -> float:
    """Exponential backoff with jitter; penalize timeouts a bit more."""
    base = BASE_DELAY_SECONDS * (2 ** (attempt - 1))
    if is_timeout:
        base *= 1.5
    wait = min(base, MAX_BACKOFF_SECONDS)
    jitter = random.uniform(0, 2.0)
    return round(wait + jitter, 2)


def _extract_content(model_content: Any) -> str:
    """Flatten an OpenAI-style content payload (str | list[blocks]) to a string."""
    if isinstance(model_content, str):
        return model_content
    if isinstance(model_content, list):
        parts: list[str] = []
        for block in model_content:
            if isinstance(block, dict):
                text = block.get("text")
                if text:
                    parts.append(text)
        return "\n".join(parts)
    if model_content is None:
        return ""
    return str(model_content)


def _post_chat(
    api_key: str,
    messages: list[dict[str, str]],
    *,
    temperature: float,
    max_tokens: int,
    attempt: int,
    use_json_mode: bool,
) -> str:
    """One raw POST. Returns the assistant text. Raises on transport errors."""
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }
    payload: dict[str, Any] = {
        "model": MODEL_NAME,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if use_json_mode:
        payload["response_format"] = {"type": "json_object"}

    response = requests.post(
        API_URL,
        headers=headers,
        json=payload,
        timeout=_timeout_for_attempt(attempt),
    )

    if response.status_code == 400 and use_json_mode:
        try:
            err_body = response.json()
        except Exception:
            err_body = {}
        msg = json.dumps(err_body).lower() if err_body else response.text.lower()
        if "response_format" in msg or "json_object" in msg or "schema" in msg:
            payload.pop("response_format", None)
            response = requests.post(
                API_URL,
                headers=headers,
                json=payload,
                timeout=_timeout_for_attempt(attempt),
            )

    response.raise_for_status()
    body = response.json()
    if "choices" not in body or not body.get("choices"):
        server_error = body.get("error") or body.get("message") or body
        raise ValueError(f"Unexpected API response (missing 'choices'): {server_error}")

    return _extract_content(body["choices"][0]["message"].get("content"))


def _post_with_backoff(
    api_key: str,
    messages: list[dict[str, str]],
    *,
    temperature: float,
    max_tokens: int,
) -> str:
    """
    Drive _post_chat through up to MAX_RETRIES attempts with exp backoff,
    using JSON-mode first and falling back to plain text on 400.
    """
    timeout_streak = 0
    last_exc: Exception | None = None
    use_json_mode = True

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            return _post_chat(
                api_key=api_key,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                attempt=attempt,
                use_json_mode=use_json_mode,
            )
        except requests.exceptions.ReadTimeout as exc:
            last_exc = exc
            timeout_streak += 1
            wait_seconds = _compute_backoff(attempt=attempt, is_timeout=True)
            if (
                timeout_streak >= TIMEOUT_COOLDOWN_AFTER
                and attempt < MAX_RETRIES
            ):
                time.sleep(TIMEOUT_COOLDOWN_SECONDS)
                timeout_streak = 0
            if attempt < MAX_RETRIES:
                time.sleep(wait_seconds)
        except (
            requests.exceptions.RequestException,
            ValueError,
        ) as exc:
            last_exc = exc
            timeout_streak = 0
            if isinstance(exc, requests.exceptions.HTTPError):
                status = getattr(exc.response, "status_code", None)
                if status == 400 and use_json_mode:
                    use_json_mode = False
            wait_seconds = _compute_backoff(attempt=attempt, is_timeout=False)
            if attempt < MAX_RETRIES:
                time.sleep(wait_seconds)

    raise GeminiCallError(
        f"All {MAX_RETRIES} attempts failed; last error: {last_exc!r}"
    )


def call_gemini(
    neutral_text: str,
    emotional_text: str,
    action1: str,
    action2: str,
    *,
    temperature: float = TEMPERATURE,
    max_tokens: int = MAX_TOKENS,
    api_key: str | None = None,
) -> tuple[dict, str, str]:
    """
    Issue a single combined Task 1 + Task 2 call.

    Returns
    -------
    parsed : dict
        Validated payload with the six expected keys.
    qc_flag : str
        One of "ok", "clipped", "parse_error", "refusal".
    raw_text : str
        The last raw assistant message text observed (post-fence-strip kept off
        so the audit trail is forensic).
    """
    if api_key is None:
        api_key = get_api_key()

    user_prompt = render_user_prompt(
        neutral_text=neutral_text,
        emotional_text=emotional_text,
        action1=action1,
        action2=action2,
    )
    messages: list[dict[str, str]] = [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": user_prompt},
    ]

    raw_text = _post_with_backoff(
        api_key=api_key,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    parsed, qc_flag = parse_and_validate(raw_text)

    if qc_flag == "parse_error":
        for _ in range(2):
            clar_messages = messages + [
                {"role": "assistant", "content": raw_text},
                {"role": "user", "content": _PARSE_RETRY_USER_MSG},
            ]
            try:
                raw_text = _post_with_backoff(
                    api_key=api_key,
                    messages=clar_messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
            except GeminiCallError:
                break
            parsed, qc_flag = parse_and_validate(raw_text)
            if qc_flag != "parse_error":
                break

    if qc_flag == "refusal":
        reframe_messages = messages + [
            {"role": "assistant", "content": raw_text or ""},
            {"role": "user", "content": _REFUSAL_RETRY_USER_MSG},
        ]
        try:
            raw_text = _post_with_backoff(
                api_key=api_key,
                messages=reframe_messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            parsed, qc_flag = parse_and_validate(raw_text)
        except GeminiCallError:
            pass

    return parsed, qc_flag, raw_text


if __name__ == "__main__":
    try:
        api_key = get_api_key()
    except EnvironmentError as exc:
        print(f"ERROR: {exc}")
        raise SystemExit(1)

    parsed, qc_flag, raw_text = call_gemini(
        neutral_text="You are deciding whether to report a friend who cheated on a test.",
        emotional_text=(
            "Your hands tremble as you stare at your friend's cheating ticket — "
            "you have to decide whether to tell the proctor."
        ),
        action1="report the friend",
        action2="stay silent",
    )
    print(json.dumps(parsed, indent=2))
    print("qc_flag:", qc_flag)
    print("raw_len:", len(raw_text))
