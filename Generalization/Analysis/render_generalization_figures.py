"""Render publication-quality figures for the Cross-Family Generalization study.

Modeled on ``DataAnalysis/Perceive/render_publication_figures.py``: reuses
``set_paper_style``, ``MODE_BASE_COLORS`` and ``HEATMAP_CMAP`` and saves every
figure twice (.png at dpi=600 and .pdf with the same bbox).

Figures rendered (every name lands as ``<name>.png`` and ``<name>.pdf`` in
``DataAnalysis/Generalization/Analysis/figures/``):

- ``fig_C1_per_model_deviation``        : per-model deviation bars + 95% CIs
- ``fig_C1_cross_model_agreement_by_mode``: 4-model x 4-model agreement heatmap
                                            (one panel per mode)
- ``fig_C2_cross_mode_agreement_by_model``: 4-mode x 4-mode agreement heatmap
                                            (one panel per model)
- ``fig_C4_topic_drift_heatmap``        : topic_group x {N-CoT, EI, EA} drift
- ``fig_C4_per_model_worst_topic``      : per-model worst-topic bar chart
"""

from __future__ import annotations

import os
from itertools import combinations

os.environ.setdefault("MPLCONFIGDIR", "/tmp/mpl_gen")

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from data_loader import ANALYSIS_DIR, FIGURES_DIR, MODES, NON_NEUTRAL_MODES
from paper_style import (
    MODE_BASE_COLORS,
    MODEL_HEATMAP_COLORS,
    THEME_BLUE,
    THEME_ORANGE,
    THEME_RED,
    light_theme_cmap,
    model_shade,
    save_publication,
    set_paper_style,
    style_axes,
    warm_alignment_cmap,
)


# Canonical paper-facing labels; internal IDs remain unchanged for data access.
MODEL_LABELS = {
    "GPT_5": "GPT-5",
    "GPT_o4": "o4-mini",
    "QwenN": "Qwen-N",
    "QwenT": "Qwen-T",
}
MODEL_LABELS_LONG = {
    "GPT_5": "GPT-5",
    "GPT_o4": "o4-mini",
    "QwenN": "Qwen-N",
    "QwenT": "Qwen-T",
}
MODEL_ORDER = ("GPT_5", "GPT_o4", "QwenN", "QwenT")
MODEL_MARKERS = {"GPT_5": "D", "GPT_o4": "o", "QwenN": "^", "QwenT": "s"}

# Y-tick label remap so the topic_group heatmap reads in plain English.
_TOPIC_LABEL_MAP = {
    "issue_wildlife_human_environment": "wildlife and\nenvironment",
    "issue_crime_addiction": "crime and\naddiction",
    "issue_personal_career": "personal career",
    "issue_pregnancy": "pregnancy",
    "issue_self_image_social": "self image",
    "issue_young_people": "young people",
    "event_special": "special events",
    "event_daily_life": "daily life events",
    "role_duty_responsibility": "responsibility\nand duty",
    "religion_custom": "religion",
    "close_relationship": "close\nrelationship",
    "comitted_relationship": "committed\nrelationship",
    "business_organization": "business\norganization",
    "family": "family",
    "school": "school",
    "workplace": "workplace",
    "friend": "friend",
}


def _pretty_topic(topic: str) -> str:
    return _TOPIC_LABEL_MAP.get(topic, topic.replace("_", " "))


def _short_topic(topic: str) -> str:
    return _pretty_topic(topic).replace("\n", " ")


def _save(fig, name: str) -> None:
    save_publication(fig, FIGURES_DIR, name)
    plt.close(fig)


