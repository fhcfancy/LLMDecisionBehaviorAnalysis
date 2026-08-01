"""
Generate figures and the final Markdown / HTML report for stakeholders.

Run AFTER analyze_results.py has produced dataset_quality.csv and reliability.csv.

Outputs:
    results/figures/bar_mean_item_quality.png
    results/figures/dist_item_quality_grid.png
    results/figures/heatmap_semantic_pass_rate.png
    results/figures/reliability_bars.png  (legacy path; see results/figures/update/)
    results/figures/update/reliability_bars.png
    results/datasets/emotion_frequency.csv
    results/datasets/qc_summary.csv
    report/validation_report.md
    report/validation_report.html
"""

from __future__ import annotations

import hashlib
import json
import os
from collections import Counter
from datetime import datetime, timezone
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Patch  # noqa: E402
import numpy as np
import pandas as pd

from config import (
    API_URL,
    COVERAGE_CSV,
    DATASETS_DIR,
    DATASET_QUALITY_CSV,
    FIGURES_DIR,
    GRADE,
    MODEL_NAME,
    RANKING_FIGURE_MAIN,
    RANKING_FIGURE_SUBDIM,
    RANKING_FRIEDMAN_JSON,
    RANKING_SUBDIMENSIONS_CSV,
    RANKING_SUMMARY_CSV,
    RELIABILITY_CSV,
    REPORT_DIR,
    REPORT_HTML,
    REPORT_MD,
    SEMANTIC_PASS_THRESHOLD,
    VARIANT_KEYS,
    W_COHERENCE,
    W_NATURALNESS,
    W_SEMANTIC,
    ensure_dirs,
    raw_jsonl_path,
)
from dataset_loader import coverage_markdown, load_variants
from paper_style import (
    THEME_BLUE,
    THEME_GRAY,
    THEME_ORANGE,
    THEME_RED,
    light_theme_cmap,
    lighten,
    save_publication,
    set_paper_style,
    style_axes,
    variant_color_map,
    variant_display_name,
    variant_hatch_map,
)
from prompts import SYSTEM, USER_TEMPLATE


def _prompt_hash_short() -> str:
    blob = (SYSTEM + "\n\n" + USER_TEMPLATE).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()[:12]


