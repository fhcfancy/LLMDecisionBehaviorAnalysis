# Claim 3 - Emotion shifts decisions much more than reasoning

## Pooled summary

| metric | value | ci_low_pp | ci_high_pp | n |
| --- | --- | --- | --- | --- |
| Pooled deviation EA (pp) | 7.1205 | 6.4581 | 7.8197 | 5435 |
| Pooled deviation EI (pp) | 12.2355 | 11.3155 | 13.1923 | 5435 |
| Pooled deviation Neutral-CoT (pp) | 6.9181 | 6.2374 | 7.6362 | 5435 |
| EA - Neutral-CoT (pp, paired) | 0.2024 | -0.3316 | 0.7912 | 5435 |
| EI - Neutral-CoT (pp, paired) | 5.3174 | 4.4342 | 6.2006 | 5435 |
| Effect ratio EA/Neutral-CoT | 1.0293 | 0.9534 | 1.1196 | 5435 |
| Effect ratio EI/Neutral-CoT | 1.7686 | 1.6088 | 1.9454 | 5435 |
| Paired McNemar (EA vs Neutral-CoT) pooled: b | 135 |  |  | 281 |
| Paired McNemar (EA vs Neutral-CoT) pooled: c | 146 |  |  | 281 |
| Paired McNemar (EA vs Neutral-CoT) pooled: p | 0.5508 |  |  | 281 |
| Paired McNemar (EI vs Neutral-CoT) pooled: b | 153 |  |  | 595 |
| Paired McNemar (EI vs Neutral-CoT) pooled: c | 442 |  |  | 595 |
| Paired McNemar (EI vs Neutral-CoT) pooled: p | 0.0000 |  |  | 595 |

## Per-model McNemar 2x2 (EA vs Neutral-CoT)

| model | n_paired | dev_ea_pp | dev_ncot_pp | b_ea_agrees_ncot_disagrees | c_ea_disagrees_ncot_agrees | mcnemar_p |
| --- | --- | --- | --- | --- | --- | --- |
| GPT_5 | 1360 | 4.6324 | 4.4853 | 13 | 15 | 0.8501 |
| GPT_o4 | 1356 | 8.0383 | 8.5546 | 56 | 49 | 0.5582 |
| QwenN | 1360 | 5.9559 | 5.4412 | 25 | 32 | 0.4268 |
| QwenT | 1359 | 9.8602 | 9.1979 | 41 | 50 | 0.4017 |

## Per-model McNemar 2x2 (EI vs Neutral-CoT)

| model | n_paired | dev_ncot_pp | mcnemar_p | dev_ei_pp | b_ei_agrees_ncot_disagrees | c_ei_disagrees_ncot_agrees |
| --- | --- | --- | --- | --- | --- | --- |
| GPT_5 | 1360 | 4.4853 | 0.0000 | 11.0294 | 15 | 104 |
| GPT_o4 | 1356 | 8.5546 | 0.0032 | 11.3569 | 60 | 98 |
| QwenN | 1360 | 5.4412 | 0.0002 | 8.2353 | 29 | 67 |
| QwenT | 1359 | 9.1979 | 0.0000 | 18.3223 | 49 | 173 |

## Paper anchors

- Pooled deviation in paper: EA 14.51 pp, EI 15.64 pp, Neutral-CoT 6.50 pp.
- Paper paired McNemar p (EA vs Neutral): 1.18e-33; (EI vs Neutral): 1.78e-24.
- Effect ratio EA/Neutral-CoT in paper: ~2.23; EI/Neutral-CoT: ~2.41.