# ---- Figure 1: per-model deviation bars (Claim 1, analogue of Fig. 4) ----
def fig_c1_per_model_deviation() -> None:
    df = pd.read_csv(ANALYSIS_DIR / "02_claim1_vulnerability.csv")
    df = df[df["mode"].isin(NON_NEUTRAL_MODES)].copy()
    df["deviation_pp"] = df["deviation"] * 100
    df["err_low_pp"] = (df["deviation"] - df["deviation_ci_low"]) * 100
    df["err_high_pp"] = (df["deviation_ci_high"] - df["deviation"]) * 100
    mode_order = ["Neutral-CoT", "EI", "EA"]

    fig, axes = plt.subplots(2, 2, figsize=(7.4, 4.4), sharey=True)
    axes_flat = axes.flatten()
    x_positions = np.arange(len(mode_order))
    width = 0.6

    for ax, model in zip(axes_flat, MODEL_ORDER):
        sub = df[df["model"] == model].set_index("mode").reindex(mode_order).reset_index()
        # Use a single shared shade per mode across every panel so the four
        # model panels are visually comparable; only bar height varies, not
        # color depth. We pin the shade to the GPT-5 row of ``model_shade``
        # (mode_color darkened by 0.14) per the visual brief.
        colors = [model_shade(MODE_BASE_COLORS[m], "GPT_5") for m in mode_order]
        bars = ax.bar(
            x_positions,
            sub["deviation_pp"],
            width=width,
            color=colors,
            edgecolor="white",
            linewidth=0.5,
        )
        ax.errorbar(
            x_positions,
            sub["deviation_pp"],
            yerr=[sub["err_low_pp"], sub["err_high_pp"]],
            fmt="none",
            ecolor="#1f1f1f",
            elinewidth=0.9,
            capsize=2.4,
        )
        ax.set_title(MODEL_LABELS[model], fontsize=10.5, pad=4, fontweight="semibold")
        ax.set_xticks(x_positions)
        ax.set_xticklabels(mode_order, fontsize=8.8)
        ax.tick_params(axis="x", length=0, pad=2)
        ax.tick_params(axis="y", labelsize=8.8)
        style_axes(ax)
        for bar, val, err_hi in zip(bars, sub["deviation_pp"], sub["err_high_pp"]):
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                val + err_hi + 0.4,
                f"{val:.1f}",
                ha="center",
                va="bottom",
                fontsize=7.6,
            )

    y_max = float((df["deviation_pp"] + df["err_high_pp"]).max()) + 2.2
    for ax in axes_flat:
        ax.set_ylim(0.0, y_max)

    axes[0, 0].set_ylabel("Deviation vs Neutral (pp)", fontsize=10.5)
    axes[1, 0].set_ylabel("Deviation vs Neutral (pp)", fontsize=10.5)

    fig.subplots_adjust(left=0.10, right=0.995, top=0.94, bottom=0.10, wspace=0.10, hspace=0.36)
    _save(fig, "fig_C1_per_model_deviation")


# ---- Figure 2: cross-model agreement heatmap, one panel per mode (Claim 1, Fig. 2 analogue) ----
def _draw_publication_heatmap(
    ax,
    matrix,
    labels,
    title,
    *,
    cmap=None,
    vmin: float = 0.80,
    vmax: float = 1.00,
    fmt: str = "{:.1f}%",
    title_fontsize: float = 8.6,
    tick_fontsize: float = 7.2,
    cell_fontsize: float = 6.2,
    x_tick_rotation: float = 0.0,
    x_tick_ha: str = "center",
    show_xticklabels: bool = True,
    show_yticklabels: bool = True,
):
    if cmap is None:
        cmap = light_theme_cmap(THEME_BLUE)
    values = matrix.values.astype(float)
    im = ax.imshow(values, vmin=vmin, vmax=vmax, cmap=cmap)
    ax.set_xticks(range(len(labels)))
    if show_xticklabels:
        ax.set_xticklabels(
            labels,
            rotation=x_tick_rotation,
            ha=x_tick_ha,
            rotation_mode="anchor" if x_tick_rotation else None,
            fontsize=tick_fontsize,
        )
    else:
        ax.set_xticklabels([])
    ax.set_yticks(range(len(labels)))
    if show_yticklabels:
        ax.set_yticklabels(labels, fontsize=tick_fontsize)
    else:
        ax.set_yticklabels([])
    ax.set_title(title, fontsize=title_fontsize, pad=2.0, fontweight="bold")
    ax.set_aspect("equal")
    ax.tick_params(axis="both", length=0, pad=1.2)

    for spine in ("top", "right", "bottom", "left"):
        ax.spines[spine].set_linewidth(0.8)
        ax.spines[spine].set_color("black")
        ax.spines[spine].set_visible(True)

    threshold = vmin + 0.55 * (vmax - vmin)
    for i in range(values.shape[0]):
        for j in range(values.shape[1]):
            v = values[i, j]
            if np.isnan(v):
                ax.text(j, i, "NA", ha="center", va="center", fontsize=cell_fontsize, color="black")
                continue
            color = "white" if v >= threshold else "black"
            ax.text(j, i, fmt.format(v * 100 if vmax <= 1.0 else v), ha="center", va="center", fontsize=cell_fontsize, color=color)
    return im


