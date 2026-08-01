# Claim 4 - Systematic, topic-concentrated drift

## A. Directional Choice-1 asymmetry on disagree-with-Neutral subset

| model | mode | n_disagree | n_to_1 | n_to_2 | choice1_share | net_shift_to_1 | binomial_p_two_sided |
| --- | --- | --- | --- | --- | --- | --- | --- |
| GPT_5 | Neutral-CoT | 61 | 27 | 34 | 0.4426 | -7 | 0.4426 |
| GPT_o4 | Neutral-CoT | 103 | 39 | 64 | 0.3786 | -25 | 0.0176 |
| QwenN | Neutral-CoT | 72 | 27 | 45 | 0.3750 | -18 | 0.0444 |
| QwenT | Neutral-CoT | 125 | 57 | 68 | 0.4560 | -11 | 0.3712 |
| POOLED | Neutral-CoT | 361 | 150 | 211 | 0.4155 | -61 | 0.0016 |
| GPT_5 | EI | 150 | 99 | 51 | 0.6600 | 48 | 0.0001 |
| GPT_o4 | EI | 152 | 72 | 80 | 0.4737 | -8 | 0.5703 |
| QwenN | EI | 112 | 64 | 48 | 0.5714 | 16 | 0.1561 |
| QwenT | EI | 249 | 136 | 113 | 0.5462 | 23 | 0.1631 |
| POOLED | EI | 663 | 371 | 292 | 0.5596 | 79 | 0.0024 |
| GPT_5 | EA | 63 | 31 | 32 | 0.4921 | -1 | 1 |
| GPT_o4 | EA | 101 | 33 | 68 | 0.3267 | -35 | 0.0006 |
| QwenN | EA | 80 | 30 | 50 | 0.3750 | -20 | 0.0330 |
| QwenT | EA | 134 | 64 | 70 | 0.4776 | -6 | 0.6660 |
| POOLED | EA | 378 | 158 | 220 | 0.4180 | -62 | 0.0017 |
Paper anchor: EA = 62.45% toward Choice 1 (n=2,365, p<.001).

## B. Topic-group drift rate per method (pooled across 4 models)

| topic_group | Neutral-CoT | EI | EA |
| --- | --- | --- | --- |
| family | 9.69 | 17.81 | 10.94 |
| event_daily_life | 9.40 | 12.50 | 9.69 |
| issue_pregnancy | 6.01 | 10.03 | 8.15 |
| close_relationship | 9.09 | 12.54 | 8.15 |
| issue_crime_addiction | 7.86 | 13.84 | 7.26 |
| business_organization | 7.19 | 16.25 | 7.19 |
| issue_wildlife_human_environment | 7.81 | 15.31 | 7.19 |
| issue_personal_career | 6.25 | 8.75 | 7.19 |
| friend | 7.19 | 11.25 | 7.19 |
| religion_custom | 4.09 | 10.94 | 6.88 |
| role_duty_responsibility | 6.60 | 13.52 | 6.62 |
| event_special | 7.89 | 12.54 | 5.97 |
| school | 5.35 | 11.88 | 5.97 |
| workplace | 5.31 | 11.56 | 5.33 |
| comitted_relationship | 3.13 | 8.75 | 5.31 |
| issue_young_people | 5.35 | 10.62 | 5 |
| issue_self_image_social | 5 | 9.38 | 4.39 |
Cells in % (drift = disagrees-with-Neutral / both-valid).

## C. Per-model worst topic

| model | mode | worst_topic_group | n | n_disagree | worst drift rate (%) |
| --- | --- | --- | --- | --- | --- |
| GPT_5 | Neutral-CoT | family | 80 | 8 | 10 |
| GPT_o4 | Neutral-CoT | event_daily_life | 79 | 10 | 12.66 |
| QwenN | Neutral-CoT | business_organization | 80 | 9 | 11.25 |
| QwenT | Neutral-CoT | event_daily_life | 80 | 12 | 15 |
| GPT_5 | EI | family | 80 | 16 | 20 |
| GPT_o4 | EI | issue_wildlife_human_environment | 80 | 15 | 18.75 |
| QwenN | EI | issue_crime_addiction | 80 | 13 | 16.25 |
| QwenT | EI | role_duty_responsibility | 80 | 20 | 25 |
| GPT_5 | EA | family | 80 | 9 | 11.25 |
| GPT_o4 | EA | issue_crime_addiction | 77 | 11 | 14.29 |
| QwenN | EA | event_daily_life | 80 | 9 | 11.25 |
| QwenT | EA | business_organization | 80 | 10 | 12.50 |
Paper anchor (Fig. 11): R1 + EI + business_organization = 33.75%.

## D. Concentration metrics (per topic-group pooled across models)

| mode | n_topics | n_total_disagreements | top3_topic_share_of_disagreements | gini_over_drift_rates | max_topic_drift_rate | max_topic_group |
| --- | --- | --- | --- | --- | --- | --- |
| Neutral-CoT | 17 | 361 | 0.2493 | 0.1536 | 0.0969 | family |
| EI | 17 | 663 | 0.2383 | 0.1132 | 0.1781 | family |
| EA | 17 | 378 | 0.2434 | 0.1257 | 0.1094 | family |

## E. Cramer's V (mode / model / topic_group -> disagree)

| factor | cramers_v | chi2_p_value |
| --- | --- | --- |
| mode | 0.0907 | 0.0000 |
| model | 0.0856 | 0.0000 |
| topic_group | 0.0619 | 0.0000 |
Paper anchor (Fig. 7 left, on flip rate not disagreement): topic_group > model > mode in marginal strength.
