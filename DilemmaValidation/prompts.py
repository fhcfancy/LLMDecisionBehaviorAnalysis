"""
Prompt strings and JSON-response parser/validator for the
DilemmaValidation experiment.

The SYSTEM and USER_TEMPLATE strings are verbatim from plan section 3
(see /Users/carina/.cursor/plans/dilemma_validation_experiment_baa1d0aa.plan.md).
Do not edit them without updating the plan.
"""

from __future__ import annotations

import json
import re
from typing import Any


SYSTEM: str = """You are participating in a research study as a human survey respondent.
Read each scenario carefully and answer from your honest first-person reaction —
what an ordinary person would think and feel reading these situations.
Do not analyze the texts as a language model; respond as a person would.
Always reply with a single valid JSON object that matches the schema exactly,
with no markdown fences and no commentary outside the JSON."""


USER_TEMPLATE: str = """You will read TWO short descriptions of the same kind of dilemma situation,
then answer two questions about them.

—— Scenario A ——
{neutral_text}
Possible actions: (1) {action1}   (2) {action2}

—— Scenario B ——
{emotional_text}
Possible actions: (1) {action1}   (2) {action2}

Part 1 — Are these the same dilemma?
Judge whether A and B describe the same underlying moral decision.
  • Is the decision conflict the same (same trade-off, same stakes)?
  • Are the two choices effectively the same?
  • Do they only differ in tone, or does one shift the meaning of the choice?
Return a single similarity score on a 0.00–1.00 scale:
  0.00 = clearly a different moral conflict
  0.50 = same topic but the conflict has shifted
  0.75 = same conflict, only minor framing differences
  1.00 = identical underlying dilemma, only tone differs
Add a one-sentence justification.

Part 2 — How does Scenario B feel?
Now think only about Scenario B, as if you were the person living through it.
  (a) emotions: up to 3 plain emotion words you would most likely feel
      (e.g., "guilt", "fear", "relief"). Do not guess an intended label.
  (b) emotion_naturalness (1–5): how organically those emotions arise from
      the situation itself. 1 = forced / over-written; 5 = exactly what a
      real person would feel here.
  (c) emotion_coherence (1–5): how well the emotional tone fits the facts
      of the dilemma. 1 = tone clashes with the facts; 5 = tone and facts
      are fully consistent.
Add a one-sentence justification.

Output ONLY this JSON:
{{
  "semantic_sim": 0.00,
  "semantic_justification": "",
  "emotions": ["", "", ""],
  "emotion_naturalness": 0,
  "emotion_coherence": 0,
  "emotion_justification": ""
}}"""


REQUIRED_KEYS: tuple[str, ...] = (
    "semantic_sim",
    "semantic_justification",
    "emotions",
    "emotion_naturalness",
    "emotion_coherence",
    "emotion_justification",
)

REFUSAL_MARKERS: tuple[str, ...] = (
    "i can't",
    "i cannot",
    "i'm unable",
    "i am unable",
    "i won't",
    "i will not",
    "sorry",
    "as an ai",
    "i'm sorry",
    "cannot assist",
)


def render_user_prompt(
    neutral_text: str,
    emotional_text: str,
    action1: str,
    action2: str,
) -> str:
    """Fill the USER_TEMPLATE with the four item fields."""
    return USER_TEMPLATE.format(
        neutral_text=neutral_text.strip(),
        emotional_text=emotional_text.strip(),
        action1=action1.strip(),
        action2=action2.strip(),
    )