def _pairwise_agreement_matrix(sub: pd.DataFrame, keys: list[str]) -> pd.DataFrame:
    """Compute the symmetric pairwise agreement matrix over ``keys`` columns."""
    matrix = pd.DataFrame(np.eye(len(keys)), index=keys, columns=keys, dtype=float)
    for left, right in combinations(keys, 2):
        mask = sub[left].notna() & sub[right].notna()
        rate = float((sub.loc[mask, left] == sub.loc[mask, right]).mean()) if mask.sum() else float("nan")
        matrix.loc[left, right] = rate
        matrix.loc[right, left] = rate
    return matrix


def fig_c1_cross_model_agreement_by_mode() -> None:
    """2x2 model-agreement heatmaps, one tile per mode.

    One-column compact (~3.35"); tight panels with shared inner axes,
    smaller font sizes than the Perceive Refined figure 3 reference.
    """
    long_df = pd.read_csv(ANALYSIS_DIR / "gen_long.csv")
    long_df["choice"] = pd.to_numeric(long_df["choice"], errors="coerce")

    # Two-family tinting:
    # - Neutral + Neutral-CoT share the Neutral hue (blue)
    # - EI + EA share the EA hue (red)
    # The cell values do the differentiating between the two modes within
    # each family; the shared tint reinforces the conceptual grouping
    # (calm baseline vs emotional prompt).
    family_cmap = {
        "Neutral": light_theme_cmap(MODE_BASE_COLORS["Neutral"]),
        "Neutral-CoT": light_theme_cmap(MODE_BASE_COLORS["Neutral"]),
        "EI": light_theme_cmap(MODE_BASE_COLORS["EA"]),
        "EA": light_theme_cmap(MODE_BASE_COLORS["EA"]),
    }

    fig, axes = plt.subplots(2, 2, figsize=(3.35, 3.55))
    axes_flat = axes.flatten()
    for idx, (ax, mode) in enumerate(zip(axes_flat, MODES)):
        sub = long_df[long_df["mode"] == mode].pivot_table(
            index="idx", columns="model", values="choice", aggfunc="first"
        ).reindex(columns=list(MODEL_ORDER))
        matrix = _pairwise_agreement_matrix(sub, list(MODEL_ORDER))
        _draw_publication_heatmap(
            ax=ax,
            matrix=matrix,
            labels=[MODEL_LABELS[m] for m in MODEL_ORDER],
            title=mode,
            cmap=family_cmap[mode],
            vmin=0.80,
            vmax=1.00,
            title_fontsize=8.4,
            tick_fontsize=6.0,
            cell_fontsize=5.4,
            x_tick_rotation=0.0,
            x_tick_ha="center",
            show_xticklabels=idx >= 2,
            show_yticklabels=idx % 2 == 0,
        )

    fig.subplots_adjust(left=0.13, right=0.995, top=0.94, bottom=0.13, wspace=0.05, hspace=0.18)
    _save(fig, "fig_C1_cross_model_agreement_by_mode")


