# Cross-Family Generalization: Replication Summary

Each row compares the new GPT/Qwen estimate (single run, 4 models)
against the paper estimate. Verdict rules:

- Strong: same direction; new estimate within +/- 3 pp (or +/- 30%) of paper.
- Directional: same direction; larger magnitude difference.
- Failure: opposite direction or not significant at alpha=0.05.

| claim | metric | paper | new | verdict |
| --- | --- | --- | --- | --- |
| 1 | Worst single (model, mode) deviation | R1 + EI = 19.44% | QwenT+EI=18.32% | Strong |
| 1 | Cross-model 6-pair agreement gap (Neutral_modes - Emotional_modes, pp) | ~6 pp (Neutral 96.99/95.67 vs EI 90.08/EA 90.82) | -0.60 pp (CI -1.36 to 0.18) | Failure |
| 1 | Thinking - Non-thinking deviation under EI (pp) | DeepSeek-R1 most vulnerable (paper: R1 EI = 19.44 vs CN EI ~13) | +5.21 pp (Thinking GPT_o4+QwenT higher than GPT_5+QwenN under EI) | Strong |
| 2 | Neutral-CoT pooled deviation (pp) | 6.50 pp | 6.92 pp | Strong |
| 2 | Anchoring: EI - EA pooled deviation (pp) | +1.13 pp | +5.11 pp | Directional |
| 2 | Within-family cross-mode agreement: agree(Neutral, Neutral-CoT) | 98.84% | 93.34% | Directional |
| 2 | Within-family cross-mode agreement: agree(EI, EA) | 97.24% | 89.74% | Directional |
| 3 | Pooled deviation EA (pp) | 14.51 pp | 7.12 pp | Directional |
| 3 | Pooled deviation EI (pp) | 15.64 pp | 12.24 pp | Directional |
| 3 | Effect ratio EA / Neutral-CoT | ~2.23 | 1.03 | Directional |
| 3 | Effect ratio EI / Neutral-CoT | ~2.41 | 1.77 | Strong |
| 3 | Paired McNemar p (EA vs Neutral-CoT) | p < 1e-33 (vs Neutral, EA was strongly > Neutral) | p = 5.508e-01 (EA vs Neutral-CoT directly) | Failure |
| 3 | Paired McNemar p (EI vs Neutral-CoT) | p < 1e-24 (vs Neutral; EI shifts much more than reasoning) | p = 3.598e-32 | Strong |
| 4 | EA pooled Choice-1 share on disagree subset | 62.45% (p < .001) | 41.80% (p = 1.668e-03) | Failure |
| 4 | EI pooled Choice-1 share on disagree subset | positive (smaller than EA) | 55.96% (p = 2.426e-03) | Strong |
| 4 | Top-3 topic share of disagreements under EA | ~25-30% (Fig. 5 cluster: business + family + env top three) | 24.34% | Strong |
| 4 | Top-3 topic share of disagreements under EI | ~25-30% (Fig. 5) | 23.83% | Strong |
| 4 | Gini of per-topic drift rates (EA) | (not reported) | 0.126 | Strong |
| 4 | Gini of per-topic drift rates (EI) | (not reported) | 0.113 | Strong |
| 4 | Top-3 worst (model, mode, topic) cells | R1 + EI + business = 33.75%; clusters in business/family/env | QwenT+EI+role_duty_responsibility=25.00%, GPT_5+EI+family=20.00%, GPT_o4+EI+issue_wildlife_human_environment=18.75% | Directional |