# Figure Style Notes — Unified Paper Aesthetic

All figures in this directory were regenerated to match the visual language of
`DataAnalysis/Perceive` so that figures across the paper (Perceive,
DilemmaValidation, Generalization) appear as a single, coherent set.

Originals are preserved in `_archive_pre_unified_style/` (pre-restyle),
`_archive_v1_colored/` (the first restyle iteration before the pattern-based
update), and `_archive_v2/` (after patterns but before the one-column
compaction pass).

## Source of style truth

- Palette names + hex values: `DataAnalysis/Perceive/theme_colors.md`
- Reference renderers (style examples): `DataAnalysis/Perceive/render_publication_*.py`
- Local style module: `DataAnalysis/DilemmaValidation/paper_style.py`

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
| `bar_mean_item_quality` | One base hue (`THEME_BLUE`) with **architecture-family hatch patterns** instead of separate hues per variant: Claude = solid, DeepSeek = `//`, GPT = `..`, Qwen = `xx`. The Excellent grade line uses a neutral slate (`#5C6068`) so the dashed line stays legible over the blue bars. **Y-axis is truncated to 0.50–1.00** so the inter-variant differences (data lives in 0.85–0.96) take up most of the plot height; Marginal/Good/Excellent grade lines are all visible. **One-column footprint (3.45″ × 2.6″)** with rotated x-tick labels and a compact 2-row legend. |
| `dist_item_quality_grid` | **2×4 grid (2 columns × 4 rows)** so the figure fits a one-column footprint (3.45″ × 4.6″). Per-variant family fill color matches the family palette. The rightmost x-tick label is hidden on each panel so the shared bottom axis does not collide with the next panel's leftmost label. |
| `heatmap_semantic_pass_rate` | **Reshaped from a 1×8 wide strip into a 4×2 grid** so the figure fits one-column publication width (~3.35″). Each cell carries the variant label and the pass-rate value stacked vertically. Light-to-blue gradient (`vmin/vmax` = 0.85–1.00) so the small differences are still readable. |
| `reliability_bars` | **Pattern-only (no color fill)**: bars are white with a thin black border and black hatches. The three metrics are distinguished entirely by hatch (`semantic_sim` = solid, `emotion_naturalness` = `////`, `emotion_coherence` = `xxxx`). Acceptable-threshold line is a neutral gray dashed line; legend on a single row above the title. Compact figsize 7.0″ × 2.4″. This is the most aggressive greyscale styling in the paper and is meant to print well in monochrome reproductions. |
| `figure_ranking_critical_difference` | Demšar CD diagram in the paper palette (CD bar + significance cliques in `THEME_BLUE`; small family-colored dots at each rank position). **Compact one-column footprint (3.45″ × 2.55″)** with reduced label/tick font sizes (7.0–7.4 pt). |
| `figure_ranking_subdimensions` | **Three vertical rows** of CD diagrams in a one-column footprint (3.45″ × 4.65″, 1.55″ per row). Tick/label fonts shrink to 5.8–6.0 pt so all 8 variants fit per row. Same CD-diagram styling as the main figure. |

### Why patterns instead of colors

The bar charts that compare per-variant scores (`bar_mean_item_quality`,
`reliability_bars`) previously used the family palette (blue / purple / orange /
red). Two reasons motivated the switch to a single hue + hatch pattern:

1. The family palette is reserved on the rest of the paper for the *mode*
   axis (Neutral / Neutral-CoT / EI / EA). Reusing it on the variant axis
   created an implicit visual collision with the rest of the figures.
2. Greyscale and color-blind reproductions of the paper preserve hatch
   patterns but lose hue distinctions; the new bars are robust under both.

## How to regenerate

```bash
cd DataAnalysis/DilemmaValidation
python generate_report.py      # bar / dist / heatmap / reliability
python analyze_ranking.py      # critical-difference + subdimensions
```