# ---- Figure 3: cross-mode agreement heatmap, one panel per model (Claim 2, Fig. 12 analogue) ----
def fig_c2_cross_mode_agreement_by_model() -> None:
    """2x2 mode-agreement heatmaps, one tile per model.

    One-column compact (~3.35"); tight panels with shared inner axes,
    smaller font sizes consistent with fig_C1.
    """
    long_df = pd.read_csv(ANALYSIS_DIR / "gen_long.csv")
    long_df["choice"] = pd.to_numeric(long_df["choice"], errors="coerce")

    fig, axes = plt.subplots(2, 2, figsize=(3.35, 3.55))
    axes_flat = axes.flatten()
    for idx, (ax, model) in enumerate(zip(axes_flat, MODEL_ORDER)):
        sub = long_df[long_df["model"] == model].pivot_table(
            index="idx", columns="mode", values="choice", aggfunc="first"
        ).reindex(columns=list(MODES))
        matrix = _pairwise_agreement_matrix(sub, list(MODES))
        _draw_publication_heatmap(
            ax=ax,
            matrix=matrix,
            labels=list(MODES),
            title=MODEL_LABELS_LONG[model],
            cmap=light_theme_cmap(MODEL_HEATMAP_COLORS[model]),
            vmin=0.80,
            vmax=1.00,
            title_fontsize=8.0,
            tick_fontsize=5.4,
            cell_fontsize=5.4,
            x_tick_rotation=0.0,
            x_tick_ha="center",
            show_xticklabels=idx >= 2,
            show_yticklabels=idx % 2 == 0,
        )

    fig.subplots_adjust(left=0.16, right=0.995, top=0.94, bottom=0.14, wspace=0.05, hspace=0.18)
    _save(fig, "fig_C2_cross_mode_agreement_by_model")


# ---- Figure 4: topic-group drift heatmap (Claim 4, Fig. 5/7 analogue) ----
def fig_c4_topic_drift_heatmap() -> None:
    """Topic-group drift heatmap, split across two columns (Perceive fig 7 layout).

    Topics are sorted by max-mode drift rate descending; the top half goes in
    the left panel, the bottom half in the right panel; a single shared
    colorbar is anchored to the right.
    """
    df = pd.read_csv(ANALYSIS_DIR / "05_claim4_topic_drift.csv")
    # The topic-drift heatmap focuses on the two emotional-prompt
    # variants (EI, EA); the Neutral-CoT comparison column is intentionally
    # dropped (the user's review pointed out it added noise without changing
    # the topic ranking).
    mode_cols = ["EI", "EA"]
    pivot = (
        df.pivot_table(index="topic_group", columns="mode", values="drift_rate", aggfunc="first")
        .reindex(columns=mode_cols)
    )
    pivot = pivot.assign(_max=pivot.max(axis=1)).sort_values("_max", ascending=False).drop(columns=["_max"])
    values_all = pivot.to_numpy(dtype=float) * 100.0
    vmin = float(np.nanmin(values_all))
    vmax = float(np.nanmax(values_all))

    n_topics = len(pivot.index)
    half = int(np.ceil(n_topics / 2.0))
    left_piv = pivot.iloc[:half].copy()
    right_piv = pivot.iloc[half:].copy()

    fig_h = max(3.6, 0.30 * half + 0.6)
    fig, axes = plt.subplots(1, 2, figsize=(5.6, fig_h), gridspec_kw={"width_ratios": [1.0, 1.0]})
    cmap = warm_alignment_cmap()

    mode_color = {m: MODE_BASE_COLORS.get(m, "black") for m in mode_cols}
    threshold = vmin + 0.6 * (vmax - vmin)

    im = None
    for ax, panel in zip(axes, (left_piv, right_piv)):
        values = panel.to_numpy(dtype=float) * 100.0
        im = ax.imshow(values, cmap=cmap, aspect="auto", vmin=vmin, vmax=vmax)

        ax.set_xticks(range(len(mode_cols)))
        ax.set_xticklabels(mode_cols, fontsize=8.4, fontweight="bold")
        for tick, mode in zip(ax.get_xticklabels(), mode_cols):
            tick.set_color(mode_color[mode])

        ylabels = [_pretty_topic(t) for t in panel.index]
        ax.set_yticks(range(len(panel.index)))
        ax.set_yticklabels(ylabels, fontsize=6.4)
        ax.tick_params(axis="x", length=0, pad=2)
        ax.tick_params(axis="y", length=0, pad=1.5)

        for i in range(values.shape[0]):
            for j in range(values.shape[1]):
                v = values[i, j]
                if np.isnan(v):
                    continue
                color = "white" if v >= threshold else "black"
                ax.text(j, i, f"{v:.1f}", ha="center", va="center", fontsize=6.6, color=color)

        for spine in ("top", "right"):
            ax.spines[spine].set_visible(False)
        ax.spines["left"].set_linewidth(0.7)
        ax.spines["bottom"].set_linewidth(0.7)

    cbar = fig.colorbar(im, ax=axes.tolist(), fraction=0.025, pad=0.018)
    cbar.set_label("Drift rate (%)", fontsize=7.0, labelpad=2.5)
    cbar.ax.tick_params(labelsize=6.4, length=1.2)

    fig.subplots_adjust(left=0.12, right=0.90, top=0.985, bottom=0.06, wspace=0.30)
    _save(fig, "fig_C4_topic_drift_heatmap")


