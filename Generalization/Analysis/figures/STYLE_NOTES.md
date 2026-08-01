# Figure Style Notes — Unified Paper Aesthetic

All figures in this directory were regenerated to match the visual language of
`DataAnalysis/Perceive` so that figures across the paper (Perceive,
DilemmaValidation, Generalization) appear as a single, coherent set.

Originals are preserved in `_archive_pre_unified_style/` (pre-restyle) and
`_archive_v1_colored/` (the first restyle iteration before the compact
one-column updates).

## Source of style truth

- Palette names + hex values: `DataAnalysis/Perceive/theme_colors.md`
- Reference renderers (style examples): `DataAnalysis/Perceive/render_publication_*.py`
- Local style module: `DataAnalysis/Generalization/Analysis/paper_style.py`

## Shared conventions

- **Font**: Times New Roman (serif), Type-42 PDFs.
- **Spines**: top/right hidden; left/bottom at width 0.7.
- **Grid**: dashed, axis=`y`, linewidth 0.6, alpha 0.22, drawn behind data.
- **Bars**: thin white edges, axis-below grid, value labels in 7–8 pt.
- **Heatmaps**: `LinearSegmentedColormap` from `#FBFBFB` (offwhite) to the
  base theme hue. Cell text switches white/black via a 60% threshold.
- **Save**: dpi=600 PNG plus PDF with white facecolor, both via
  `paper_style.save_publication`.

## Per-figure adaptations

| Figure | Adaptation decision |
| --- | --- |
| `fig_C1_per_model_deviation` | Bars colored by Perceive mode palette (Neutral-CoT=purple, EI=orange, EA=red). **All four model panels now share the same per-mode shade** (the GPT-5 row of `model_shade`, i.e. `darken(mode_color, 0.14)`), so cross-panel comparisons read on bar height alone — Qwen-N, Qwen-T, GPT-5, and o4-mini do not differ in color depth. Black-edged 95% CI whiskers. |
| `fig_C1_cross_model_agreement_by_mode` | 2×2 heatmap (one panel per mode) compacted to single-column width (3.35″). **Two-family tinting**: Neutral and Neutral-CoT share the Neutral hue (blue); EI and EA share the EA hue (red). The shared tint reinforces the calm-baseline / emotional-prompt grouping; the cell values do the work of differentiating modes within each family. Black 0.8 pt border around every panel; inner axes shared so only the bottom row carries x-tick labels and only the left column carries y-tick labels (tick fonts ~6 pt, cell labels ~5.4 pt, titles 8.4 pt) — smaller than the Perceive Refined figure 3 reference per the print-density requirement. `vmin/vmax` = 0.80–1.00 so off-diagonal differences are visible. |
| `fig_C2_cross_mode_agreement_by_model` | Same compact one-column 2×2 layout as fig_C1 but per model. Each panel uses a `MODEL_HEATMAP_COLORS` shade (o4-mini darkest, Qwen-T lightest), exactly mirroring the Perceive figure 1B convention. Canonical model names are used at 8 pt for panel titles; tick labels shrink to 5.4 pt. |
| `fig_C4_topic_drift_heatmap` | Two-panel split layout adapted from Perceive figure 7: 17 topics are sorted by max drift rate (across the two methods) descending; the top 9 occupy the left panel and the bottom 8 the right. A single shared colorbar sits on the right. Cells share `vmin/vmax` so colors are comparable across panels. Method labels along each x-axis are colored by `MODE_BASE_COLORS` and bolded. Y-tick labels use the human-readable topic names (wildlife and environment, responsibility and duty, …) wrapped on two lines for long names. **The Neutral-CoT column was dropped** (it did not change the topic ranking and added a third near-uniform column that diluted the visual signal); only EI and EA are shown. |
| `fig_C4_per_model_worst_topic` | Single-panel grouped bars (EA + EI side-by-side per model), matching Perceive Refined figure 8. EA uses `THEME_ORANGE`, EI uses `THEME_RED`; topic name and percentage are stacked above each bar. Model x-tick labels are bolded. Compact one-column footprint (~3.45″). |

## How to regenerate

```bash
cd DataAnalysis/Generalization/Analysis
python render_generalization_figures.py
```
