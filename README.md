# Emotional Decision-Making Analysis

Code and data for analyzing emotional vs. neutral decision-making in large language models across moral dilemma scenarios.

## Repository Structure

| Folder | Description |
|--------|-------------|
| `Dilemma/` | Emotional dilemma datasets used across models (CN, CT, R1, V3, neutral variants) |
| `DilemmaValidation/` | Validation pipeline: ranking analysis, reliability runs, report generation |
| `EmoitonalAnalytic/` | Emotional-analytic (EA) decision data per model, 3 runs each |
| `EmotionalIntuitive/` | Emotional-intuitive (EI) decision data per model, 3 runs each |
| `Generalization/` | Generalization experiments: dilemma generation and decision generators (CoT, intuitive, neutral) |
| `Neutral/` | Neutral (baseline) decision data per model |
| `Software/` | Analysis software and shared utilities |

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
export HKUST_API_KEY="<your key>"
```

## Reproducing

1. Dilemma generation: see `Generalization/generate_emotional_dilemmas.py`
2. Decision collection: see `Generalization/*_decision_generator.py`
3. Validation and analysis: see `DilemmaValidation/analyze_results.py` and `DilemmaValidation/run_reliability.py`