# ---- Figure 5: per-model worst-topic bar chart (Claim 4, Fig. 8 analogue) ----
def fig_c4_per_model_worst_topic() -> None:
    """Per-model worst-topic grouped bars (EA + EI side-by-side per model).

    Mirrors Perceive Refined figure 8: single panel, two methods grouped per
    model, topic-name + percentage stacked above each bar. Compact one-column
    layout (~3.45" wide).
    """
    df = pd.read_csv(ANALYSIS_DIR / "05_claim4_worst_topic_per_model.csv")
    df = df[df["mode"].isin(["EA", "EI"])].copy()
    df["drift_pct"] = df["drift_rate"] * 100.0

    methods = ("EA", "EI")
    method_colors = {"EA": THEME_ORANGE, "EI": THEME_RED}
    method_labels = {"EA": "EA", "EI": "EI"}

    group_step = 0.78
    width = 0.30
    x = np.arange(len(MODEL_ORDER)) * group_step

    fig, ax = plt.subplots(figsize=(3.45, 2.55))
    max_val = 0.0
    for idx, mode in enumerate(methods):
        sub = (
            df[df["mode"] == mode]
            .set_index("model")
            .reindex(list(MODEL_ORDER))
            .reset_index()
        )
        vals = sub["drift_pct"].astype(float).to_numpy()
        max_val = max(max_val, float(np.nanmax(vals)))
        offsets = x + (idx - 0.5) * width
        bars = ax.bar(
            offsets,
            vals,
            width=width,
            color=method_colors[mode],
            edgecolor="white",
            linewidth=0.5,
            alpha=0.94,
            label=method_labels[mode],
        )
        for bar, (_, row) in zip(bars, sub.iterrows()):
            topic = _pretty_topic(str(row["worst_topic_group"]))
            rate = float(row["drift_pct"])
            ax.text(
                bar.get_x() + bar.get_width() / 2.0,
                bar.get_height() + 0.35,
                f"{topic}\n{rate:.1f}%",
                ha="center",
                va="bottom",
                fontsize=4.9,
                linespacing=1.0,
            )

    ax.set_xticks(x)
    ax.set_xticklabels([MODEL_LABELS[m] for m in MODEL_ORDER], fontsize=7.8, fontweight="bold")
    ax.set_ylabel("Highest Topic Drift Rate (%)", fontsize=7.8)
    ax.tick_params(axis="x", length=0, pad=2)
    ax.tick_params(axis="y", labelsize=7.0)
    ax.set_ylim(0.0, max(14.0, max_val + 8.2))
    ax.set_xlim(x[0] - 0.42, x[-1] + 0.42)
    style_axes(ax)
    ax.legend(
        frameon=False,
        ncol=2,
        loc="upper left",
        bbox_to_anchor=(0.0, 1.005),
        fontsize=6.6,
        handlelength=1.3,
        columnspacing=1.0,
    )

    fig.subplots_adjust(left=0.16, right=0.995, top=0.88, bottom=0.13)
    _save(fig, "fig_C4_per_model_worst_topic")


def main() -> None:
    set_paper_style()
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    fig_c1_per_model_deviation()
    fig_c1_cross_model_agreement_by_mode()
    fig_c2_cross_mode_agreement_by_model()
    fig_c4_topic_drift_heatmap()
    fig_c4_per_model_worst_topic()
    print(f"Wrote figures to {FIGURES_DIR}")


if __name__ == "__main__":
    main()
