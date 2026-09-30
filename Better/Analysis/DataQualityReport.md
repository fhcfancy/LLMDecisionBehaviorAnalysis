# Data Quality Report: Better Decision Datasets

**Scope:** EmotionalAnalytic, EmotionalIntuitive, Neutral, Neutral-CoT

---

## EmotionalAnalytic

- **Location:** `Better/decisions/EmotionalAnalytic`
- **Files:** 12 (EA_CN_1.csv, EA_CN_2.csv, EA_CN_3.csv, EA_CT_1.csv, EA_CT_2.csv, EA_CT_3.csv, EA_R1_1.csv, EA_R1_2.csv, EA_R1_3.csv, EA_V3_1.csv, EA_V3_2.csv, EA_V3_3.csv)

### Aggregate metrics

| Metric | Value |
|--------|--------|
| Total rows | 16320 |
| Unique dilemma indices (idx) | 1360 |
| Rows with choice_value in {1,2} | 16317 |
| Choice 1 | 8164 |
| Choice 2 | 8153 |
| Choice value other/empty | 3 |
| Rows with parse status explicit_json | 16315 |
| Rows with API error recorded | 0 |
| Rows with HTTP status ≠ 200 | 0 |

### Per-file summary

| File | Rows | Unique idx | Duplicate idx | Choice 1/2 | Other/empty | API err | Parse OK |
|------|------|------------|---------------|------------|-------------|--------|----------|
| EA_CN_1.csv | 1360 | 1360 | 0 | 1358 | 2 | 0 | 1358 |
| EA_CN_2.csv | 1360 | 1360 | 0 | 1360 | 0 | 0 | 1360 |
| EA_CN_3.csv | 1360 | 1360 | 0 | 1360 | 0 | 0 | 1360 |
| EA_CT_1.csv | 1360 | 1360 | 0 | 1360 | 0 | 0 | 1360 |
| EA_CT_2.csv | 1360 | 1360 | 0 | 1360 | 0 | 0 | 1360 |
| EA_CT_3.csv | 1360 | 1360 | 0 | 1360 | 0 | 0 | 1360 |
| EA_R1_1.csv | 1360 | 1360 | 0 | 1359 | 1 | 0 | 1359 |
| EA_R1_2.csv | 1360 | 1360 | 0 | 1360 | 0 | 0 | 1360 |
| EA_R1_3.csv | 1360 | 1360 | 0 | 1360 | 0 | 0 | 1360 |
| EA_V3_1.csv | 1360 | 1360 | 0 | 1360 | 0 | 0 | 1359 |
| EA_V3_2.csv | 1360 | 1360 | 0 | 1360 | 0 | 0 | 1359 |
| EA_V3_3.csv | 1360 | 1360 | 0 | 1360 | 0 | 0 | 1360 |

### Completeness and consistency

- **Indices present in every file:** 1360
- **Indices in at least one file:** 1360
- **Run coverage:** All files cover the same set of indices.

### Quality assessment

- **Valid choice rate (choice_value ∈ {1,2}):** 100.0%
- **Explicit JSON parse rate:** 100.0%
- **Issues:** some rows have missing or invalid choice_value

## EmotionalIntuitive

- **Location:** `Better/decisions/EmotionalIntuitive`
- **Files:** 12 (EI_CN_1.csv, EI_CN_2.csv, EI_CN_3.csv, EI_CT_1.csv, EI_CT_2.csv, EI_CT_3.csv, EI_R1_1.csv, EI_R1_2.csv, EI_R1_3.csv, EI_V3_1.csv, EI_V3_2.csv, EI_V3_3.csv)

### Aggregate metrics

| Metric | Value |
|--------|--------|
| Total rows | 16320 |
| Unique dilemma indices (idx) | 1360 |
| Rows with choice_value in {1,2} | 16311 |
| Choice 1 | 8088 |
| Choice 2 | 8223 |
| Choice value other/empty | 9 |
| Rows with parse status explicit_json | 16299 |
| Rows with API error recorded | 4 |
| Rows with HTTP status ≠ 200 | 0 |

### Per-file summary