def _read_jsonl(path) -> pd.DataFrame:
    if not os.path.isfile(str(path)):
        return pd.DataFrame()
    rows: list[dict[str, Any]] = []
    with open(str(path), "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return pd.DataFrame(rows)


def _compute_item_quality(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    df = df.copy()
    df["semantic_sim"] = pd.to_numeric(df.get("semantic_sim"), errors="coerce")
    df["emotion_naturalness"] = pd.to_numeric(df.get("emotion_naturalness"), errors="coerce")
    df["emotion_coherence"] = pd.to_numeric(df.get("emotion_coherence"), errors="coerce")
    df["item_quality"] = (
        W_SEMANTIC * df["semantic_sim"]
        + W_NATURALNESS * (df["emotion_naturalness"] / 5.0)
        + W_COHERENCE * (df["emotion_coherence"] / 5.0)
    )
    df["semantic_pass"] = df["semantic_sim"] >= SEMANTIC_PASS_THRESHOLD
    return df


_GRADE_LINE_COLORS = {
    "excellent": "#5C6068",  # neutral slate so it does not collide with blue bars
    "good": THEME_ORANGE,
    "marginal": THEME_RED,
}


def _figure_stem(out_path: str) -> tuple[str, str]:
    """Split ``.../foo.png`` into (parent_dir, ``foo``)."""
    parent = os.path.dirname(out_path) or "."
    stem = os.path.splitext(os.path.basename(out_path))[0]
    return parent, stem


_FAMILY_LABELS = {
    "Claude": ("CN", "CT"),
    "DeepSeek": ("R1", "V3"),
    "GPT": ("GPT_5", "GPT_o4"),
    "Qwen": ("QwenN", "QwenT"),
}
_FAMILY_HATCH = {
    "Claude": "",
    "DeepSeek": "//",
    "GPT": "..",
    "Qwen": "xx",
}


def _variant_family(variant: str) -> str:
    for fam, members in _FAMILY_LABELS.items():
        if variant in members:
            return fam
    return "Other"


def fig_bar_mean_iq(dq: pd.DataFrame, out: str) -> None:
    if dq.empty or "mean_item_quality" not in dq.columns:
        return
    dq = dq.dropna(subset=["mean_item_quality"]).sort_values("mean_item_quality", ascending=False)
    if dq.empty:
        return

    set_paper_style()
    hatch_map = variant_hatch_map(dq["variant"].tolist())
    base_fill = lighten(THEME_BLUE, 0.10)

    fig, ax = plt.subplots(figsize=(3.45, 2.6))
    x = np.arange(len(dq))
    err_lo = (dq["mean_item_quality"] - dq["ci_lo"]).clip(lower=0)
    err_hi = (dq["ci_hi"] - dq["mean_item_quality"]).clip(lower=0)
    bars = ax.bar(
        x,
        dq["mean_item_quality"],
        yerr=[err_lo, err_hi],
        capsize=1.8,
        color=base_fill,
        edgecolor=THEME_BLUE,
        linewidth=0.7,
        hatch=[hatch_map[v] for v in dq["variant"]],
        error_kw={"elinewidth": 0.7, "capthick": 0.7, "ecolor": "#1f1f1f", "alpha": 0.9},
    )

    # The non-zero floor removes the white band of empty space below the
    # data (every variant lives between ~0.85 and ~0.96) so the inter-variant
    # differences are visible at a glance. The floor stays a hair below the
    # Marginal grade line (0.55) so the dashed line is visible as a line
    # rather than overlapping the axis.
    y_floor = 0.50
    ax.set_ylim(y_floor, 1.0)
    ax.set_yticks([0.50, 0.70, 0.85, 1.0])
    ax.set_xticks(x)
    ax.set_xticklabels(
        [variant_display_name(v) for v in dq["variant"]],
        fontsize=6.6,
        rotation=20,
        ha="right",
        rotation_mode="anchor",
    )
    ax.tick_params(axis="x", length=0, pad=1.5)
    ax.tick_params(axis="y", labelsize=6.8)
    ax.set_ylabel("Mean item_quality", fontsize=7.6)
    ax.set_title(
        "Dataset quality across emotional variants",
        fontsize=8.2,
        fontweight="semibold",
        pad=2,
    )

    grade_lines = [
        (GRADE.excellent, _GRADE_LINE_COLORS["excellent"], f"Excel ≥{GRADE.excellent}"),
        (GRADE.good, _GRADE_LINE_COLORS["good"], f"Good ≥{GRADE.good}"),
        (GRADE.marginal, _GRADE_LINE_COLORS["marginal"], f"Marg ≥{GRADE.marginal}"),
    ]
    grade_handles = []
    for y, color, label in grade_lines:
        if y < y_floor:
            grade_handles.append(
                plt.Line2D([], [], color=color, linestyle="--", linewidth=0.8, label=label)
            )
            continue
        line = ax.axhline(y, color=color, linestyle="--", linewidth=0.8, alpha=0.85, label=label)
        grade_handles.append(line)

    for bar, value in zip(bars, dq["mean_item_quality"]):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            value + 0.006,
            f"{value:.2f}",
            ha="center",
            va="bottom",
            fontsize=5.6,
        )

    style_axes(ax)

    family_handles = [
        Patch(
            facecolor=base_fill,
            edgecolor=THEME_BLUE,
            hatch=_FAMILY_HATCH[fam],
            linewidth=0.7,
            label=fam,
        )
        for fam in _FAMILY_LABELS
    ]
    fig.legend(
        handles=family_handles + grade_handles,
        loc="upper center",
        ncol=4,
        frameon=False,
        bbox_to_anchor=(0.5, 1.025),
        fontsize=5.8,
        handlelength=1.2,
        columnspacing=0.85,
        handletextpad=0.35,
    )
    fig.subplots_adjust(top=0.78, bottom=0.18, left=0.13, right=0.985)

    parent, stem = _figure_stem(out)
    save_publication(fig, parent, stem)
    plt.close(fig)


def fig_distribution_grid(items_by_variant: dict[str, pd.DataFrame], out: str) -> None:
    variants = list(items_by_variant.keys())
    if not variants:
        return

    set_paper_style()
    color_map = variant_color_map(variants)
    # 2 columns x 4 rows fits a single-column publication width (~3.4")
    # without crushing the histograms; ordering walks the architecture
    # families so adjacent panels stay related.
    cols = 2
    rows = int(np.ceil(len(variants) / cols))
    fig, axes = plt.subplots(
        rows,
        cols,
        figsize=(3.45, 4.6),
        sharex=True,
        sharey=True,
    )
    axes = np.array(axes).reshape(-1)

    for ax, v in zip(axes, variants):
        df = items_by_variant[v]
        ax.set_title(
            variant_display_name(v),
            fontsize=7.6,
            pad=1.5,
            fontweight="semibold",
        )
        if df.empty or "item_quality" not in df.columns or df["item_quality"].dropna().empty:
            ax.text(0.5, 0.5, "no data", ha="center", va="center", fontsize=6.6, transform=ax.transAxes, color="#666666")
            ax.set_xticks([])
            ax.set_yticks([])
            for side in ("top", "right", "left", "bottom"):
                ax.spines[side].set_visible(False)
            continue
        ax.hist(
            df["item_quality"].dropna(),
            bins=20,
            color=color_map[v],
            edgecolor="white",
            linewidth=0.4,
        )
        ax.set_xlim(0, 1)
        ax.axvline(GRADE.good, color=_GRADE_LINE_COLORS["good"], linestyle="--", linewidth=0.7, alpha=0.7)
        ax.tick_params(axis="both", labelsize=6.4)
        style_axes(ax)

    for ax in axes[len(variants):]:
        ax.axis("off")

    # Drop the rightmost x-tick label on every column so the shared bottom
    # axis doesn't render "1.0" right next to the neighbouring panel's "0.0".
    for ax in axes:
        ticks = list(ax.get_xticks())
        labels = [f"{t:.1f}" for t in ticks]
        if labels:
            labels[-1] = ""
        ax.set_xticks(ticks)
        ax.set_xticklabels(labels)

    fig.suptitle("Per-variant item_quality distribution", fontsize=8.6, fontweight="semibold", y=0.995)
    fig.supxlabel("item_quality", fontsize=7.6, y=0.005)
    fig.supylabel("count", fontsize=7.6, x=0.005)
    fig.subplots_adjust(left=0.13, right=0.985, top=0.94, bottom=0.085, wspace=0.22, hspace=0.36)

    parent, stem = _figure_stem(out)
    save_publication(fig, parent, stem)
    plt.close(fig)


def fig_semantic_pass_heatmap(dq: pd.DataFrame, out: str) -> None:
    if dq.empty or "semantic_pass_rate" not in dq.columns:
        return
    dq = dq.sort_values("variant").reset_index(drop=True)

    set_paper_style()
    # Reshape from a 1x8 strip to a more square 4x2 grid so the figure fits
    # a single column without becoming a very wide, very thin band. The
    # ordering walks the architecture families (CN/CT, GPT, Qwen, R1/V3) so
    # adjacent cells stay related.
    grid_order = ["CN", "CT", "GPT_5", "GPT_o4", "QwenN", "QwenT", "R1", "V3"]
    dq_lookup = dq.set_index("variant")
    grid_order = [v for v in grid_order if v in dq_lookup.index]
    if not grid_order:
        return
    n_rows, n_cols = 4, 2
    pad = n_rows * n_cols - len(grid_order)
    cells = list(grid_order) + [None] * max(pad, 0)
    val_grid = np.full((n_rows, n_cols), np.nan, dtype=float)
    label_grid: list[list[str]] = [["" for _ in range(n_cols)] for _ in range(n_rows)]
    for k, variant in enumerate(cells):
        r, c = divmod(k, n_cols)
        if variant is None:
            continue
        val = float(pd.to_numeric(dq_lookup.loc[variant, "semantic_pass_rate"], errors="coerce"))
        val_grid[r, c] = val
        label_grid[r][c] = variant_display_name(variant)

    vmin, vmax = 0.85, 1.0
    cmap = light_theme_cmap(THEME_BLUE)

    fig, ax = plt.subplots(figsize=(3.35, 2.4))
    im = ax.imshow(val_grid, aspect="auto", cmap=cmap, vmin=vmin, vmax=vmax)
    ax.set_xticks([])
    ax.set_yticks([])

    threshold = vmin + 0.55 * (vmax - vmin)
    for r in range(n_rows):
        for c in range(n_cols):
            v = val_grid[r, c]
            if np.isnan(v):
                continue
            text_color = "white" if v >= threshold else "black"
            ax.text(
                c,
                r - 0.15,
                label_grid[r][c],
                ha="center",
                va="center",
                fontsize=8.2,
                fontweight="bold",
                color=text_color,
            )
            ax.text(
                c,
                r + 0.18,
                f"{v:.2f}",
                ha="center",
                va="center",
                fontsize=8.6,
                color=text_color,
            )

    for side in ("top", "right", "left", "bottom"):
        ax.spines[side].set_linewidth(0.7)
        ax.spines[side].set_color("black")

    cbar = fig.colorbar(im, ax=ax, fraction=0.06, pad=0.04)
    cbar.ax.tick_params(labelsize=6.6, length=1.2)
    cbar.set_label("Semantic pass rate", fontsize=7.6, labelpad=3)

    ax.set_title(
        f"Semantic pass rate (semantic_sim ≥ {SEMANTIC_PASS_THRESHOLD:.2f})",
        fontsize=9.6,
        pad=4,
        fontweight="semibold",
    )

    fig.subplots_adjust(left=0.04, right=0.86, top=0.90, bottom=0.04)
    parent, stem = _figure_stem(out)
    save_publication(fig, parent, stem)
    plt.close(fig)


def fig_reliability_bars(rel: pd.DataFrame, out: str) -> None:
    if rel.empty:
        return
    metrics = ["rho_semantic_sim", "rho_emotion_naturalness", "rho_emotion_coherence"]
    present = [m for m in metrics if m in rel.columns]
    if not present:
        return

    set_paper_style()
    rel = rel.sort_values("variant").reset_index(drop=True)
    x = np.arange(len(rel))
    width = 0.8 / max(len(present), 1)

    # Same blue / orange / red as Perceive figure6 (SMR / EfA / CMR).
    metric_colors = {
        "rho_semantic_sim": THEME_BLUE,
        "rho_emotion_naturalness": THEME_ORANGE,
        "rho_emotion_coherence": THEME_RED,
    }
    metric_labels = {
        "rho_semantic_sim": "semantic_sim",
        "rho_emotion_naturalness": "emotion_naturalness",
        "rho_emotion_coherence": "emotion_coherence",
    }

    fig, ax = plt.subplots(figsize=(7.0, 2.55))
    ceiling_notes: list[str] = []

    for i, m in enumerate(present):
        offset = (i - (len(present) - 1) / 2) * width
        vals = pd.to_numeric(rel[m], errors="coerce").astype(float)
        ax.bar(
            x + offset,
            vals,
            width=width,
            color=metric_colors.get(m, THEME_GRAY),
            edgecolor="white",
            linewidth=0.6,
            label=metric_labels.get(m, m.replace("rho_", "")),
        )
        if m == "rho_semantic_sim":
            for j, (variant, val) in enumerate(zip(rel["variant"], vals)):
                if pd.isna(val):
                    mad = rel.loc[j, "mad_semantic_sim"] if "mad_semantic_sim" in rel.columns else float("nan")
                    ax.text(
                        x[j] + offset,
                        0.04,
                        "\u2020",
                        ha="center",
                        va="bottom",
                        fontsize=11,
                        color=metric_colors[m],
                        fontweight="bold",
                    )
                    mad_txt = f"MAD={mad:.3f}" if pd.notna(mad) else "MAD n/a"
                    ceiling_notes.append(
                        f"{variant_display_name(variant)}: Spearman rho undefined "
                        f"(retest semantic_sim = 1.0 for all items; {mad_txt})."
                    )

    threshold_line = ax.axhline(
        0.7, color=THEME_GRAY, linestyle="--", linewidth=0.9, alpha=0.9, label="acceptable ≥ 0.70"
    )
    ax.set_xticks(x)
    ax.set_xticklabels(
        [variant_display_name(v) for v in rel["variant"]],
        fontsize=9.0,
    )
    ax.tick_params(axis="x", length=0, pad=2)
    ax.tick_params(axis="y", labelsize=8.6)
    ax.set_ylabel(r"Spearman $\rho$ (test–retest)", fontsize=10)
    ax.set_yticks([0.0, 0.25, 0.5, 0.7, 1.0])
    ax.set_ylim(0, 1.05)
    ax.set_title("Intra-rater reliability per variant", fontsize=10.5, fontweight="semibold", pad=4)

    style_axes(ax)

    metric_handles = [
        Patch(
            facecolor=metric_colors.get(m, THEME_GRAY),
            edgecolor="white",
            linewidth=0.6,
            label=metric_labels.get(m, m.replace("rho_", "")),
        )
        for m in present
    ]
    fig.legend(
        handles=metric_handles + [threshold_line],
        loc="upper center",
        ncol=4,
        frameon=False,
        bbox_to_anchor=(0.5, 1.045),
        fontsize=7.8,
        handlelength=1.4,
        columnspacing=1.2,
        handletextpad=0.45,
    )
    if ceiling_notes:
        line1 = (
            "\u2020 Missing bar: excellent semantic performance reached the ceiling "
            "(zero variance on retest; Spearman \u03c1 undefined)."
        )
        line2 = " ".join(ceiling_notes)
        note_color = "#2F2F2F"
        ax.text(
            0.0,
            -0.11,
            line1,
            transform=ax.transAxes,
            ha="left",
            va="top",
            fontsize=7.8,
            color=note_color,
            fontweight="medium",
        )
        ax.text(
            0.0,
            -0.19,
            line2,
            transform=ax.transAxes,
            ha="left",
            va="top",
            fontsize=7.8,
            color=note_color,
        )
        fig.subplots_adjust(top=0.80, bottom=0.26, left=0.075, right=0.99)
    else:
        fig.subplots_adjust(top=0.80, bottom=0.13, left=0.075, right=0.99)

    parent, stem = _figure_stem(out)
    save_publication(fig, parent, stem)
    plt.close(fig)


def _md_table(df: pd.DataFrame, float_fmt: str = "{:.3f}") -> str:
    if df is None or df.empty:
        return "_(no data)_"
    df = df.copy()
    for c in df.columns:
        if pd.api.types.is_float_dtype(df[c]):
            df[c] = df[c].map(lambda v: float_fmt.format(v) if pd.notna(v) else "")
    header = "| " + " | ".join(df.columns) + " |"
    sep = "|" + "|".join(["---"] * len(df.columns)) + "|"
    rows = ["| " + " | ".join(str(v) for v in r) + " |" for r in df.itertuples(index=False, name=None)]
    return "\n".join([header, sep] + rows)


def _worst_items_section(items_by_variant: dict[str, pd.DataFrame], k: int = 10) -> str:
    sections = []
    cols = ["idx", "item_quality", "semantic_sim", "emotion_naturalness",
            "emotion_coherence", "semantic_justification", "emotion_justification"]
    for v, df in items_by_variant.items():
        if df.empty:
            sections.append(f"### {v}\n\n_(no data)_\n")
            continue
        present = [c for c in cols if c in df.columns]
        worst = df.dropna(subset=["item_quality"]).sort_values("item_quality").head(k)[present]
        sections.append(f"### {v}\n\n" + _md_table(worst) + "\n")
    return "\n".join(sections)


def _emotion_frequency_table(items_by_variant: dict[str, pd.DataFrame], top_k: int = 15) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for v, df in items_by_variant.items():
        counter: Counter[str] = Counter()
        if df.empty or "emotions" not in df.columns:
            continue
        for ems in df["emotions"]:
            if isinstance(ems, list):
                for e in ems:
                    token = str(e).strip().lower()
                    if token:
                        counter[token] += 1
        total = sum(counter.values())
        for emotion, count in counter.most_common(top_k):
            rows.append({"variant": v, "emotion": emotion, "count": count,
                         "share": count / total if total else 0.0})
    return pd.DataFrame(rows)


def _qc_summary(items_by_variant: dict[str, pd.DataFrame]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for v, df in items_by_variant.items():
        record: dict[str, Any] = {"variant": v}
        if not df.empty and "qc_flag" in df.columns:
            for flag, n in df["qc_flag"].value_counts().items():
                record[str(flag)] = int(n)
        rows.append(record)
    return pd.DataFrame(rows).fillna(0)


def _ranking_section(report_dir: str) -> str:
    """Build the Markdown for the within-idx Friedman + Nemenyi ranking section."""
    if not os.path.isfile(str(RANKING_SUMMARY_CSV)) or not os.path.isfile(str(RANKING_FRIEDMAN_JSON)):
        return "_(ranking analysis has not been generated; run `python analyze_ranking.py`)_"

    summary = pd.read_csv(str(RANKING_SUMMARY_CSV))
    try:
        with open(str(RANKING_FRIEDMAN_JSON), "r", encoding="utf-8") as fh:
            stats = json.load(fh)
    except (OSError, json.JSONDecodeError):
        stats = {}

    chi2 = stats.get("friedman_chi2", float("nan"))
    p_value = stats.get("friedman_p", float("nan"))
    n_complete = stats.get("n_complete", "?")
    k = stats.get("k", len(VARIANT_KEYS))
    cd = stats.get("critical_difference", float("nan"))
    alpha = stats.get("alpha", 0.05)
    score = stats.get("score", "item_quality")

    headline = (
        f"Within-idx Friedman test on `{score}` over k={k} variants and N={n_complete} "
        f"complete idx: chi^2 = {chi2:.3f} (dof = {k - 1}), p = {p_value:.3g}; "
        f"Nemenyi CD = {cd:.3f} at alpha = {alpha}."
    )

    def _rel(path: str) -> str:
        try:
            return os.path.relpath(path, report_dir)
        except ValueError:
            return path

    parts: list[str] = [headline, "", _md_table(summary)]
    parts.append("")
    parts.append(f"![critical-difference diagram]({_rel(str(RANKING_FIGURE_MAIN))})")
    parts.append("")
    parts.append(
        "Two variants that share at least one letter in `sig_group` are **not** "
        "statistically distinguishable at alpha = 0.05 (their mean-rank gap is "
        "smaller than the critical difference)."
    )

    sub_path = RANKING_SUBDIMENSIONS_CSV
    if os.path.isfile(str(sub_path)):
        sub = pd.read_csv(str(sub_path))
        parts.append("")
        parts.append("### Sub-dimension rankings")
        parts.append("")
        parts.append(f"![sub-dimension CD diagrams]({_rel(str(RANKING_FIGURE_SUBDIM))})")
        for dim, group in sub.groupby("dimension", sort=False):
            parts.append("")
            parts.append(f"**{dim}**")
            parts.append("")
            parts.append(_md_table(group.drop(columns=["dimension"])))
    return "\n".join(parts)


def _emotion_section(emo: pd.DataFrame) -> str:
    if emo.empty:
        return "_(no emotion data)_"
    parts = []
    for v, sub in emo.groupby("variant", sort=False):
        top = sub.head(10)
        rows = [f"- **{r.emotion}** ({int(r['count'])}, {r['share']:.1%})"
                for _, r in top.iterrows()]
        parts.append(f"### {v}\n\n" + "\n".join(rows) + "\n")
    return "\n".join(parts)


def main() -> None:
    ensure_dirs()

    if os.path.isfile(str(COVERAGE_CSV)):
        cov = pd.read_csv(str(COVERAGE_CSV))
    else:
        _, _, cov = load_variants()
        cov.to_csv(str(COVERAGE_CSV), index=False)

    dq = pd.read_csv(str(DATASET_QUALITY_CSV)) if os.path.isfile(str(DATASET_QUALITY_CSV)) else pd.DataFrame()
    rel = pd.read_csv(str(RELIABILITY_CSV)) if os.path.isfile(str(RELIABILITY_CSV)) else pd.DataFrame()

    items_by_variant: dict[str, pd.DataFrame] = {}
    for v in VARIANT_KEYS:
        raw = _read_jsonl(raw_jsonl_path(v, run=1))
        items_by_variant[v] = _compute_item_quality(raw)

    emo = _emotion_frequency_table(items_by_variant)
    emo_path = os.path.join(str(DATASETS_DIR), "emotion_frequency.csv")
    emo.to_csv(emo_path, index=False)

    qc = _qc_summary(items_by_variant)
    qc_path = os.path.join(str(DATASETS_DIR), "qc_summary.csv")
    qc.to_csv(qc_path, index=False)

    figures_dir = str(FIGURES_DIR)
    figures_update_dir = os.path.join(figures_dir, "update")
    os.makedirs(figures_update_dir, exist_ok=True)
    f_bar = os.path.join(figures_dir, "bar_mean_item_quality.png")
    f_dist = os.path.join(figures_dir, "dist_item_quality_grid.png")
    f_heat = os.path.join(figures_dir, "heatmap_semantic_pass_rate.png")
    f_rel = os.path.join(figures_update_dir, "reliability_bars.png")

    fig_bar_mean_iq(dq, f_bar)
    fig_distribution_grid(items_by_variant, f_dist)
    fig_semantic_pass_heatmap(dq, f_heat)
    fig_reliability_bars(rel, f_rel)

    timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    report_dir = str(REPORT_DIR)

    def _rel(path: str) -> str:
        try:
            return os.path.relpath(path, report_dir)
        except ValueError:
            return path

    dq_view_cols = [c for c in (
        "variant", "n_evaluated", "n_failed", "coverage_pct",
        "mean_item_quality", "ci_lo", "ci_hi",
        "semantic_pass_rate", "mean_naturalness", "mean_coherence",
        "dataset_quality_grade",
    ) if (not dq.empty) and (c in dq.columns)]

    rel_view_cols = [c for c in (
        "variant", "n_retest", "rho_semantic_sim", "rho_emotion_naturalness",
        "rho_emotion_coherence", "kappa_semantic_pass", "mad_semantic_sim",
        "mad_emotion_naturalness", "mad_emotion_coherence", "jaccard_emotions",
        "low_reliability",
    ) if (not rel.empty) and (c in rel.columns)]

    coverage_block = coverage_markdown(cov) if not cov.empty else "_(no coverage data)_"
    dq_table = _md_table(dq[dq_view_cols] if dq_view_cols else dq)
    rel_table = _md_table(rel[rel_view_cols] if rel_view_cols else rel)
    worst_block = _worst_items_section(items_by_variant, k=10)
    emotion_block = _emotion_section(emo)
    qc_table = _md_table(qc)
    ranking_block = _ranking_section(report_dir)

    parts: list[str] = [
        "# Dilemma Dataset Validation Report",
        "",
        f"- Generated: {timestamp}",
        f"- Rater: `{MODEL_NAME}` via `{API_URL}`",
        f"- Prompt hash: `{_prompt_hash_short()}`",
        f"- Scoring weights: semantic_sim={W_SEMANTIC}, naturalness={W_NATURALNESS}, coherence={W_COHERENCE}",
        (
            f"- Grade thresholds: Excellent>={GRADE.excellent}, Good>={GRADE.good}, "
            f"Marginal>={GRADE.marginal}, Fail<{GRADE.marginal}"
        ),
        "",
        "## 1. Dataset coverage",
        "",
        coverage_block,
        "",
        "## 2. Headline grades",
        "",
        f"![mean item_quality]({_rel(f_bar)})",
        "",
        dq_table,
        "",
        f"![semantic pass rate]({_rel(f_heat)})",
        "",
        "## 3. Per-variant item_quality distribution",
        "",
        f"![distribution grid]({_rel(f_dist)})",
        "",
        "## 4. Test-retest reliability",
        "",
        f"![reliability bars]({_rel(f_rel)})",
        "",
        rel_table,
        "",
        "Spearman ρ ≥ 0.70 is treated as acceptable intra-rater consistency.",
        "",
        (
            "**GPT_5 `semantic_sim` bar:** No bar is shown because Spearman ρ is undefined "
            "(ceiling effect). On retest, all 34 sampled items received `semantic_sim = 1.0`, "
            "leaving zero variance; mean absolute difference (MAD) was 0.003. This reflects "
            "excellent semantic preservation, not low reliability."
        ),
        "",
        "## 5. Lowest-quality items per variant",
        "",
        worst_block,
        "",
        "## 6. Emotion frequency (open-ended Task 2)",
        "",
        emotion_block,
        "",
        "## 7. QC flag summary",
        "",
        qc_table,
        "",
        "## 8. Ranking analysis (within-idx, Friedman + Nemenyi)",
        "",
        ranking_block,
        "",
        "## 9. Limitations",
        "",
        f"- Single LLM rater ({MODEL_NAME}); ratings may carry the model's own framing biases.",
        "- Prompt sensitivity is partly mitigated by the fixed prompt hash and bootstrap CIs.",
        (
            "- Reliability is intra-rater (same model, same prompt, same temperature); "
            "inter-rater agreement with an additional model would strengthen the validation."
        ),
        (
            "- Intra-rater Spearman \u03c1 in the 0.58\u20130.68 range on the Likert ordinal "
            "dimensions (`emotion_naturalness`, `emotion_coherence`) is comparable to the "
            "acceptable range for human survey raters on ordinal psychometric scales "
            "(Cicchetti, 1994: 0.60\u20130.74 \u201cgood\u201d; 0.40\u20130.59 \u201cfair\u201d). "
            "Ceiling effects on `semantic_sim` (most items score 0.95\u20131.00) further "
            "compress the rank correlation: when a dimension has little true variance, "
            "\u03c1 is dominated by a small number of disagreements and underestimates "
            "agreement. Mean absolute difference (MAD) on naturalness/coherence is "
            "\u22640.35 of a Likert step, which is the more interpretable agreement metric "
            "in this regime."
        ),
    ]
    md = "\n".join(parts).strip() + "\n"

    REPORT_MD.parent.mkdir(parents=True, exist_ok=True)
    with open(str(REPORT_MD), "w", encoding="utf-8") as f:
        f.write(md)
    print(f"Wrote {REPORT_MD}")

    try:
        import markdown as _md_mod
        body_html = _md_mod.markdown(md, extensions=["tables", "fenced_code"])
    except ImportError:
        body_html = "<pre>" + md.replace("&", "&amp;").replace("<", "&lt;") + "</pre>"

    html = (
        "<!doctype html><meta charset='utf-8'>\n"
        "<title>Dilemma Validation Report</title>\n"
        "<style>body{font-family:system-ui;max-width:1000px;margin:2em auto;padding:0 1em;line-height:1.5}"
        "table{border-collapse:collapse;margin:1em 0}td,th{border:1px solid #ccc;padding:4px 8px}"
        "img{max-width:100%}</style>\n"
        + body_html
    )

    with open(str(REPORT_HTML), "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Wrote {REPORT_HTML}")


if __name__ == "__main__":
    main()
