# Dilemma Validation

Reproducible Gemini-as-human-rater experiment that scores all 8 emotional
dilemma variants against the neutral baseline on (a) semantic equivalence
and (b) emotional authenticity, in a single API call per item. Includes a
10 % test-retest reliability pass.

Reference plan:
`/Users/carina/.cursor/plans/dilemma_validation_experiment_baa1d0aa.plan.md`

## Layout

```
DilemmaValidation/
  config.py                  paths, model, weights, thresholds, RNG seeds
  prompts.py                 verbatim SYSTEM + USER_TEMPLATE and parser
  dataset_loader.py          normalize 9 CSVs, dedupe idx, build join
  sampling.py                topic_group-stratified sampling + review pack
  gemini_client.py           retrying HTTP client + JSON-mode + reframe
  run_stratified_sampling.py CLI: draw 20 idx/stratum, write sampling/*
  run_validation.py          main census, --use-sample / --resume / --workers
  run_reliability.py         stratified 10 % retest, --use-sample
  analyze_results.py         item_quality, dataset means, bootstrap CI, grade
  analyze_ranking.py         within-idx Friedman + Nemenyi + CD diagram
  generate_report.py         figures + report/validation_report.{md,html}
  results/
    raw/<variant>.jsonl           run-1 records
    raw/<variant>_retest.jsonl    run-2 records
    items/<variant>_items.csv     per-idx scored rows
    datasets/dataset_quality.csv  one row per variant
    datasets/reliability.csv      test-retest stats per variant
    datasets/coverage.csv         loader coverage table
    datasets/ranking_summary.csv  Friedman + Nemenyi ranking + CLD groups
    datasets/ranking_friedman.json
    datasets/ranking_nemenyi_pmatrix.csv
    datasets/ranking_subdimensions.csv
    figures/*.png                 includes figure_ranking_*.png
  logs/
    run_validation.log
    failed_items.csv
  report/
    validation_report.md
    validation_report.html
  sampling/
    sampled_idx.csv
    human_validation_pack.csv
    sampling_report.md
    manifest.json
```

## Setup

```bash
cd DataAnalysis/DilemmaValidation
pip install -r requirements.txt
export AIGCBEST_API_KEY="<your key>"
```

The endpoint is `https://api2.aigcbest.top/v1/chat/completions` with model
`gemini-3.1-pro-preview-low`.

## Stratified sampling (recommended first round)

Before burning API budget on the full 1,360 × 8 census, draw a topic_group-stratified
random sample of `idx` and validate against that subset. Default allocation is
**20 idx per stratum × 17 strata = 340 idx**, expanded into a 9-row review pack
(1 neutral + 8 emotional) for human verification.

```bash
python run_stratified_sampling.py
python run_validation.py --use-sample
python run_reliability.py --use-sample
python analyze_results.py
python analyze_ranking.py
python generate_report.py
```

Cost change: `340 × 8 = 2,720` main calls (~$8–10) instead of `1,360 × 8 = 10,880`
calls (~$30+). The retest pool is drawn from the sampled idx only; the run-1
item_quality quartile stratification is preserved.

Outputs land in `sampling/`:

```
sampling/
  sampled_idx.csv             340 rows: idx, topic_group, seed, per_stratum_quota, drawn_at_iso
  human_validation_pack.csv   3,060 rows: 9 per idx, sorted (idx, role, model_tag)
  sampling_report.md          source files, eligibility, per-stratum draw, totals
  manifest.json               seed, per_stratum, source SHAs, drawn_at_iso
```

Seeding:

- `config.SAMPLE_SEED = 20260514` is the stratum-draw seed.
- `config.RANDOM_STATE = 20260519` remains pinned for retest stratification + bootstraps.
- Re-running `run_stratified_sampling.py` with the same `--seed` produces an
  identical `sampled_idx.csv`; `--seed 99` (or any other value) produces a
  different sample.

## Quickstart

### Smoke test (5 items, CN only)

```bash
python run_validation.py --variants CN --limit 5
```

### Full census (10,880 calls)

```bash
python run_validation.py
python run_validation.py --resume        # continue if interrupted
python run_validation.py --workers 16    # bump concurrency
```

### Reliability retest (10 %)

```bash
python run_reliability.py
```

### Aggregate + grade

```bash
python analyze_results.py
```

### Ranking analysis (within-idx, Friedman + Nemenyi)

```bash
python analyze_ranking.py
python analyze_ranking.py --score semantic_sim
```

Consumes the existing `results/items/<variant>_items.csv` and
`results/datasets/dataset_quality.csv`; does **not** call the API. Outputs
`results/datasets/ranking_{summary,friedman,nemenyi_pmatrix,subdimensions}.{csv,json}`
and `results/figures/figure_ranking_{critical_difference,subdimensions}.png`.
`python analyze_ranking.py --selftest` produces a synthetic 8 x 50 demo even
when the real items CSVs are empty.

Run this **before** `generate_report.py` so that Section 8 of the report
(ranking analysis) is populated; otherwise that section renders as a
placeholder.

### Build the report (figures + Markdown + HTML)

```bash
python generate_report.py
```

## Output JSONL schema

One JSON object per line in `results/raw/<variant>.jsonl`:

```
variant, idx, run (1|2), timestamp, model, prompt_hash,
semantic_sim, semantic_justification,
emotions, emotion_naturalness, emotion_coherence, emotion_justification,
qc_flag, raw_text (truncated to 4 KB)
```

`qc_flag` is one of `ok`, `clipped`, `parse_error`, `refusal`, `network_failed`.

## Reproducibility

- `SAMPLE_SEED = 20260514` pins the topic_group-stratified pre-validation sample.
- `RANDOM_STATE = 20260519` is pinned for the retest stratified sample and
  the bootstrap CI.
- All paths live in `config.py`; only the API key comes from the environment.
- The exact rendered prompt and SYSTEM string are hashed (sha256) and stored
  with every record (`prompt_hash`).
- `sampling/manifest.json` records the seed, per-stratum quota, draw timestamp,
  and SHA-256 of each source CSV.
