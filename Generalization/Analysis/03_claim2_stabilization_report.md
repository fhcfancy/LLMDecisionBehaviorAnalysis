# Claim 2 - Reasoning stabilizes choices

Action bias (the swap counterfactual) is outside the scope of this study by design.
All evidence here is agreement-based.

## A. Neutral-CoT preserves Neutral (per-model deviation)

| model | mode | EfA | CMR | deviation_pp |
| --- | --- | --- | --- | --- |
| GPT_5 | Neutral-CoT | 0.9551 | 0.9551 | 4.4853 |
| GPT_5 | EI | 0.8897 | 0.8897 | 11.0294 |
| GPT_5 | EA | 0.9537 | 0.9537 | 4.6324 |
| GPT_o4 | Neutral-CoT | 0.9145 | 0.9233 | 8.5546 |
| GPT_o4 | EI | 0.8864 | 0.8877 | 11.3569 |
| GPT_o4 | EA | 0.9196 | 0.9251 | 8.0383 |
| QwenN | Neutral-CoT | 0.9456 | 0.9470 | 5.4412 |
| QwenN | EI | 0.9176 | 0.9176 | 8.2353 |
| QwenN | EA | 0.9404 | 0.9411 | 5.9559 |
| QwenT | Neutral-CoT | 0.9080 | 0.9080 | 9.1979 |
| QwenT | EI | 0.8168 | 0.8168 | 18.3223 |
| QwenT | EA | 0.9014 | 0.9014 | 9.8602 |

Mean per-model deviation (pp): Neutral-CoT = 6.92, EI = 12.24, EA = 7.12.
Paper benchmark: Neutral-CoT 6.50 pp << EA 14.51 pp / EI 15.64 pp.

## B. EA anchors EI under emotion (paired)

| model | n_paired | dev_ei | dev_ea | ei_minus_ea_pp | diff_ci_low_pp | diff_ci_high_pp | mcnemar_b_ea_agrees_ei_disagrees | mcnemar_c_ea_disagrees_ei_agrees | mcnemar_p |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| GPT_5 | 1360 | 0.1103 | 0.0463 | 6.3971 | 4.8529 | 7.7941 | 99 | 12 | 0.0000 |
| GPT_o4 | 1356 | 0.1136 | 0.0804 | 3.3186 | 1.4749 | 5.1622 | 99 | 54 | 0.0004 |
| QwenN | 1360 | 0.0824 | 0.0596 | 2.2794 | 0.9559 | 3.6765 | 60 | 29 | 0.0015 |
| QwenT | 1359 | 0.1832 | 0.0986 | 8.4621 | 6.4753 | 10.5960 | 164 | 49 | 0.0000 |
| POOLED | 5435 | 0.1224 | 0.0712 | 5.1150 | 4.2502 | 5.9618 | 422 | 144 | 0.0000 |
Paper benchmark: pooled EI 15.64 pp vs EA 14.51 pp -> +1.13 pp anchoring (EI - EA).

## C. Cross-mode within-family agreement (per model and pooled)

| model | agreement_Neutral_vs_NCoT | agreement_EI_vs_EA | n_NCoT_pair | n_EIEA_pair | NCoT_ci_low | NCoT_ci_high | EIEA_ci_low | EIEA_ci_high |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| GPT_5 | 0.9551 | 0.9184 | 1360 | 1360 |  |  |  |  |
| GPT_o4 | 0.9233 | 0.8927 | 1343 | 1351 |  |  |  |  |
| QwenN | 0.9470 | 0.9352 | 1358 | 1359 |  |  |  |  |
| QwenT | 0.9080 | 0.8434 | 1359 | 1360 |  |  |  |  |
| POOLED | 0.9334 | 0.8974 | 5420 | 5430 | 0.9264 | 0.9397 | 0.8891 | 0.9059 |
Paper benchmark: agree(Neutral, Neutral-CoT) = 98.84%; agree(EI, EA) = 97.24%.

## D. Cross-model 6-pair mean agreement per mode

| mode | n_pairs | mean_n_compared | mean_pair_agreement_pct | min_pair_agreement_pct | max_pair_agreement_pct |
| --- | --- | --- | --- | --- | --- |
| Neutral | 6 | 1357.50 | 84.36 | 81.40 | 86.95 |
| Neutral-CoT | 6 | 1352.50 | 85.89 | 83.22 | 87.78 |
| EI | 6 | 1359 | 84.68 | 81.08 | 89.03 |
| EA | 6 | 1355.50 | 86.68 | 83.88 | 89.79 |
Stabilization sign check: agreement(Neutral-CoT) > agreement(Neutral)?  agreement(EA) > agreement(EI)?
Paper baseline: Neutral 96.99%, Neutral-CoT 95.67%, EI 90.08%, EA 90.82%.
