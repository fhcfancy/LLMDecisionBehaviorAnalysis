# Generalization Data Validity Report

- Reference dilemma set: `/Users/carina/Documents/MyResearch/Professional/DataAnalysis/Dilemma/NeutralDilemma.csv` (N=1360 idx).
- Decision CSV root: `/Users/carina/Documents/MyResearch/Professional/DataAnalysis/Generalization/decisions`.
- Topic labels: `/Users/carina/Documents/MyResearch/Professional/DataAnalysis/dilemmas_with_detail_by_action.csv`.
- Cells: 4 models x 4 modes = 16; one run per cell.
- Total rows in long frame (reference x model x mode): 21,760.

## Per-cell row counts (unique idx in CSV)

| model | Neutral | Neutral-CoT | EI | EA |
| --- | --- | --- | --- | --- |
| GPT_5 | 1360 | 1360 | 1360 | 1360 |
| GPT_o4 | 1360 | 1360 | 1360 | 1360 |
| QwenN | 1360 | 1360 | 1360 | 1360 |
| QwenT | 1360 | 1360 | 1360 | 1360 |

## Per-cell valid decisions (choice in {1, 2})

| model | Neutral | Neutral-CoT | EI | EA |
| --- | --- | --- | --- | --- |
| GPT_5 | 1360 | 1360 | 1360 | 1360 |
| GPT_o4 | 1356 | 1347 | 1358 | 1352 |
| QwenN | 1360 | 1358 | 1360 | 1359 |
| QwenT | 1359 | 1360 | 1360 | 1360 |

## Per-cell valid rate

| model | Neutral | Neutral-CoT | EI | EA |
| --- | --- | --- | --- | --- |
| GPT_5 | 1 | 1 | 1 | 1 |
| GPT_o4 | 0.9971 | 0.9904 | 0.9985 | 0.9941 |
| QwenN | 1 | 0.9985 | 1 | 0.9993 |
| QwenT | 0.9993 | 1 | 1 | 1 |

## Reference idx covered (presence in long frame after merge)

| model | Neutral | Neutral-CoT | EI | EA |
| --- | --- | --- | --- | --- |
| GPT_5 | 1360 | 1360 | 1360 | 1360 |
| GPT_o4 | 1356 | 1347 | 1358 | 1352 |
| QwenN | 1360 | 1358 | 1360 | 1359 |
| QwenT | 1359 | 1360 | 1360 | 1360 |

## Choice-1 base rate per cell (sanity for Claim 4)

| model | Neutral | Neutral-CoT | EI | EA |
| --- | --- | --- | --- | --- |
| GPT_5 | 0.4529 | 0.4478 | 0.4882 | 0.4522 |
| GPT_o4 | 0.4978 | 0.4788 | 0.4912 | 0.4719 |
| QwenN | 0.4882 | 0.4757 | 0.5000 | 0.4731 |
| QwenT | 0.4930 | 0.4853 | 0.5103 | 0.4890 |

## Topic coverage (17 unique topic_groups)

| topic_group | n_dilemmas |
| --- | --- |
| business_organization | 80 |
| issue_pregnancy | 80 |
| school | 80 |
| role_duty_responsibility | 80 |
| religion_custom | 80 |
| issue_young_people | 80 |
| issue_wildlife_human_environment | 80 |
| issue_self_image_social | 80 |
| issue_personal_career | 80 |
| close_relationship | 80 |
| issue_crime_addiction | 80 |
| friend | 80 |
| family | 80 |
| event_special | 80 |
| event_daily_life | 80 |
| comitted_relationship | 80 |
| workplace | 80 |

## Detailed per-cell information

| model | mode | n_rows | n_unique_idx | n_valid | valid_rate | n_invalid | n_api_error | path |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| GPT_5 | Neutral | 1360 | 1360 | 1360 | 1 | 0 | 0 | decisions/Neutral/Neutral_GPT_5.csv |
| GPT_5 | Neutral-CoT | 1360 | 1360 | 1360 | 1 | 0 | 0 | decisions/Neutral-CoT/Neutral-CoT_GPT_5.csv |
| GPT_5 | EI | 1360 | 1360 | 1360 | 1 | 0 | 0 | decisions/EmotionalIntuitive/EI_GPT_5.csv |
| GPT_5 | EA | 1360 | 1360 | 1360 | 1 | 0 | 0 | decisions/EmotionalAnalytic/EA_GPT_5.csv |
| GPT_o4 | Neutral | 1360 | 1360 | 1356 | 0.9971 | 4 | 0 | decisions/Neutral/Neutral_GPT_o4.csv |
| GPT_o4 | Neutral-CoT | 1360 | 1360 | 1347 | 0.9904 | 13 | 0 | decisions/Neutral-CoT/Neutral-CoT_GPT_o4.csv |
| GPT_o4 | EI | 1360 | 1360 | 1358 | 0.9985 | 2 | 0 | decisions/EmotionalIntuitive/EI_GPT_o4.csv |
| GPT_o4 | EA | 1360 | 1360 | 1352 | 0.9941 | 8 | 0 | decisions/EmotionalAnalytic/EA_GPT_o4.csv |
| QwenN | Neutral | 1360 | 1360 | 1360 | 1 | 0 | 0 | decisions/Neutral/Neutral_QwenN.csv |
| QwenN | Neutral-CoT | 1360 | 1360 | 1358 | 0.9985 | 2 | 0 | decisions/Neutral-CoT/Neutral-CoT_QwenN.csv |
| QwenN | EI | 1360 | 1360 | 1360 | 1 | 0 | 0 | decisions/EmotionalIntuitive/EI_QwenN.csv |
| QwenN | EA | 1360 | 1360 | 1359 | 0.9993 | 1 | 0 | decisions/EmotionalAnalytic/EA_QwenN.csv |
| QwenT | Neutral | 1360 | 1360 | 1359 | 0.9993 | 1 | 0 | decisions/Neutral/Neutral_QwenT.csv |
| QwenT | Neutral-CoT | 1360 | 1360 | 1360 | 1 | 0 | 0 | decisions/Neutral-CoT/Neutral-CoT_QwenT.csv |
| QwenT | EI | 1360 | 1360 | 1360 | 1 | 0 | 0 | decisions/EmotionalIntuitive/EI_QwenT.csv |
| QwenT | EA | 1360 | 1360 | 1360 | 1 | 0 | 0 | decisions/EmotionalAnalytic/EA_QwenT.csv |
