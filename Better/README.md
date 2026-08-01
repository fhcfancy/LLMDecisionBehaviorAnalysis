# Better Pipeline (Technical-Effect Controlled)

This folder provides a technically aligned version of the Polish generators to reduce engineering confounds when comparing reasoning styles.

## What is aligned

- Same API call logic and retries
- Same timeout and token budget
- Same temperature
- Same final answer schema (JSON with explicit `choice`)
- Same parsing and retry policy
- Same first-pass/eventual diagnostics for fair mechanism analysis

## Added analysis-friendly fields

Each output row now includes:
- eventual outcome: `choice_value`, `made_choice`, `has_json`
- first-pass outcome: `first_pass_choice_value`, `first_pass_made_choice`, `first_pass_has_json`
- retry metadata: `attempts_used`, `retry_count`
- API diagnostics (both eventual and first-pass): `http_status`, `finish_reason`, `api_error`, `raw_json`, plus `first_pass_*` counterparts

## What remains different (intended)

- Prompt reasoning style only:
  - `EmotionalAnalytic`: 3-step analytical CoT
  - `EmotionalIntuitive`: intuitive judgment style
  - `Neutral`: neutral reasoning style

## Run

From this folder:

- EA:
  - `python EmotionalAnalytic/cot_decision_generator.py CN`
- EI:
  - `python EmotionalIntuitive/intuitive_decision_generator.py CN`
- Neutral:
  - `python Neutral/neutral_decision_generator.py CN`

Replace `CN` with `CT`, `R1`, or `V3`.

### 3-step vs normal CoT experiment (EA)

- `python EmotionalAnalytic/cot_prompt_comparison_experiment.py CN`
- optional subset:
  - `python EmotionalAnalytic/cot_prompt_comparison_experiment.py CN --limit 200`

Outputs are saved under:

- `DataAnalysis/Better/decisions/EmotionalAnalytic`
- `DataAnalysis/Better/decisions/EmotionalIntuitive`
- `DataAnalysis/Better/decisions/Neutral`
- `DataAnalysis/Better/decisions/EmotionalAnalytic/experiments` (comparison experiment outputs)

## Analysis (new, separate from old Code/Analysis)

Run:

- `python Analysis/run_analysis.py`

Outputs are saved to:

- `DataAnalysis/Better/Processed_Results`

Key outputs:
- `master.csv`
- `choice_rate_first_pass.csv`
- `choice_rate_eventual.csv`
- `choice_rate_retry_uplift.csv`
- `diagnostic_breakdown_first_pass.csv`
- `diagnostic_breakdown_eventual.csv`
- `choice_made_cross_model_shift_first_pass.csv`
- `choice_made_cross_model_shift_eventual.csv`
- `choice_made_cross_mode_shift_first_pass.csv`
- `choice_made_cross_mode_shift_eventual.csv`
- `retry_profile.csv`