def _strip_fences(text: str) -> str:
    """Remove leading/trailing markdown code fences if present."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`").strip()
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:].strip()
    if cleaned.endswith("```"):
        cleaned = cleaned[: -3].strip()
    return cleaned


_JSON_OBJECT_RE = re.compile(r"\{.*\}", re.DOTALL)


def _extract_json_blob(text: str) -> str | None:
    """Return the largest balanced {...} blob found in text, or None."""
    match = _JSON_OBJECT_RE.search(text)
    if match:
        return match.group(0)
    return None


def _clip_float(value: Any, lo: float, hi: float, default: float) -> float:
    try:
        x = float(value)
    except (TypeError, ValueError):
        return default
    if x != x:
        return default
    return max(lo, min(hi, x))


def _clip_int(value: Any, lo: int, hi: int, default: int) -> tuple[int, bool]:
    """Clip value to [lo, hi]. Returns (clipped_int, was_clipped)."""
    try:
        x = float(value)
    except (TypeError, ValueError):
        return default, True
    if x != x:
        return default, True
    raw_int = int(round(x))
    clipped = max(lo, min(hi, raw_int))
    return clipped, clipped != raw_int


def _normalize_emotions(value: Any) -> list[str]:
    """Coerce the emotions field to a list of up to 3 lowercase, stripped strings."""
    if value is None:
        return []
    if isinstance(value, str):
        parts = re.split(r"[,/;\n]+", value)
        raw = [p.strip() for p in parts]
    elif isinstance(value, (list, tuple)):
        raw = [str(x).strip() for x in value]
    else:
        raw = [str(value).strip()]
    out: list[str] = []
    seen: set[str] = set()
    for item in raw:
        if not item:
            continue
        lower = item.lower()
        lower = re.sub(r"[^a-z\-' ]", "", lower).strip()
        if not lower or lower in seen:
            continue
        seen.add(lower)
        out.append(lower)
        if len(out) == 3:
            break
    return out


def _looks_like_refusal(text: str) -> bool:
    lowered = text.strip().lower()
    if not lowered:
        return True
    for marker in REFUSAL_MARKERS:
        if marker in lowered:
            return True
    return False


def parse_and_validate(raw_text: str) -> tuple[dict, str]:
    """
    Parse the model's raw text into a validated dict.

    Returns
    -------
    parsed : dict
        The validated and normalized response with keys
        semantic_sim, semantic_justification, emotions,
        emotion_naturalness, emotion_coherence, emotion_justification.
    qc_flag : str
        One of "ok", "clipped", "parse_error", "refusal".

    On parse_error or refusal the parsed dict still contains the field shape
    populated with safe defaults so downstream code can rely on the schema.
    """
    if raw_text is None:
        return _empty_payload(), "refusal"

    text = _strip_fences(str(raw_text))

    if not text:
        return _empty_payload(), "refusal"

    data: Any = None
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        blob = _extract_json_blob(text)
        if blob is not None:
            try:
                data = json.loads(blob)
            except json.JSONDecodeError:
                data = None

    if not isinstance(data, dict):
        if _looks_like_refusal(text):
            return _empty_payload(), "refusal"
        return _empty_payload(), "parse_error"

    missing = [k for k in REQUIRED_KEYS if k not in data]
    if missing and _looks_like_refusal(text):
        return _empty_payload(), "refusal"

    qc_flag = "ok"

    semantic_sim = _clip_float(data.get("semantic_sim"), 0.0, 1.0, default=0.0)
    if semantic_sim != _safe_float(data.get("semantic_sim"), default=semantic_sim):
        qc_flag = "clipped"

    naturalness, nat_clipped = _clip_int(
        data.get("emotion_naturalness"), 1, 5, default=1
    )
    coherence, coh_clipped = _clip_int(
        data.get("emotion_coherence"), 1, 5, default=1
    )
    if nat_clipped or coh_clipped:
        qc_flag = "clipped"

    emotions = _normalize_emotions(data.get("emotions"))

    semantic_just = str(data.get("semantic_justification", "")).strip()
    emotion_just = str(data.get("emotion_justification", "")).strip()

    parsed = {
        "semantic_sim": round(semantic_sim, 4),
        "semantic_justification": semantic_just,
        "emotions": emotions,
        "emotion_naturalness": int(naturalness),
        "emotion_coherence": int(coherence),
        "emotion_justification": emotion_just,
    }

    if missing:
        qc_flag = "parse_error"

    return parsed, qc_flag


def _safe_float(value: Any, default: float) -> float:
    try:
        x = float(value)
        if x != x:
            return default
        return x
    except (TypeError, ValueError):
        return default


def _empty_payload() -> dict:
    return {
        "semantic_sim": None,
        "semantic_justification": "",
        "emotions": [],
        "emotion_naturalness": None,
        "emotion_coherence": None,
        "emotion_justification": "",
    }


if __name__ == "__main__":
    sample = """```json
{
  "semantic_sim": 1.2,
  "semantic_justification": "Same conflict, different framing.",
  "emotions": ["Guilt", "FEAR", "guilt"],
  "emotion_naturalness": 7,
  "emotion_coherence": 4,
  "emotion_justification": "Tone fits."
}
```"""
    parsed, flag = parse_and_validate(sample)
    print(json.dumps(parsed, indent=2))
    print("qc_flag:", flag)