| File | Rows | Unique idx | Duplicate idx | Choice 1/2 | Other/empty | API err | Parse OK |
|------|------|------------|---------------|------------|-------------|--------|----------|
| EI_CN_1.csv | 1360 | 1360 | 0 | 1357 | 3 | 1 | 1355 |
| EI_CN_2.csv | 1360 | 1360 | 0 | 1358 | 2 | 1 | 1357 |
| EI_CN_3.csv | 1360 | 1360 | 0 | 1358 | 2 | 1 | 1351 |
| EI_CT_1.csv | 1360 | 1360 | 0 | 1359 | 1 | 0 | 1359 |
| EI_CT_2.csv | 1360 | 1360 | 0 | 1360 | 0 | 0 | 1360 |
| EI_CT_3.csv | 1360 | 1360 | 0 | 1360 | 0 | 0 | 1359 |
| EI_R1_1.csv | 1360 | 1360 | 0 | 1360 | 0 | 0 | 1359 |
| EI_R1_2.csv | 1360 | 1360 | 0 | 1359 | 1 | 1 | 1359 |
| EI_R1_3.csv | 1360 | 1360 | 0 | 1360 | 0 | 0 | 1360 |
| EI_V3_1.csv | 1360 | 1360 | 0 | 1360 | 0 | 0 | 1360 |
| EI_V3_2.csv | 1360 | 1360 | 0 | 1360 | 0 | 0 | 1360 |
| EI_V3_3.csv | 1360 | 1360 | 0 | 1360 | 0 | 0 | 1360 |

### Completeness and consistency

- **Indices present in every file:** 1360
- **Indices in at least one file:** 1360
- **Run coverage:** All files cover the same set of indices.

### Quality assessment

- **Valid choice rate (choice_value ∈ {1,2}):** 99.9%
- **Explicit JSON parse rate:** 99.9%
- **Issues:** some rows have missing or invalid choice_value; some rows have API/HTTP failures

## Neutral

- **Location:** `Better/decisions/Neutral`
- **Files:** 12 (Neutral_CN_1.csv, Neutral_CN_2.csv, Neutral_CN_3.csv, Neutral_CT_1.csv, Neutral_CT_2.csv, Neutral_CT_3.csv, Neutral_R1_1.csv, Neutral_R1_2.csv, Neutral_R1_3.csv, Neutral_V3_1.csv, Neutral_V3_2.csv, Neutral_V3_3.csv)

### Aggregate metrics

| Metric | Value |
|--------|--------|
| Total rows | 16320 |
| Unique dilemma indices (idx) | 1360 |
| Rows with choice_value in {1,2} | 16320 |
| Choice 1 | 7575 |
| Choice 2 | 8745 |
| Choice value other/empty | 0 |
| Rows with parse status explicit_json | 16320 |
| Rows with API error recorded | 0 |
| Rows with HTTP status ≠ 200 | 0 |

### Per-file summary

| File | Rows | Unique idx | Duplicate idx | Choice 1/2 | Other/empty | API err | Parse OK |
|------|------|------------|---------------|------------|-------------|--------|----------|
| Neutral_CN_1.csv | 1360 | 1360 | 0 | 1360 | 0 | 0 | 1360 |
| Neutral_CN_2.csv | 1360 | 1360 | 0 | 1360 | 0 | 0 | 1360 |
| Neutral_CN_3.csv | 1360 | 1360 | 0 | 1360 | 0 | 0 | 1360 |
| Neutral_CT_1.csv | 1360 | 1360 | 0 | 1360 | 0 | 0 | 1360 |
| Neutral_CT_2.csv | 1360 | 1360 | 0 | 1360 | 0 | 0 | 1360 |
| Neutral_CT_3.csv | 1360 | 1360 | 0 | 1360 | 0 | 0 | 1360 |
| Neutral_R1_1.csv | 1360 | 1360 | 0 | 1360 | 0 | 0 | 1360 |
| Neutral_R1_2.csv | 1360 | 1360 | 0 | 1360 | 0 | 0 | 1360 |
| Neutral_R1_3.csv | 1360 | 1360 | 0 | 1360 | 0 | 0 | 1360 |
| Neutral_V3_1.csv | 1360 | 1360 | 0 | 1360 | 0 | 0 | 1360 |
| Neutral_V3_2.csv | 1360 | 1360 | 0 | 1360 | 0 | 0 | 1360 |
| Neutral_V3_3.csv | 1360 | 1360 | 0 | 1360 | 0 | 0 | 1360 |

