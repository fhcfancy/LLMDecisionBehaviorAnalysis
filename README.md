# Emotional Decision-Making Analysis

Code and data for analyzing emotional vs. neutral decision-making in large language models across moral dilemma scenarios.

## Repository Structure

| Folder | Description |
|--------|-------------|
| `Better/` | Main experiment pipeline and decision data: EA/EI/Neutral/Neutral-CoT decisions per model (3 runs each), action-bias swap experiments, CoT prompt comparison experiments, and analysis |
| `Dilemma/` | Emotional dilemma datasets used across models (CN, CT, R1, V3, neutral variants) |
| `DilemmaValidation/` | Validation pipeline: ranking analysis, reliability runs, report generation |
| `Generalization/` | Generalization experiments: dilemma generation and decision generators (CoT, intuitive, neutral) |

Note: two aggregated experiment files (`Better/decisions/EmotionalAnalytic/experiments/cot_prompt_comparison_{CN,CT}.csv`) are not included because they exceed GitHub's 100MB file limit; the per-run files (`_run1`–`_run3`) they were aggregated from are included.

## Models

Decisions were collected from four models, identified by prefix in file names:

- `CN` — Claude (non-thinking)
- `CT` — Claude (thinking)
- `R1` — DeepSeek-R1
- `V3` — DeepSeek-V3

## Setup

```bash
pip install -r DilemmaValidation/requirements.txt
```

Some scripts call external LLM APIs. Set the required API keys as environment variables before running (see comments in each script), e.g.:

```bash
export AIGCBEST_API_KEY="<your key>"
export QWEN_API_KEY="<your key>"
```

The Qwen runs in `Generalization/` went through an OpenAI-compatible gateway
rather than a public endpoint, so its host is read from the environment too:

```bash
export QWEN_API_URL="https://<gateway>/v1/chat/completions"
```

## Reproducing

1. Dilemma generation: see `Generalization/generate_emotional_dilemmas.py`
2. Decision collection: see `Generalization/*_decision_generator.py`
3. Validation and analysis: see `DilemmaValidation/analyze_results.py` and `DilemmaValidation/run_reliability.py`
