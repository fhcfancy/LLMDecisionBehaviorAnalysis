# Alignment Report (Neutral Reference)

## Scope
- Models: CN, CT, R1, V3
- Runs: 1, 2, 3 (each run uses each model's Neutral baseline)
- Modes: Neutral (reference), Neutral-CoT, EI, EA
- Decisions directory: `/Users/carina/Documents/MyResearch/Professional/DataAnalysis/Better/decisions`

## Metrics
- `strict_match_rate`: Match rate on all-4-valid idx (same denominator fairness).
- `coverage`: Share of Neutral-valid idx where method has valid choice.
- `effective`: Match vs Neutral over Neutral-valid idx (technical + behavior).
- `conditional_match`: `effective / coverage` (behavior after removing technical failures).

## Model `CN` (by run)

| Run | Method | RefN | All4N | Valid(M∩Ref) | StrictMatch | StrictRate | Coverage | Effective | Conditional |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | EA | 1360 | 1357 | 1358 | 1173 | 86.44% | 99.85% | 86.32% | 86.45% |
| 1 | EI | 1360 | 1357 | 1357 | 1184 | 87.25% | 99.78% | 87.06% | 87.25% |
| 1 | Neutral-CoT | 1360 | 1357 | 1360 | 1249 | 92.04% | 100.00% | 92.06% | 92.06% |
| 2 | EA | 1360 | 1358 | 1360 | 1160 | 85.42% | 100.00% | 85.37% | 85.37% |
| 2 | EI | 1360 | 1358 | 1358 | 1175 | 86.52% | 99.85% | 86.40% | 86.52% |
| 2 | Neutral-CoT | 1360 | 1358 | 1360 | 1246 | 91.75% | 100.00% | 91.69% | 91.69% |
| 3 | EA | 1360 | 1358 | 1360 | 1163 | 85.64% | 100.00% | 85.66% | 85.66% |
| 3 | EI | 1360 | 1358 | 1358 | 1162 | 85.57% | 99.85% | 85.44% | 85.57% |
| 3 | Neutral-CoT | 1360 | 1358 | 1360 | 1248 | 91.90% | 100.00% | 91.91% | 91.91% |

**Leaders (across runs)**
- Strict fairness: Neutral-CoT (92.04%)
- Technical coverage: Neutral-CoT (100.00%)
- End-to-end effective: Neutral-CoT (92.06%)
- Conditional behavior: Neutral-CoT (92.06%)

## Model `CT` (by run)

| Run | Method | RefN | All4N | Valid(M∩Ref) | StrictMatch | StrictRate | Coverage | Effective | Conditional |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | EA | 1360 | 1359 | 1360 | 1163 | 85.58% | 100.00% | 85.59% | 85.59% |
| 1 | EI | 1360 | 1359 | 1359 | 1175 | 86.46% | 99.93% | 86.40% | 86.46% |
| 1 | Neutral-CoT | 1360 | 1359 | 1360 | 1256 | 92.42% | 100.00% | 92.43% | 92.43% |
| 2 | EA | 1360 | 1360 | 1360 | 1169 | 85.96% | 100.00% | 85.96% | 85.96% |
| 2 | EI | 1360 | 1360 | 1360 | 1177 | 86.54% | 100.00% | 86.54% | 86.54% |
| 2 | Neutral-CoT | 1360 | 1360 | 1360 | 1256 | 92.35% | 100.00% | 92.35% | 92.35% |
| 3 | EA | 1360 | 1360 | 1360 | 1170 | 86.03% | 100.00% | 86.03% | 86.03% |
| 3 | EI | 1360 | 1360 | 1360 | 1179 | 86.69% | 100.00% | 86.69% | 86.69% |
| 3 | Neutral-CoT | 1360 | 1360 | 1360 | 1259 | 92.57% | 100.00% | 92.57% | 92.57% |

**Leaders (across runs)**
- Strict fairness: Neutral-CoT (92.57%)
- Technical coverage: EA (100.00%)
- End-to-end effective: Neutral-CoT (92.57%)
- Conditional behavior: Neutral-CoT (92.57%)

## Model `R1` (by run)

| Run | Method | RefN | All4N | Valid(M∩Ref) | StrictMatch | StrictRate | Coverage | Effective | Conditional |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | EA | 1360 | 1359 | 1359 | 1155 | 84.99% | 99.93% | 84.93% | 84.99% |
| 1 | EI | 1360 | 1359 | 1360 | 1085 | 79.84% | 100.00% | 79.78% | 79.78% |
| 1 | Neutral-CoT | 1360 | 1359 | 1360 | 1274 | 93.75% | 100.00% | 93.75% | 93.75% |
| 2 | EA | 1360 | 1359 | 1360 | 1161 | 85.43% | 100.00% | 85.37% | 85.37% |
| 2 | EI | 1360 | 1359 | 1359 | 1102 | 81.09% | 99.93% | 81.03% | 81.09% |
| 2 | Neutral-CoT | 1360 | 1359 | 1360 | 1259 | 92.64% | 100.00% | 92.65% | 92.65% |
| 3 | EA | 1360 | 1360 | 1360 | 1159 | 85.22% | 100.00% | 85.22% | 85.22% |
| 3 | EI | 1360 | 1360 | 1360 | 1100 | 80.88% | 100.00% | 80.88% | 80.88% |
| 3 | Neutral-CoT | 1360 | 1360 | 1360 | 1284 | 94.41% | 100.00% | 94.41% | 94.41% |

**Leaders (across runs)**
- Strict fairness: Neutral-CoT (94.41%)
- Technical coverage: EA (100.00%)
- End-to-end effective: Neutral-CoT (94.41%)
- Conditional behavior: Neutral-CoT (94.41%)

## Model `V3` (by run)

| Run | Method | RefN | All4N | Valid(M∩Ref) | StrictMatch | StrictRate | Coverage | Effective | Conditional |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | EA | 1360 | 1360 | 1360 | 1146 | 84.26% | 100.00% | 84.26% | 84.26% |
| 1 | EI | 1360 | 1360 | 1360 | 1133 | 83.31% | 100.00% | 83.31% | 83.31% |
| 1 | Neutral-CoT | 1360 | 1360 | 1360 | 1299 | 95.51% | 100.00% | 95.51% | 95.51% |
| 2 | EA | 1360 | 1359 | 1360 | 1174 | 86.39% | 100.00% | 86.32% | 86.32% |
| 2 | EI | 1360 | 1359 | 1360 | 1152 | 84.77% | 100.00% | 84.71% | 84.71% |
| 2 | Neutral-CoT | 1360 | 1359 | 1359 | 1314 | 96.69% | 99.93% | 96.62% | 96.69% |
| 3 | EA | 1360 | 1360 | 1360 | 1154 | 84.85% | 100.00% | 84.85% | 84.85% |
| 3 | EI | 1360 | 1360 | 1360 | 1143 | 84.04% | 100.00% | 84.04% | 84.04% |
| 3 | Neutral-CoT | 1360 | 1360 | 1360 | 1307 | 96.10% | 100.00% | 96.10% | 96.10% |

**Leaders (across runs)**
- Strict fairness: Neutral-CoT (96.69%)
- Technical coverage: EA (100.00%)
- End-to-end effective: Neutral-CoT (96.62%)
- Conditional behavior: Neutral-CoT (96.69%)

## Overall rate (pooled across runs and models)

### EA
- **Strict match rate:** 85.52% (n = 13947 / 16309)
- **Coverage:** 99.98% | **Effective:** 85.49% | **Conditional:** 85.51%

### EI
- **Strict match rate:** 84.41% (n = 13767 / 16309)
- **Coverage:** 99.94% | **Effective:** 84.36% | **Conditional:** 84.40%

### Neutral-CoT
- **Strict match rate:** 93.51% (n = 15251 / 16309)
- **Coverage:** 99.99% | **Effective:** 93.50% | **Conditional:** 93.51%

| Method | RefN | All4N | Valid(M∩Ref) | StrictMatch | StrictRate | Coverage | Effective | Conditional |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| EA | 16320 | 16309 | 16317 | 13947 | 85.52% | 99.98% | 85.49% | 85.51% |
| EI | 16320 | 16309 | 16311 | 13767 | 84.41% | 99.94% | 84.36% | 84.40% |
| Neutral-CoT | 16320 | 16309 | 16319 | 15251 | 93.51% | 99.99% | 93.50% | 93.51% |

**Overall leaders**
- Strict fairness: Neutral-CoT (93.51%)
- Technical coverage: Neutral-CoT (99.99%)
- End-to-end effective: Neutral-CoT (93.50%)
- Conditional behavior: Neutral-CoT (93.51%)
