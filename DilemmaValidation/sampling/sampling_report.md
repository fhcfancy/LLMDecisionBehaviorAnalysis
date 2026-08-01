# Stratified Sampling Report

- Run timestamp (UTC): `2026-05-19T12:49:07+00:00`
- Sample seed: `20260514`
- Per-stratum quota: `20`
- Strata: `17`
- Reference idx (unique): `1360`
- Eligible idx (intersection across neutral + 8 variants): `1360`
- Sampled idx: `340`
- Review pack rows: `3060` (= 340 idx x 9 rows = 3060)

## Source files (1 neutral + 8 emotional)

| model_tag | role | source_file | n_in_file | n_with_text | n_idx_matched |
|---|---|---|---:|---:|---:|
| NEUTRAL | neutral | NeutralDilemma.csv | 1360 | 1360 | 1360 |
| CN | emotional | CN_emotional_dilemma.csv | 1360 | 1360 | 1360 |
| CT | emotional | CT_emotional_dilemma.csv | 1360 | 1360 | 1360 |
| R1 | emotional | R1_emotional_dilemma.csv | 1360 | 1360 | 1360 |
| V3 | emotional | V3_emotional_dilemma.csv | 1360 | 1360 | 1360 |
| GPT_5 | emotional | GPT_5_emmotional_dilemma.csv | 1360 | 1360 | 1360 |
| GPT_o4 | emotional | GPT_o4_emmotional_dilemma.csv | 1360 | 1360 | 1360 |
| QwenN | emotional | QwenN_emotional_dilemma.csv | 1360 | 1360 | 1360 |
| QwenT | emotional | QwenT_emotional_dilemma.csv | 1360 | 1360 | 1360 |

## Reference idx missing from each source

- **NEUTRAL**: 0 missing idx
- **CN**: 0 missing idx
- **CT**: 0 missing idx
- **R1**: 0 missing idx
- **V3**: 0 missing idx
- **GPT_5**: 0 missing idx
- **GPT_o4**: 0 missing idx
- **QwenN**: 0 missing idx
- **QwenT**: 0 missing idx

## Per-stratum draw

| stratum | population_size | drawn | mean_topic_len_chars |
|---|---:|---:|---:|
| business_organization | 80 | 20 | 311.2 |
| close_relationship | 80 | 20 | 325.9 |
| comitted_relationship | 80 | 20 | 323.3 |
| event_daily_life | 80 | 20 | 311.0 |
| event_special | 80 | 20 | 333.9 |
| family | 80 | 20 | 334.6 |
| friend | 80 | 20 | 289.6 |
| issue_crime_addiction | 80 | 20 | 318.4 |
| issue_personal_career | 80 | 20 | 309.0 |
| issue_pregnancy | 80 | 20 | 359.0 |
| issue_self_image_social | 80 | 20 | 339.1 |
| issue_wildlife_human_environment | 80 | 20 | 319.8 |
| issue_young_people | 80 | 20 | 303.8 |
| religion_custom | 80 | 20 | 337.8 |
| role_duty_responsibility | 80 | 20 | 326.2 |
| school | 80 | 20 | 306.6 |
| workplace | 80 | 20 | 333.8 |

## Final totals

- 340 idx x 9 rows = 3060 rows in `human_validation_pack.csv`
- Main census calls if `--use-sample`: 340 x 8 = 2720

## Reproducibility

- Command: `python run_stratified_sampling.py --per-stratum 20 --seed 20260514`
- Seed: `20260514` (config.SAMPLE_SEED)
- Method: equal-allocation stratified sample on `topic_group`, without replacement, via `numpy.random.default_rng(seed)` -> `DataFrame.sample(random_state=...)`.
