"""Shared paper style for DilemmaValidation figures.

Mirrors the visual language of ``DataAnalysis/Perceive`` so figures across the
project look like they belong to the same paper.

Conventions
-----------
- Serif font (Times New Roman) with Type-42 PDFs for vector publishing.
- Spines: top/right hidden; left/bottom width 0.7.
- Grid: dashed, axis="y", linewidth 0.6, alpha 0.22, drawn below data.
- Titles: serif, semibold (bar/line) or bold (heatmap panels).
- Bar charts: edgecolor "white" with thin linewidth, no top-spine label crowding.
- Heatmaps: light-to-theme gradient (offwhite -> base color) so the figure
  reads as part of the same publication family.
- Saves at dpi=600 and as PDF with white facecolor.

The palette names follow ``Perceive/theme_colors.md``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import rcParams  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap  # noqa: E402


THEME_BLUE = "#4C78A8"
THEME_BLUE_DARK = "#547397"
THEME_BLUE_LIGHT = "#5A83AF"
THEME_BLUE_SOFT = "#81A0C2"
THEME_PURPLE = "#B279A2"
THEME_ORANGE = "#F3973C"
THEME_RED = "#E36466"

THEME_WHITE = "#FFFFFF"
THEME_OFFWHITE = "#FBFBFB"
THEME_LIGHT_GRAY = "#EBEBEB"
THEME_GRAY = "#D4D4D4"
THEME_BLACK = "#000000"

MODE_BASE_COLORS = {
    "Neutral": THEME_BLUE,
    "Neutral-CoT": THEME_PURPLE,
    "EI": THEME_ORANGE,
    "EA": THEME_RED,
}

# Paper-facing names only. Internal variant keys, filenames, and data IDs must
# continue to use the identifiers on the left-hand side.
VARIANT_DISPLAY_NAMES: dict[str, str] = {
    "CN": "CN",
    "CT": "CT",
    "R1": "R1",
    "V3": "V3",
    "GPT_5": "GPT-5",
    "GPT_o4": "o4-mini",
    "QwenN": "Qwen-N",
    "QwenT": "Qwen-T",
}


def variant_display_name(variant: str) -> str:
    """Return the paper-facing name for an internal variant key."""
    return VARIANT_DISPLAY_NAMES.get(variant, variant)


def set_paper_style() -> None:
    """Apply the Perceive paper rcParams."""
    rcParams["font.family"] = "serif"
    rcParams["font.serif"] = ["Times New Roman", "Times", "Nimbus Roman", "DejaVu Serif"]
    rcParams["pdf.fonttype"] = 42
    rcParams["ps.fonttype"] = 42
    rcParams["text.color"] = "black"
    rcParams["axes.labelcolor"] = "black"
    rcParams["xtick.color"] = "black"
    rcParams["ytick.color"] = "black"
    rcParams["axes.edgecolor"] = "black"
    rcParams["axes.linewidth"] = 0.7
    rcParams["hatch.color"] = "white"
    rcParams["hatch.linewidth"] = 0.7


def hex_to_rgb(hex_color: str) -> tuple[float, float, float]:
    h = hex_color.lstrip("#")
    return tuple(int(h[i : i + 2], 16) / 255.0 for i in (0, 2, 4))


def rgb_to_hex(rgb: tuple[float, float, float]) -> str:
    return "#{:02X}{:02X}{:02X}".format(*(max(0, min(255, round(c * 255))) for c in rgb))


def blend(hex_color: str, target: tuple[float, float, float], amount: float) -> str:
    r, g, b = hex_to_rgb(hex_color)
    tr, tg, tb = target
    mixed = (
        r * (1 - amount) + tr * amount,
        g * (1 - amount) + tg * amount,
        b * (1 - amount) + tb * amount,
    )
    return rgb_to_hex(mixed)


def lighten(hex_color: str, amount: float) -> str:
    return blend(hex_color, (1.0, 1.0, 1.0), amount)


def darken(hex_color: str, amount: float) -> str:
    return blend(hex_color, (0.0, 0.0, 0.0), amount)


def style_axes(ax: plt.Axes, *, grid: bool = True, grid_axis: str = "y") -> None:
    """Apply the standard axis styling used across the paper."""
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_linewidth(0.7)
    ax.spines["bottom"].set_linewidth(0.7)
    if grid:
        ax.grid(axis=grid_axis, linestyle="--", linewidth=0.6, alpha=0.22)
        ax.set_axisbelow(True)


def light_theme_cmap(base_hex: str, name: str | None = None) -> LinearSegmentedColormap:
    """Light-to-theme gradient (offwhite -> base) for heatmaps."""
    cmap_name = name or f"theme_{base_hex.strip('#').lower()}"
    return LinearSegmentedColormap.from_list(cmap_name, [THEME_OFFWHITE, base_hex], N=256)


def warm_alignment_cmap() -> LinearSegmentedColormap:
    """Multi-stop warm gradient used for topic-drift heatmaps."""
    return LinearSegmentedColormap.from_list(
        "alignment_orange_red",
        [THEME_OFFWHITE, "#F7D8B5", THEME_ORANGE, "#EB6A57", THEME_RED],
        N=256,
    )


def save_publication(fig, out_dir: Path | str, name: str, *, dpi: int = 600) -> None:
    """Save a figure as both PNG (dpi) and PDF with white facecolor."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_dir / f"{name}.png", dpi=dpi, bbox_inches="tight", facecolor="white")
    fig.savefig(out_dir / f"{name}.pdf", bbox_inches="tight", facecolor="white")


def variant_color_map(variants: Iterable[str]) -> dict[str, str]:
    """Map dilemma variant keys to a deterministic, theme-aligned palette.

    Splits the 8 emotional-variant family into two architectural groups
    (Claude/DeepSeek vs GPT/Qwen). Within each model family, the
    "thinking" variant gets the darker shade, the "non-thinking" variant
    a lighter shade. This mirrors the model-shade convention used by the
    Perceive consistency bar chart.
    """
    palette = {
        "CN": darken(THEME_BLUE, 0.12),
        "CT": darken(THEME_BLUE, 0.28),
        "R1": darken(THEME_PURPLE, 0.12),
        "V3": darken(THEME_PURPLE, 0.28),
        "GPT_5": darken(THEME_ORANGE, 0.16),
        "GPT_o4": darken(THEME_ORANGE, 0.32),
        "QwenN": darken(THEME_RED, 0.12),
        "QwenT": darken(THEME_RED, 0.28),
    }
    return {v: palette.get(v, THEME_BLUE) for v in variants}


# Hatch patterns per architecture family. Used in the pattern-based bar
# charts (e.g. ``bar_mean_item_quality``, ``reliability_bars``) to keep the
# palette restrained while still letting the eye distinguish families.
VARIANT_HATCH_MAP: dict[str, str] = {
    "CN": "",         # Claude family -> solid
    "CT": "",
    "R1": "//",       # DeepSeek family -> diagonal stripes
    "V3": "//",
    "GPT_5": "..",    # GPT family -> dots
    "GPT_o4": "..",
    "QwenN": "xx",    # Qwen family -> cross-hatch
    "QwenT": "xx",
}


def variant_hatch_map(variants: Iterable[str]) -> dict[str, str]:
    """Architecture-family hatch lookup for the requested variant keys."""
    return {v: VARIANT_HATCH_MAP.get(v, "") for v in variants}