### Completeness and consistency

- **Indices present in every file:** 1360
- **Indices in at least one file:** 1360
- **Run coverage:** All files cover the same set of indices.

### Quality assessment

- **Valid choice rate (choice_value ∈ {1,2}):** 100.0%
- **Explicit JSON parse rate:** 100.0%
- **Issues:** none detected

## Neutral-CoT

- **Location:** `Better/decisions/Neutral-CoT`
- **Files:** 12 (Neutral-CoT_CN_1.csv, Neutral-CoT_CN_2.csv, Neutral-CoT_CN_3.csv, Neutral-CoT_CT_1.csv, Neutral-CoT_CT_2.csv, Neutral-CoT_CT_3.csv, Neutral-CoT_R1_1.csv, Neutral-CoT_R1_2.csv, Neutral-CoT_R1_3.csv, Neutral-CoT_V3_1.csv, Neutral-CoT_V3_2.csv, Neutral-CoT_V3_3.csv)

### Aggregate metrics

| Metric | Value |
|--------|--------|
| Total rows | 16320 |
| Unique dilemma indices (idx) | 1360 |
| Rows with choice_value in {1,2} | 16319 |
| Choice 1 | 7766 |
| Choice 2 | 8553 |
| Choice value other/empty | 1 |
| Rows with parse status explicit_json | 16318 |
| Rows with API error recorded | 0 |
| Rows with HTTP status ≠ 200 | 0 |

### Per-file summary

| File | Rows | Unique idx | Duplicate idx | Choice 1/2 | Other/empty | API err | Parse OK |
|------|------|------------|---------------|------------|-------------|--------|----------|
| Neutral-CoT_CN_1.csv | 1360 | 1360 | 0 | 1360 | 0 | 0 | 1360 |
| Neutral-CoT_CN_2.csv | 1360 | 1360 | 0 | 1360 | 0 | 0 | 1360 |
| Neutral-CoT_CN_3.csv | 1360 | 1360 | 0 | 1360 | 0 | 0 | 1360 |
| Neutral-CoT_CT_1.csv | 1360 | 1360 | 0 | 1360 | 0 | 0 | 1360 |
| Neutral-CoT_CT_2.csv | 1360 | 1360 | 0 | 1360 | 0 | 0 | 1360 |
| Neutral-CoT_CT_3.csv | 1360 | 1360 | 0 | 1360 | 0 | 0 | 1360 |
| Neutral-CoT_R1_1.csv | 1360 | 1360 | 0 | 1360 | 0 | 0 | 1359 |
| Neutral-CoT_R1_2.csv | 1360 | 1360 | 0 | 1360 | 0 | 0 | 1360 |
| Neutral-CoT_R1_3.csv | 1360 | 1360 | 0 | 1360 | 0 | 0 | 1360 |
| Neutral-CoT_V3_1.csv | 1360 | 1360 | 0 | 1360 | 0 | 0 | 1360 |
| Neutral-CoT_V3_2.csv | 1360 | 1360 | 0 | 1359 | 1 | 0 | 1359 |
| Neutral-CoT_V3_3.csv | 1360 | 1360 | 0 | 1360 | 0 | 0 | 1360 |

### Completeness and consistency

- **Indices present in every file:** 1360
- **Indices in at least one file:** 1360
- **Run coverage:** All files cover the same set of indices.

### Quality assessment

- **Valid choice rate (choice_value ∈ {1,2}):** 100.0%
- **Explicit JSON parse rate:** 100.0%
- **Issues:** some rows have missing or invalid choice_value

---

## Summary

- **Total rows across all four datasets:** 65280
- **Total rows with valid choice (1 or 2):** 65267
- **Overall valid choice rate:** 100.0%
- **Total rows with API/HTTP issues:** 4

*Report generated by data quality check script.*