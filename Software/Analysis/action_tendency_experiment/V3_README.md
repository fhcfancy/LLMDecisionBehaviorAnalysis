# Action Tendency Counterfactual Analysis

This folder implements a swap-order counterfactual experiment to diagnose why a mode (especially EA) may choose action2 more often.

## Files

- `run_swap_counterfactual.py`  
  Runs swapped-order prompts (action2/action1) using the same model + mode prompt style and saves outputs under:
  - `DataAnalysis/Better/decisions/ActionBiasSwap/{mode}/{mode}_{dataset}_swap.csv`

- `analyze_swap_counterfactual.py`  
  Reads original decisions + swap outputs and computes:
  - technical metrics: `coverage`
  - overall metrics: `effective`
  - behavior-only metrics: `conditional_match = effective / coverage`
  - strict fairness metric across modes: `strict_match_rate` on all-modes-both-valid idx
  - action2 tendency shift metrics under swap

## Recommended workflow

1) Run swap generation (example for V3 only):

```bash
python DataAnalysis/Better/Analysis/action_tendency_experiment/run_swap_counterfactual.py V3
```

2) Analyze swap results:

```bash
python DataAnalysis/Better/Analysis/action_tendency_experiment/analyze_swap_counterfactual.py V3
```

Generate markdown report at the same time:

```bash
python DataAnalysis/Better/Analysis/action_tendency_experiment/analyze_swap_counterfactual.py V3 \
  --report-md DataAnalysis/Better/Analysis/action_tendency_experiment/results/swap_bias_report_v3.md
```

3) Inspect outputs in:

- `DataAnalysis/Better/Analysis/action_tendency_experiment/results/swap_bias_mode_dataset_metrics.csv`
- `DataAnalysis/Better/Analysis/action_tendency_experiment/results/swap_bias_overall_by_mode.csv`
- `DataAnalysis/Better/Analysis/action_tendency_experiment/results/swap_bias_overall_by_dataset.csv`
- `DataAnalysis/Better/Analysis/action_tendency_experiment/results/swap_bias_strict_mode_dataset.csv`
- `DataAnalysis/Better/Analysis/action_tendency_experiment/results/swap_bias_strict_overall_by_mode.csv`
- optional markdown report path given by `--report-md`

## Interpretation quick guide

- High `strict_match_rate`: stable canonical choices under swap on fair same-denominator set.
- High `coverage`: fewer technical misses in counterfactual runs.
- High `effective`: practical stability including technical effects.
- High `conditional_match`: behavioral stability among technically valid pairs.
- Positive `action2_delta_original_minus_swapped_canonical`: action2 tendency drops after de-slotting, suggesting slot-position effect.
