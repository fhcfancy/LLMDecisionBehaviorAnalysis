"""
Within-idx, non-parametric ranking of the 8 emotional dilemma variants.

Consumes the per-item CSVs already produced by ``analyze_results.py``
(``results/items/<variant>_items.csv``) and the per-variant summary
(``results/datasets/dataset_quality.csv``). Does NOT call any API.

Statistical recipe (Demsar 2006, JMLR 7):
    1. Pivot per-item scores to a wide ``idx x variant`` matrix and
       drop any idx that is not complete across all variants.
    2. Friedman test on the columns -> chi^2, p, dof = k - 1.
    3. Mean rank per variant (rank within idx; lower = better; ties
       average).
    4. Nemenyi post-hoc to obtain an 8 x 8 p-value matrix.
    5. Critical Difference at alpha = 0.05:
           CD = q_alpha * sqrt(k * (k + 1) / (6 * N))
    6. Compact-Letter Display: two variants share a letter iff their
       mean ranks differ by less than CD.

Outputs (paths via ``config.py``):
    results/datasets/ranking_summary.csv
    results/datasets/ranking_friedman.json
    results/datasets/ranking_nemenyi_pmatrix.csv
    results/datasets/ranking_subdimensions.csv
    results/figures/figure_ranking_critical_difference.png
    results/figures/figure_ranking_subdimensions.png
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from scikit_posthocs import posthoc_nemenyi_friedman  # noqa: E402
from scipy.stats import friedmanchisquare, rankdata  # noqa: E402

from config import (  # noqa: E402
    DATASETS_DIR,
    DATASET_QUALITY_CSV,
    FIGURES_DIR,
    ITEMS_DIR,
    NEMENYI_Q_ALPHA_05,
    RANKING_FIGURE_MAIN,
    RANKING_FIGURE_SUBDIM,
    RANKING_FRIEDMAN_JSON,
    RANKING_NEMENYI_CSV,
    RANKING_SUBDIMENSIONS_CSV,
    RANKING_SUMMARY_CSV,
    VARIANT_KEYS,
    ensure_dirs,
)
from paper_style import (  # noqa: E402
    THEME_BLACK,
    THEME_BLUE,
    save_publication,
    set_paper_style,
    variant_color_map,
    variant_display_name,
)


SUBDIMENSIONS: tuple[str, ...] = (
    "semantic_sim",
    "emotion_naturalness",
    "emotion_coherence",
)
ALL_SCORES: tuple[str, ...] = ("item_quality",) + SUBDIMENSIONS

# Critical-difference constants follow Demsar (2006), JMLR 7, Table 5.
DEMSAR_CITATION: str = "Demsar (2006), Statistical Comparisons of Classifiers, JMLR 7, Table 5."

MIN_N_COMPLETE: int = 5

EXIT_OK: int = 0
EXIT_BAD_ARGS: int = 2
EXIT_NOT_ENOUGH_DATA: int = 4


@dataclass
class RankingResult:
    """Container for the outputs of one Friedman + Nemenyi pass."""

    mean_ranks: pd.Series
    friedman_chi2: float
    friedman_p: float
    n_complete_items: int
    cd: float
    nemenyi_pvalues: pd.DataFrame
    score_name: str


def load_item_quality_matrix(
    items_dir: Path,
    variant_keys: Sequence[str],
    *,
    score: str = "item_quality",
) -> pd.DataFrame:
    """Load per-variant items CSVs and pivot to an ``idx x variant`` matrix.

    Any idx that does not have a numeric value in every variant column is
    dropped (listwise deletion). Columns are returned in ``variant_keys``
    order; the index is the (stringified) ``idx`` value.
    """
    series_by_variant: dict[str, pd.Series] = {}
    for variant in variant_keys:
        path = items_dir / f"{variant}_items.csv"
        if not path.is_file():
            series_by_variant[variant] = pd.Series(dtype=float, name=variant)
            continue
        df = pd.read_csv(path)
        if df.empty or "idx" not in df.columns or score not in df.columns:
            series_by_variant[variant] = pd.Series(dtype=float, name=variant)
            continue
        df = df.copy()
        df["idx"] = df["idx"].astype(str)
        df = df.drop_duplicates(subset=["idx"], keep="last")
        values = pd.to_numeric(df[score], errors="coerce")
        values.index = df["idx"].to_numpy()
        values.name = variant
        series_by_variant[variant] = values

    matrix = pd.DataFrame(series_by_variant)
    matrix = matrix.reindex(columns=list(variant_keys))
    matrix = matrix.dropna(axis=0, how="any")
    matrix.index.name = "idx"
    return matrix


def compute_critical_difference(k: int, n: int, alpha: float = 0.05) -> float:
    """Nemenyi critical difference for ``k`` variants and ``n`` complete blocks.

    Uses the tabulated Studentized-range/sqrt(2) values from Demsar (2006)
    Table 5 (``config.NEMENYI_Q_ALPHA_05``); only ``alpha == 0.05`` is
    supported.
    """
    if k < 2 or n < 1:
        return float("nan")
    if abs(alpha - 0.05) > 1e-9:
        raise ValueError(
            f"Only alpha=0.05 is tabulated in NEMENYI_Q_ALPHA_05; got {alpha}."
        )
    if k not in NEMENYI_Q_ALPHA_05:
        raise ValueError(
            f"No tabulated q_alpha for k={k}; extend config.NEMENYI_Q_ALPHA_05."
        )
    q_alpha = NEMENYI_Q_ALPHA_05[k]
    return float(q_alpha * np.sqrt(k * (k + 1) / (6.0 * n)))


def friedman_and_nemenyi(
    matrix: pd.DataFrame,
    *,
    score_name: str = "item_quality",
    alpha: float = 0.05,
) -> RankingResult:
    """Run the Friedman omnibus + Nemenyi post-hoc on a complete matrix.

    ``matrix`` is ``idx x variant`` with no NaNs. Higher scores are treated
    as better, so the best variant gets the lowest (rank 1) mean rank.
    """
    if matrix.empty:
        raise ValueError("matrix is empty; nothing to rank")
    n, k = matrix.shape
    if k < 2:
        raise ValueError(f"need >= 2 variants; got {k}")

    column_arrays = [matrix[col].to_numpy(dtype=float) for col in matrix.columns]
    chi2, p_value = friedmanchisquare(*column_arrays)

    ranks_per_row = np.apply_along_axis(
        lambda row: rankdata(-row, method="average"),
        axis=1,
        arr=matrix.to_numpy(dtype=float),
    )
    ranks_df = pd.DataFrame(
        ranks_per_row, index=matrix.index, columns=list(matrix.columns)
    )
    mean_ranks = ranks_df.mean(axis=0)
    mean_ranks.name = "mean_rank"

    nemenyi = posthoc_nemenyi_friedman(matrix.to_numpy(dtype=float))
    nemenyi = pd.DataFrame(
        nemenyi.values,
        index=list(matrix.columns),
        columns=list(matrix.columns),
    )
    np.fill_diagonal(nemenyi.values, 1.0)

    cd = compute_critical_difference(k, n, alpha=alpha)
    return RankingResult(
        mean_ranks=mean_ranks,
        friedman_chi2=float(chi2),
        friedman_p=float(p_value),
        n_complete_items=int(n),
        cd=cd,
        nemenyi_pvalues=nemenyi,
        score_name=score_name,
    )


def assign_sig_groups(mean_ranks: pd.Series, cd: float) -> list[str]:
    """Compact-Letter Display labels aligned to ``mean_ranks`` ordering.

    Two variants share at least one letter iff their mean ranks differ by
    strictly less than ``cd``. Letters are assigned in ascending mean-rank
    order (``a`` is the best-ranked group).
    """
    sorted_mr = mean_ranks.sort_values()
    sorted_vals = sorted_mr.to_numpy(dtype=float)
    sorted_keys = list(sorted_mr.index)
    n_items = len(sorted_vals)
    if n_items == 0:
        return []
    if not np.isfinite(cd) or cd <= 0:
        return ["" for _ in mean_ranks.index]

    # Enumerate maximal cliques of the interval graph (gap < cd).
    cliques: list[tuple[int, int]] = []
    prev_right = -1
    for i in range(n_items):
        right = i
        while right + 1 < n_items and sorted_vals[right + 1] - sorted_vals[i] < cd:
            right += 1
        if right > prev_right:
            cliques.append((i, right))
            prev_right = right

    letters_sorted: list[str] = ["" for _ in range(n_items)]
    for clique_idx, (left, right) in enumerate(cliques):
        letter = chr(ord("a") + clique_idx)
        for position in range(left, right + 1):
            letters_sorted[position] += letter

    key_to_letter = dict(zip(sorted_keys, letters_sorted))
    return [key_to_letter[k] for k in mean_ranks.index]


def build_ranking_table(
    matrix: pd.DataFrame,
    ranking: RankingResult,
    dataset_quality: pd.DataFrame,
) -> pd.DataFrame:
    """Assemble the per-variant ranking summary table sorted by mean rank."""
    if dataset_quality is None:
        dataset_quality = pd.DataFrame()
    dq = dataset_quality.copy()
    if not dq.empty and "variant" in dq.columns:
        dq = dq.set_index("variant", drop=False)

    rows: list[dict[str, object]] = []
    for variant in matrix.columns:
        row: dict[str, object] = {
            "variant": variant,
            "n_complete": ranking.n_complete_items,
            "mean_rank": float(ranking.mean_ranks[variant]),
            "mean_item_quality": float("nan"),
            "ci_lo": float("nan"),
            "ci_hi": float("nan"),
            "semantic_pass_rate": float("nan"),
            "mean_naturalness": float("nan"),
            "mean_coherence": float("nan"),
            "grade": "",
        }
        if not dq.empty and variant in dq.index:
            dq_row = dq.loc[variant]
            for key, source in (
                ("mean_item_quality", "mean_item_quality"),
                ("ci_lo", "ci_lo"),
                ("ci_hi", "ci_hi"),
                ("semantic_pass_rate", "semantic_pass_rate"),
                ("mean_naturalness", "mean_naturalness"),
                ("mean_coherence", "mean_coherence"),
            ):
                if source in dq_row.index:
                    row[key] = dq_row[source]
            if "dataset_quality_grade" in dq_row.index:
                row["grade"] = str(dq_row["dataset_quality_grade"])
        if pd.isna(row["mean_item_quality"]):
            row["mean_item_quality"] = float(matrix[variant].mean())
        rows.append(row)

    table = pd.DataFrame(rows)
    table = table.sort_values("mean_rank", ascending=True, kind="mergesort").reset_index(
        drop=True
    )
    sig_letters = assign_sig_groups(
        table.set_index("variant")["mean_rank"], ranking.cd
    )
    table["sig_group"] = sig_letters

    return table[
        [
            "variant",
            "n_complete",
            "mean_rank",
            "mean_item_quality",
            "ci_lo",
            "ci_hi",
            "semantic_pass_rate",
            "mean_naturalness",
            "mean_coherence",
            "grade",
            "sig_group",
        ]
    ]


def _draw_cd_diagram(
    ax: plt.Axes,
    mean_ranks: pd.Series,
    cd: float,
    title: str,
    *,
    accent: str = THEME_BLUE,
    label_fontsize: float = 7.4,
    tick_fontsize: float = 7.4,
    title_fontsize: float = 9.0,
) -> None:
    """Draw a Demsar-style critical-difference diagram on ``ax``.

    Uses the paper palette: rank axis and connector lines in near-black,
    leader-line dots in the theme blue, and a thin theme-blue accent under
    each significance clique. The result still reads as a CD diagram but
    matches the Perceive paper aesthetic. Font sizes default to a
    one-column publication footprint.
    """
    sorted_mr = mean_ranks.sort_values()
    variants = list(sorted_mr.index)
    ranks = sorted_mr.to_numpy(dtype=float)
    k = len(variants)
    if k == 0:
        ax.set_axis_off()
        return

    color_map = variant_color_map(variants)
    line_color = THEME_BLACK

    rank_min = 1.0
    rank_max = float(k)
    half = (k + 1) // 2
    label_step = 0.50
    y_label_top = -0.55
    y_label_bottom = y_label_top - label_step * max(half - 1, 0)

    ax.set_xlim(rank_min - 0.95, rank_max + 0.95)
    ax.set_ylim(y_label_bottom - 0.7, 1.35)

    ax.plot([rank_min, rank_max], [0.0, 0.0], color=line_color, linewidth=0.9)
    for tick in range(int(rank_min), int(rank_max) + 1):
        ax.plot([tick, tick], [0.0, 0.07], color=line_color, linewidth=0.7)
        ax.text(tick, 0.15, str(tick), ha="center", va="bottom", fontsize=tick_fontsize)

    if np.isfinite(cd) and cd > 0:
        cd_left = rank_min
        cd_right = min(rank_min + cd, rank_max)
        y_cd = 0.62
        ax.plot([cd_left, cd_right], [y_cd, y_cd], color=accent, linewidth=2.0)
        ax.plot(
            [cd_left, cd_left],
            [y_cd - 0.06, y_cd + 0.06],
            color=accent,
            linewidth=1.2,
        )
        ax.plot(
            [cd_right, cd_right],
            [y_cd - 0.06, y_cd + 0.06],
            color=accent,
            linewidth=1.2,
        )
        ax.text(
            (cd_left + cd_right) / 2.0,
            y_cd + 0.09,
            f"CD = {cd:.2f}",
            ha="center",
            va="bottom",
            fontsize=tick_fontsize,
        )

    for i, (variant, rank_val) in enumerate(zip(variants, ranks)):
        marker_color = color_map.get(variant, accent)
        if i < half:
            y_label = y_label_top - i * label_step
            x_label = rank_min - 0.45
            ax.plot([rank_val, rank_val], [0.0, y_label], color=line_color, linewidth=0.6)
            ax.plot([rank_val, x_label], [y_label, y_label], color=line_color, linewidth=0.6)
            ax.scatter([rank_val], [0.0], s=10, color=marker_color, zorder=4, edgecolor="white", linewidths=0.4)
            ax.text(
                x_label - 0.05,
                y_label,
                f"{variant_display_name(variant)} ({rank_val:.2f})",
                ha="right",
                va="center",
                fontsize=label_fontsize,
            )
        else:
            mirror = k - 1 - i
            y_label = y_label_top - mirror * label_step
            x_label = rank_max + 0.45
            ax.plot([rank_val, rank_val], [0.0, y_label], color=line_color, linewidth=0.6)
            ax.plot([rank_val, x_label], [y_label, y_label], color=line_color, linewidth=0.6)
            ax.scatter([rank_val], [0.0], s=10, color=marker_color, zorder=4, edgecolor="white", linewidths=0.4)
            ax.text(
                x_label + 0.05,
                y_label,
                f"{variant_display_name(variant)} ({rank_val:.2f})",
                ha="left",
                va="center",
                fontsize=label_fontsize,
            )

    if np.isfinite(cd) and cd > 0:
        cliques: list[tuple[int, int]] = []
        prev_right = -1
        for i in range(k):
            right = i
            while right + 1 < k and ranks[right + 1] - ranks[i] < cd:
                right += 1
            if right > i and right > prev_right:
                cliques.append((i, right))
                prev_right = right

        bar_y0 = -0.18
        bar_step = 0.12
        for clique_idx, (left, right) in enumerate(cliques):
            y_bar = bar_y0 - clique_idx * bar_step
            ax.plot(
                [ranks[left] - 0.08, ranks[right] + 0.08],
                [y_bar, y_bar],
                color=accent,
                linewidth=2.6,
                solid_capstyle="butt",
                alpha=0.9,
            )

    ax.set_title(title, fontsize=title_fontsize, fontweight="semibold", pad=3)
    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ("top", "right", "bottom", "left"):
        ax.spines[spine].set_visible(False)


def _write_main_outputs(
    matrix: pd.DataFrame,
    ranking: RankingResult,
    dataset_quality: pd.DataFrame,
    out_dir: Path,
    figures_dir: Path,
    alpha: float,
) -> tuple[Path, Path, Path, Path]:
    summary = build_ranking_table(matrix, ranking, dataset_quality)
    summary_csv = out_dir / RANKING_SUMMARY_CSV.name
    summary.to_csv(summary_csv, index=False)

    friedman_payload = {
        "score": ranking.score_name,
        "n_complete": ranking.n_complete_items,
        "k": int(len(ranking.mean_ranks)),
        "friedman_chi2": ranking.friedman_chi2,
        "friedman_p": ranking.friedman_p,
        "alpha": alpha,
        "critical_difference": ranking.cd,
        "q_alpha": NEMENYI_Q_ALPHA_05[int(len(ranking.mean_ranks))],
        "citation": DEMSAR_CITATION,
    }
    friedman_json = out_dir / RANKING_FRIEDMAN_JSON.name
    friedman_json.write_text(json.dumps(friedman_payload, indent=2), encoding="utf-8")

    nemenyi_csv = out_dir / RANKING_NEMENYI_CSV.name
    ranking.nemenyi_pvalues.to_csv(nemenyi_csv, index=True)

    set_paper_style()
    fig, ax = plt.subplots(figsize=(3.45, 2.55))
    _draw_cd_diagram(
        ax,
        ranking.mean_ranks,
        ranking.cd,
        title=f"Critical-difference ({ranking.score_name})  CD = {ranking.cd:.2f}",
        label_fontsize=7.4,
        tick_fontsize=7.0,
        title_fontsize=8.6,
    )
    fig.subplots_adjust(left=0.04, right=0.96, top=0.93, bottom=0.04)
    stem = RANKING_FIGURE_MAIN.stem
    save_publication(fig, figures_dir, stem)
    figure_path = figures_dir / f"{stem}.png"
    plt.close(fig)

    return summary_csv, friedman_json, nemenyi_csv, figure_path


def _build_subdimension_outputs(
    items_dir: Path,
    variant_keys: Sequence[str],
    dataset_quality: pd.DataFrame,
    out_dir: Path,
    figures_dir: Path,
    alpha: float,
) -> tuple[Path | None, Path | None]:
    panel_results: list[tuple[str, RankingResult]] = []
    sub_rows: list[pd.DataFrame] = []
    for score in SUBDIMENSIONS:
        matrix = load_item_quality_matrix(items_dir, variant_keys, score=score)
        if matrix.shape[0] < MIN_N_COMPLETE or matrix.shape[1] < 2:
            continue
        ranking = friedman_and_nemenyi(matrix, score_name=score, alpha=alpha)
        panel_results.append((score, ranking))
        sub = build_ranking_table(matrix, ranking, dataset_quality)
        sub.insert(0, "dimension", score)
        sub_rows.append(sub)

    sub_csv: Path | None = None
    if sub_rows:
        combined = pd.concat(sub_rows, ignore_index=True)
        sub_csv = out_dir / RANKING_SUBDIMENSIONS_CSV.name
        combined.to_csv(sub_csv, index=False)

    sub_fig: Path | None = None
    if panel_results:
        set_paper_style()
        n_panels = len(panel_results)
        # Three rows stacked vertically for a compact one-column footprint.
        # Each CD diagram only needs to lay out 8 labels (four on each side)
        # across ~3.4" of width, so the label fonts are small but legible.
        fig, axes = plt.subplots(n_panels, 1, figsize=(3.45, 1.55 * n_panels))
        axes_iter = np.atleast_1d(axes).ravel()
        for axis, (score, ranking) in zip(axes_iter, panel_results):
            _draw_cd_diagram(
                axis,
                ranking.mean_ranks,
                ranking.cd,
                title=f"{score}  CD = {ranking.cd:.2f}",
                label_fontsize=6.0,
                tick_fontsize=5.8,
                title_fontsize=7.4,
            )
        fig.subplots_adjust(left=0.04, right=0.96, top=0.96, bottom=0.025, hspace=0.45)
        stem = RANKING_FIGURE_SUBDIM.stem
        save_publication(fig, figures_dir, stem)
        sub_fig = figures_dir / f"{stem}.png"
        plt.close(fig)

    return sub_csv, sub_fig


def _write_synthetic_items(items_dir: Path, n_idx: int = 50, seed: int = 20260519) -> None:
    """Generate a plausible 8 x 50 items dataset for ``--selftest``."""
    items_dir.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(seed)
    quality_offsets = {
        "CN": 0.78,
        "CT": 0.74,
        "R1": 0.70,
        "V3": 0.66,
        "GPT_5": 0.82,
        "GPT_o4": 0.79,
        "QwenN": 0.68,
        "QwenT": 0.72,
    }
    for variant in VARIANT_KEYS:
        base = quality_offsets.get(variant, 0.70)
        idx_values = [f"idx_{i:03d}" for i in range(n_idx)]
        semantic = np.clip(rng.normal(loc=base, scale=0.07, size=n_idx), 0.0, 1.0)
        naturalness = np.clip(
            rng.normal(loc=base * 5.0, scale=0.6, size=n_idx), 1.0, 5.0
        )
        coherence = np.clip(
            rng.normal(loc=base * 5.0, scale=0.6, size=n_idx), 1.0, 5.0
        )
        item_quality = (
            0.40 * semantic + 0.35 * (naturalness / 5.0) + 0.25 * (coherence / 5.0)
        )
        df = pd.DataFrame(
            {
                "variant": variant,
                "idx": idx_values,
                "semantic_sim": np.round(semantic, 4),
                "emotion_naturalness": np.round(naturalness, 2),
                "emotion_coherence": np.round(coherence, 2),
                "item_quality": np.round(item_quality, 4),
                "qc_flag": "ok",
            }
        )
        df.to_csv(items_dir / f"{variant}_items.csv", index=False)


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Within-idx, non-parametric ranking of dilemma variants "
            "(Friedman + Nemenyi + critical-difference diagram)."
        )
    )
    parser.add_argument(
        "--score",
        choices=list(ALL_SCORES),
        default="item_quality",
        help="Per-item score column to rank on (default: %(default)s).",
    )
    parser.add_argument(
        "--items-dir",
        type=Path,
        default=ITEMS_DIR,
        help="Directory containing <variant>_items.csv (default: %(default)s).",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=DATASETS_DIR,
        help="Directory for CSV/JSON outputs (default: %(default)s).",
    )
    parser.add_argument(
        "--figures-dir",
        type=Path,
        default=FIGURES_DIR,
        help="Directory for the CD-diagram PNGs (default: %(default)s).",
    )
    parser.add_argument(
        "--alpha",
        type=float,
        default=0.05,
        help="Significance level for Nemenyi CD (only 0.05 is tabulated).",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help=(
            "Generate a synthetic 8 x 50 items dataset in a tmpdir and run the "
            "full pipeline; does not require real items CSVs."
        ),
    )
    return parser.parse_args(list(argv) if argv is not None else None)


def _run_pipeline(
    items_dir: Path,
    out_dir: Path,
    figures_dir: Path,
    score: str,
    alpha: float,
) -> int:
    out_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    matrix = load_item_quality_matrix(items_dir, VARIANT_KEYS, score=score)
    n_complete = int(matrix.shape[0])
    if n_complete < MIN_N_COMPLETE:
        print(
            f"ERROR: only {n_complete} complete idx across all {len(VARIANT_KEYS)} "
            f"variants in {items_dir} (need >= {MIN_N_COMPLETE}). "
            "Run analyze_results.py first or supply --items-dir.",
            file=sys.stderr,
        )
        return EXIT_NOT_ENOUGH_DATA

    ranking = friedman_and_nemenyi(matrix, score_name=score, alpha=alpha)

    if DATASET_QUALITY_CSV.is_file():
        dataset_quality = pd.read_csv(DATASET_QUALITY_CSV)
    else:
        dataset_quality = pd.DataFrame()

    summary_csv, friedman_json, nemenyi_csv, figure_path = _write_main_outputs(
        matrix, ranking, dataset_quality, out_dir, figures_dir, alpha
    )

    sub_csv, sub_fig = _build_subdimension_outputs(
        items_dir, VARIANT_KEYS, dataset_quality, out_dir, figures_dir, alpha
    )

    print(f"N complete idx        : {ranking.n_complete_items}")
    print(f"Friedman chi^2 (df={len(VARIANT_KEYS) - 1}) : {ranking.friedman_chi2:.3f}")
    print(f"Friedman p-value      : {ranking.friedman_p:.4g}")
    print(f"Critical difference   : {ranking.cd:.3f}  (alpha = {alpha}, k = {len(VARIANT_KEYS)})")
    print(f"Wrote {summary_csv}")
    print(f"Wrote {friedman_json}")
    print(f"Wrote {nemenyi_csv}")
    print(f"Wrote {figure_path}")
    if sub_csv is not None:
        print(f"Wrote {sub_csv}")
    if sub_fig is not None:
        print(f"Wrote {sub_fig}")
    return EXIT_OK


def main(argv: Sequence[str] | None = None) -> int:
    """Entry point for the ranking analysis CLI."""
    args = _parse_args(argv)
    ensure_dirs()

    if args.selftest:
        with tempfile.TemporaryDirectory(prefix="dilemmaval_ranking_selftest_") as tmp_str:
            tmp = Path(tmp_str)
            items_tmp = tmp / "items"
            out_tmp = tmp / "datasets"
            figures_tmp = tmp / "figures"
            _write_synthetic_items(items_tmp)
            print(f"[selftest] tmp items dir: {items_tmp}")
            rc = _run_pipeline(
                items_dir=items_tmp,
                out_dir=out_tmp,
                figures_dir=figures_tmp,
                score=args.score,
                alpha=args.alpha,
            )
            # Persist a copy of the main CD diagram next to the script so the
            # user can inspect it after the tmpdir is cleaned up.
            persist = ITEMS_DIR.parent / "figures" / "selftest_critical_difference.png"
            persist.parent.mkdir(parents=True, exist_ok=True)
            src = figures_tmp / RANKING_FIGURE_MAIN.name
            if src.is_file():
                persist.write_bytes(src.read_bytes())
                print(f"[selftest] copied figure -> {persist}")
            return rc

    return _run_pipeline(
        items_dir=Path(args.items_dir),
        out_dir=Path(args.out_dir),
        figures_dir=Path(args.figures_dir),
        score=args.score,
        alpha=args.alpha,
    )


if __name__ == "__main__":
    raise SystemExit(main())
